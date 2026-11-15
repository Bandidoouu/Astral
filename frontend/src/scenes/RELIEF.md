# Relieve topográfico de los tres globos

Todo este trabajo pertenece a `frontend/src/scenes/`. No cambia los exports de
`index.ts`, props compartidos, API, contratos, dependencias ni UI de Violeta.

## Fuentes y referencias

| Cuerpo | Original | Unidades y referencia | Orientación |
| --- | --- | --- | --- |
| Tierra | NASA SRTMGL30 v002 (Earthdata), promediado a 1440×720 con `frontend/tools/make_earth_height_nasa.py` (reemplaza a NOAA ETOPO 2022, retirado para que todo sea NASA) | Metros; océano = 0 m (sin batimetría); sur de 60° S sin dato, relleno 0 m | 1440×720, norte arriba, -180..180 este positivo |
| Luna | NASA SVS CGI Moon Kit / LRO LOLA, `ldem_4_uint.tif` | Unsigned16 en medios metros respecto a 1727400 m: `m = valor*0.5 - 10000`, relativo a 1737400 m | 1440×720, norte arriba, -180..180, centro 0° |
| Marte | NASA MGS MOLA, `megt90n000cb.img` y `.xml`, MEGDR v2 | Int16 big-endian en metros respecto al areoide GMM3. La esfera visual usa 3396 km; no modela la forma del areoide. | 1440×720, planetocéntrico, norte arriba, 0..360 este positivo; rotar 720 columnas |

Fuentes primarias:
- https://lpdaac.usgs.gov/products/srtmgl30v002/
- https://svs.gsfc.nasa.gov/4720/
- https://pds-geosciences.wustl.edu/missions/mgs/megdr.html
- La etiqueta XML original se conserva en `assets/mars-height.xml`.

Las alturas EGM2008 y GMM3 se dibujan sobre esferas de presentación, sin convertirlas
en radios geocéntricos exactos. No son datos de navegación, de búsqueda ni DEM locales.
La Tierra usa radio de presentación 6371 km; Luna 1737.4 km y Marte 3396 km.

## Reproducir los recursos compactos

Se requiere Python con NumPy y Pillow para la conversión offline. Ya estaban
instalados en esta laptop; no se agregan dependencias del frontend. Desde la raíz:

```powershell
python frontend/src/scenes/tools/convert_heights.py
```

El script descarga fuentes a `tools/.cache/` (ignorada por Git). ETOPO original
ocupa aproximadamente 444 MiB. Verifica dimensiones, geotransformación TIFF,
codificación lunar y campos de la etiqueta PDS4 antes de convertir.

- Tierra: promedio de área 15×15, de 60 segundos a 15 minutos (1440×720).
  La resolución global reducida suaviza cumbres y costa; no representa el Everest
  con su altura puntual. Se conserva la batimetría negativa en el recurso.
- Luna: se conserva la resolución original; se aplica la conversión de unsigned16
  a metros sin normalización de contraste.
- Marte: se conserva la resolución original; se convierte big-endian y se rota
  la longitud para compartir el mismo origen geográfico con los otros mapas.
- Salida: `assets/{earth,moon,mars}.height.gz`, cabecera `ATH1`, ancho y alto uint16
  little-endian, valores int16 little-endian en metros, filas norte→sur, celdas
  centradas, límites -180..180 y -90..90. Redondeo al metro (error ≤0.5 m).
  Gzip determinista (`mtime=0`), decodificado con `DecompressionStream`.
- `assets/heights.manifest.json` registra fuentes, dimensiones, referencias,
  rangos y SHA-256 de originales y recursos resultantes.

Las texturas de color no se usan como alturas. Se preservan Blue Marble, LROC y
Viking. `assets/SOURCES.md` conserva su procedencia. Los DEM originales de pruebas
anteriores siguen locales; ya no forman parte del bundle de la app.

## Representación y controles

Malla 512×256 segmentos por globo (96×48 sin DEM). Se desplazan vértices en CPU
con interpolación bilineal del mapa; `computeVertexNormals()` actualiza iluminación.
Se comparten posiciones/alturas polares y se promedian normales duplicadas en polos
y meridiano. La misma función de altura sitúa cuadrícula, marcadores y extremos de
arcos. Los clics usan el raycaster sobre los triángulos desplazados, y recuperan
latitud/longitud de su dirección radial.

El control local `Vertical exaggeration` permite 1..30× (12× inicial). A 1× se indica
`true scale`. La exageración afecta exclusivamente a la altura; no cambia longitudes,
latitudes, datos ni puntajes. En Tierra se aplica `max(altura,0)` para dibujar océanos
a nivel del agua. Los otros cuerpos conservan cuencas negativas.

`Himalaya`, `South Pole–Aitken` y `Olympus Mons` seleccionan coordenadas conocidas
y enfocan el cuerpo. Arrastrar gira; la rueda acerca y aleja. El zoom mínimo es 1.65
unidades de escena. Cambiar la exageración no reinicia la cámara. Reset recupera
la vista general, también bajo React StrictMode. La galaxia conserva su encuadre.

Carga y fallo del DEM se indican por cuerpo; si falla se conserva la textura sobre
una esfera lisa. Sin WebGL se conserva el mensaje de respaldo y la UI externa.

## Comprobaciones

Desde `frontend/`:

```powershell
npm.cmd test
node --test src/scenes/*.test.ts
npm.cmd run build
```

El script npm compartido todavía solo recoge pruebas de `src/api/`; por eso se
invocan además las pruebas locales de escenas sin editar configuración compartida.
Las pruebas verifican Himalaya, Olympus Mons y South Pole–Aitken, signos y escala
de alturas, mar a cero, continuidad de ±180°, polos y normales duplicadas, raycasting
y coordenadas, anclajes externos a la malla, y rechazo de recursos corruptos.

Prueba manual en laptop: `npm.cmd run dev`; abrir la URL de Vite, esperar `relief ready`
en los tres cuerpos. Visitar cada acceso geográfico, acercar con la rueda y arrastrar
hasta ver la región de perfil. Comparar 1×, 12× y 30×. Comprobar marcadores/arcos con
resultados, reset, galaxia y vuelta a sistema. Las fuentes globales no muestran
cráteres pequeños ni detalle de aterrizaje. La malla y las texturas son visualización.

## Integración pendiente (sin modificar archivos ajenos)

Copiar procedencia, URLs, comandos y referencias de esta guía y del manifiesto a
`docs/datos.md`. (ETOPO se retiró: el relieve terrestre de respaldo es SRTMGL30 de la NASA.) Sustituir los registros anteriores de LOLA float32 y
MOLA sin XML por estos recursos de presentación. Coordinar si se desea que `npm test`
incluya `src/scenes/*.test.ts`. No se necesita cambiar contratos ni props compartidos.

Validación visual automatizada (Chrome instalado, sin dependencias adicionales):
`node src/scenes/tools/browser_smoke.mjs` desde frontend. Levanta temporalmente
Vite en 5181 y Chrome headless con perfil independiente, guarda capturas en
`tools/.cache/browser/` y cierra ambos al terminar. Comprueba carga de los tres DEM,
accesos geográficos, zoom, órbita, exageración 1×/30×, reset, vistas y fallbacks.

La UI compartida todavía incluye el texto “Schematic globes · not to scale”.
Coordinar su actualización con Violeta; esta tarea no edita su carpeta.

Nota de precisión: ETOPO mantiene coordenadas horizontales WGS84/latitud geodésica;
se presentan sobre una esfera, sin modelar el elipsoide terrestre ni el geoide.
MOLA usa latitud planetocéntrica. Las diferencias de referencia vertical entre
cuerpos se conservan: no se equiparan sus cotas ni se recalculan métricas científicas.

## Capas de Hanna: actualización vigente

El arranque actual usa las alturas PNG y normales de `public/textures`, con escala
según el `height.json` de cada cuerpo. Los DEM ETOPO/LOLA/MOLA descritos en esta guía
se conservan como opción `Global DEMs` y respaldo de carga. El detalle de recursos,
normales, capas, cobertura y controles actual está en [LAYERS.md](LAYERS.md).

> **2026-11-15:** se retiró NOAA ETOPO 2022 y la opción "Global DEMs" del selector *Height source*: todo el relieve es de la NASA (SRTMGL30, LOLA, MOLA). `earth.height.gz` ahora sale de SRTMGL30.
