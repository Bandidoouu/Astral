# Hanna: capas de los globos desde public/textures

Esta tarea edita únicamente `frontend/src/scenes/`. Conserva los exports de
`index.ts` y los props compartidos. API, UI de Gris/Violeta, backend, contratos,
dependencias y publicación quedan fuera de esta tarea.

## Uso

Abrir la demo local y usar el panel de la escena (arriba a la derecha):

- **Surface layer:** Visible color, Height map, Shaded relief, Topography o Base suitability.
- **Height source:** Packaged NASA elevation (predeterminado) o los DEM globales
  anteriores ETOPO/LOLA/MOLA.
- **Normal-map lighting:** normales de public/textures en Visible y Base suitability.
  Se desactiva para los DEM globales porque representan otras fuentes/resoluciones.
- **Vertical exaggeration:** 1..30×; 1× conserva la escala física vertical.
- **Layer legend & coverage:** leyenda y advertencias del cuerpo seleccionado.

Los tres globos comparten el modo visual. Tierra permanece con color visible al
seleccionar Base suitability: el repositorio no trae aptitud terrestre.

## Recursos usados (sin nuevas descargas)

`public/textures/{earth,moon,mars}/` contiene mapas equirectangulares norte arriba,
longitud -180..180 este positiva. Procedencia: los README de cada cuerpo y
`docs/datos.md` §4. Esta implementación usa:

| Recurso | Uso |
| --- | --- |
| color_4k.jpg | Color principal, con las imágenes locales anteriores de respaldo |
| height_4k.png + height.json | Campo de elevaciones para desplazar vértices en CPU |
| normal_4k.jpg | Iluminación de detalle, con orientación este/norte/arriba |
| hillshade_4k.jpg | Sombreado calculado previamente; luz fija, no dinámica |
| topography_4k.jpg + topography_legend.png | Topografía y leyenda en metros |
| suitability_4k.png + suitability_legend.png | Aptitud total de Luna/Marte; alfa transparente = sin datos |

El PNG de aptitud global es un recurso georreferenciado distinto de la figura
polar con ejes/leyenda que consume `LunarSuitabilityMap`. La figura polar no se
proyecta sobre los globos.

## Alturas y normales

`height.json` se valida por cuerpo, dimensiones 2:1, orientación, codificación,
rango finito y unidades declaradas por la fórmula:

```
height_m = min_m + pixel / 255 * (max_m - min_m)
```

El navegador lee los bytes de gris del PNG, sin usarlos como color sRGB. Reduce
el campo de presentación a 1440×720 mediante Canvas y convierte metros a km para
el muestreo compartido. El modelo, rankings y puntajes no usan estos datos.

En Tierra el bin de gris que representa cero metros se restaura a 0 m para evitar
que la cuantización de 8 bits eleve los océanos unos metros. La geometría visible
continúa usando `max(altura,0)`. Se preservan las notas del paquete: SRTM no cubre
Antártida al sur de 60° S (relleno visual a cero), y los extremos sin datos de los
otros mapas se rellenan con la fila válida más cercana. Los DEM globales anteriores
siguen disponibles mediante el selector; su conversión está en `RELIEF.md`.

Se desplazan los vértices en CPU y se recalculan sus normales. Esto mantiene
coherentes el raycaster, los clics geográficos, los marcadores y los arcos. Se
suavizan las normales duplicadas del meridiano y de los polos.

Los normal maps son datos lineales (`NoColorSpace`), con +x este, +y norte, +z arriba.
El shader transforma ese marco a XYZ del globo y luego a la cámara. **Sustituye**
la normal de iluminación en lugar de sumar dos veces la pendiente ya presente en
la malla. La amplitud tangencial se ajusta por `exageración actual / exageración del
normal map` (Tierra 20×, Luna 8×, Marte 6×). En el grado más próximo a cada polo se
suaviza la componente tangencial para evitar la singularidad del marco longitudinal.
Si el mapa falla o se usa otro DEM, se conservan las normales de la malla.

El sombreado precalculado y la topografía se muestran sin iluminación adicional
ni tone mapping para conservar sus colores y leyendas. El sombreado mantiene su
luz y exageración de generación; no sigue la luz ni la exageración de la geometría.
La aptitud usa una malla superpuesta que comparte geometría y no intercepta clics.
Las zonas con alfa cero dejan ver el color del globo, nunca un puntaje cero inventado.

## Límites visibles

La aptitud es una sugerencia, no selección final de un sitio. Luna solo cubre la
zona polar sur y no incluye iluminación ni visibilidad terrestre. Marte tiene
hidrógeno limitado a 60° N–60° S y otras variables faltantes según el README fuente.
Las leyendas se muestran solo si la imagen de la capa correspondiente está cargada.

Si falta el PNG de altura se intenta el DEM global local, indicando el respaldo.
Si también falla, queda la esfera de color. Si faltan normales se usa la malla;
si falta una capa de color se conserva la imagen disponible, con aviso. El respaldo
sin WebGL deja la interfaz externa disponible. Ningún recurso necesita una API.

## Comprobaciones

Desde frontend:

```powershell
npm.cmd test
node --test src/scenes/*.test.ts
npm.cmd run build
node src/scenes/tools/hanna_layers_smoke.mjs
```

Las pruebas de escenas leen los PNG originales con un decodificador independiente
para verificar Himalaya, Olympus Mons y South Pole–Aitken, escala de metros, costa,
alfa RGBA, URL bajo subdirectorio, costuras, normales de malla, raycasting y anclajes.
El script de Chrome headless prueba los cinco modos, normales, fuentes de altura,
reset, vistas y respaldos; detecta también errores de compilación de shaders.
Capturas y resultado quedan en `tools/.cache/hanna-layers/`, ignorado por Git.

Para integración documental: registrar este uso de las capas y los controles junto
al inventario existente en `docs/datos.md`; no hace falta una fuente nueva. El
selector de Same size / Gravity-scaled, los textos de resultados, los endpoints y
el sitio público pertenecen a las otras prioridades y no se modifican aquí.
