# ASTRAL · Módulo `ml/` (red neuronal, el corazón del proyecto)

Este archivo es la fuente de verdad del frente de la red neuronal. Si algo aquí
contradice al documento del plan, manda este archivo: incluye las decisiones
tomadas durante el hackathon. **Las reglas generales del equipo (qué es ASTRAL,
dueños, aviso de cambios, nada de co-autores de IA) están en el `CLAUDE.md` de la
raíz y también aplican aquí.**

## 1. El proyecto en 30 segundos

Ver `CLAUDE.md` de la raíz, §1. Resumen para ML: la red recibe un parche de
relieve y devuelve sus gemelos; tiene que **ganarle a la fórmula base** y
**redescubrir El Pinacate sin haberlo visto**.

**Requisito central:** el usuario elige un punto en **cualquiera de los tres
cuerpos** (Tierra, Luna o Marte) y recibe coincidencias en los otros dos (o en los
que pida en `target_bodies`), **en cualquier punto del globo**. Dos escalas:
**1 km/px global** (los tres cuerpos, por defecto) y **60 m/px de detalle** (solo
Luna ↔ Tierra y solo dentro de su cobertura: Luna al sur de 80° S, Tierra en la caja
de México). Cada búsqueda indica su escala (`scale_m` = 1000 o 60). Búsqueda:
`ml/search.py` (método por defecto `hybrid`: la fórmula base preselecciona ~500
candidatos y la red reordena).

**Requisito central: la búsqueda no es solo de forma.** La red se encarga
únicamente de la forma del terreno (`terrain`, ranking por **fusión RRF** de la red y
la fórmula base, k = 60 fijo, sin ajustar pesos). Las demás dimensiones se calculan
aparte, como características por parche con datos de los portales oficiales:

| Dimensión | Tierra | Luna | Marte (bloque 4) |
| --- | --- | --- | --- |
| `thermal` (máx., mín., rango) | MODIS MOD11C3 (LST 2023) | Diviner: PRP sur (media, máx., hielo; ~0.5 km) + GCP global (tbol por hora local, 0.5°) | TES |
| `albedo` | MODIS MCD43C3 (infrarrojo cercano) | LOLA `ldam` (1064 nm; polar 1 km, global `ldam_10`) | TES |
| hielo (atributo del sitio) | — | Diviner PRP `ice_depth`: distancia a hielo estable a ≤ 1 m | Hidrógeno de Mars Odyssey |

Cada dimensión da un puntaje de 0 a 1; si falta el dato en un lugar, es `null`
("sin dato") y **no cuenta en el total. Nunca se inventan valores.**

**Capa de aptitud para base lunar** (reglas transparentes, no la red): pendiente
< 8° (aterrizaje) y < 15° (rover) con LOLA, cercanía a hielo estable y temperatura con
Diviner; cada criterio de 0 a 1 con pesos visibles; rasters del polo sur por criterio
y del total; se superponen los candidatos de la NASA y se mide si caen en zonas de
puntaje alto. **Faltan la iluminación y la visibilidad de la Tierra porque no están en
los portales del reto: por eso la capa es una sugerencia, no una elección final.**
Marte: la misma capa con MOLA (pendiente y altitud baja), TES (inercia térmica y
albedo) e hidrógeno de Mars Odyssey, todo del PDS. Minerales: fuera de alcance.

## 2. Cómo trabajar aquí (reglas para Claude Code)

- `ml/` es el frente de ML: datos para la red, parches, modelo, entrenamiento,
  embeddings, índice, UMAP, Grad-CAM y validación. Produce los artefactos que
  consumen backend y frontend (`docs/contratos.md`). ML también puede tocar
  `backend/`, pero cualquier cambio que afecte a otro integrante sigue el
  protocolo de aviso del `CLAUDE.md` raíz (§4.1): rama, push, PR y confirmación.
- Prioridad absoluta: que funcione de punta a punta. Primero una versión simple que
  corra, después se mejora. Nada de refactors grandes después de H16.
- Antes de cualquier proceso que tarde más de ~2 minutos (generar todos los
  parches, entrenar, embeber), probar primero con una muestra pequeña y mostrar el
  resultado. Los procesos largos se lanzan dentro de tmux.
- Verificar siempre unidades y georreferencia: imprimir min/max/media de alturas
  por cuerpo y revisar que estén en metros y en rangos razonables.
- Código en `ml/` (ver estructura en la sección 5). Scripts ejecutables con
  argumentos (`argparse`), sin rutas absolutas escondidas: usar `ASTRAL_ROOT`
  (por defecto, la raíz del repositorio). Se corren desde la raíz:
  `python -m ml.train ...`.
- Instalar paquetes con `uv pip install` (el venv no tiene pip). Nunca
  `--break-system-packages`.
- Hacer commits pequeños y frecuentes con mensajes claros. **Sin `Co-Authored-By`
  de ninguna IA** (regla del equipo).
- Si una decisión cambia algo de este archivo, actualizar este archivo.

## 3. Equipo y fronteras

| Persona | Frente | Qué espera del frente de ML |
| --- | --- | --- |
| Esteban (con Claude Code) | ML (red neuronal) | Dueño de `ml/` y de los contratos |
| Hanna | Frontend 3D (globos, capas, arcos, galaxia) | `galaxy.json` y alturas de parches para la vista de detalle |
| Gris | Frontend UI (tarjetas, radar, perfiles, idioma) | Puntajes por dimensión (`contracts/similar_response.json`) |
| Angel, Tamara, Ethan | Backend (FastAPI) | Embeddings, índice FAISS, metadatos, puntajes; validación y Grad-CAM para el pitch |

## 4. Máquina y entorno

- PC con Windows y WSL2 (Ubuntu 24.04). Host Tailscale: `astral-gpu`.
- GPU: RTX 3060, 12 GB de VRAM. Driver con CUDA 13.5.
- RAM: WSL limitado a 12 GB (`.wslconfig`), swap 16 GB. Usar memmap para parches.
- Python 3.12 en `~/astral/.venv` (uv). PyTorch 2.15 con CUDA 13.4, torchvision 0.29.
- Ya instalado: numpy, scipy, pandas, pyarrow, scikit-learn, faiss-cpu, umap-learn,
  grad-cam (pytorch-grad-cam), tensorboard, tqdm, matplotlib, jupyterlab, rasterio,
  pyproj, xarray, rioxarray, geopandas, shapely, earthaccess, fastapi, uvicorn, pillow.
  GDAL de línea de comandos (`gdalinfo`, `gdalwarp`, `gdal_translate`) disponible.
- Benchmark medido: ResNet-18 de 5 canales, 128x128, lote de 256 imágenes, AMP:
  **1694 img/s y 1.3 GB de VRAM pico.** Hay mucho margen para lotes más grandes.
- Trabajar siempre en `~/astral` (ext4), nunca en `/mnt/c` (muy lento).
- Earthdata: credenciales guardadas en `~/.netrc` (`earthaccess.login(strategy="netrc")`).

## 5. Estructura de carpetas

```text
Astral/                       # raíz del repo (local: ~/astral)
├── data/                      # fuera de git
│   ├── raw/{moon,earth,mars}/ # descargas tal cual
│   ├── patches/               # parches y metadatos
│   └── artifacts/             # modelo, embeddings, índice, UMAP, Grad-CAM
└── ml/
    ├── CLAUDE.md              # este archivo
    ├── data/                  # descarga, reproyección, parches
    ├── model/                 # red, pérdidas, dataset
    ├── train.py
    ├── embed.py               # embeddings + índice FAISS + UMAP
    ├── baseline.py            # fórmula base (estadísticas de relieve)
    └── evaluate.py            # red contra fórmula, prueba ciega, ablación
```

## 6. Datos

Regla del equipo: todos los datos salen de los portales oficiales del reto
(NASA PDS, LRO / PDS Geosciences, NASA Earthdata) o de los recursos de agencias
asociadas listados en el reto (ESA Copernicus Data Space, JAXA G-Portal, CSA).
Para premios globales es obligatorio usar datos de la NASA; ya se cumple.
**Lista oficial completa, procedencia verificada y comandos de descarga:
`docs/datos.md`.** Todo dato nuevo se registra ahí antes de usarlo.

### 6.1 Inventario descargado

| Cuerpo | Archivo | Detalles |
| --- | --- | --- |
| Luna | `data/raw/moon/ldem_75s_60m_float.img` + `.lbl` | LOLA (LRO), polo sur de 75° S al polo (esquinas a ~69° S). Estereográfica polar centrada en el polo sur, 60 m/px, 15248x15248, Float32. **VALORES EN KM relativos al radio de 1737.4 km: multiplicar por 1000 para metros.** NoData = -3.4028227e+38. Leer con GDAL usando el `.lbl`. |
| Tierra | `data/raw/earth/mexico_60m.tif` | NASADEM (30 m) mosaico de México, reproyectado a EPSG:6372 (Lambert para México, metros), 60 m/px, 62012x40339. Rango verificado: -82 a 5644 m. NoData = -32768. |
| Tierra | `data/raw/earth/mexico_500m.tif` | Igual, a 500 m/px (7441x4841). Para comparar con Marte. |
| Tierra | `data/raw/earth/mexico_200m.tif` | Igual, a 200 m/px. Ya no se usa (Marte quedó a 500 m). |
| Tierra | `data/raw/earth/mexico_dem.vrt`, `hgt/*.hgt`, `dem/*.zip` | Fuente: 411 mosaicos NASADEM_HGT en la caja (-118, 14, -86, 33). |
| Tierra | `data/raw/earth/lst/*.hdf` | MODIS MOD11C3 (Terra), temperatura de superficie mensual, 0.05°, 12 meses de 2023. HDF4: si rasterio no lo abre, `uv pip install pyhdf`. Subdatasets `LST_Day_CMG`, `LST_Night_CMG` (escala 0.02, kelvin). |
| Marte | `data/raw/mars/mars_megdr.vrt` | MOLA MEGDR (Mars Global Surveyor) de PDS Geosciences, 128 px/grado, 16 mosaicos `megt*hb.img` + `.xml`. 46080x22528, de 88° N a 88° S. Int16 en **metros** sobre el areoide. Proyección equirectangular en metros con píxel de 463.06 m medido en el ecuador: el píxel este-oeste real mide 463 * cos(lat). **Reproyectar cada región a una proyección métrica local antes de cortar parches.** |
| Luna | `data/raw/moon/lola_global/ldem_64_float.{img,lbl,xml}` | LOLA GDR cilíndrico global, 64 px/° (~474 m en el ecuador). **En km.** Para la escala de 500 m. |
| Luna | `data/raw/moon/sldem2015/sldem2015_512_*_float.*` | SLDEM2015 (LOLA + Kaguya de JAXA), 512 px/° (~59 m), equirectangular, **en km**: Montes Marius (`00n_30n_270_315`), Mare Tranquillitatis (`00n_30n_000_045`), Mare Imbrium (`30n_60n_315_360`). Para la prueba ciega. |
| Luna | `data/raw/moon/diviner/dlre_prp_south.*` | Diviner PRP sur (PDS4). Para `thermal`. |
| Tierra | `data/raw/earth/analogs/{arizona,deathvalley}/` | NASADEM alrededor de Meteor Crater y el campo volcánico de San Francisco (Arizona) y de Death Valley. Para la validación. |
| (apartado) | `data/raw/_no_oficial/jezero.tif` | Recorte del blend MOLA-HRSC del USGS. **No usar** (no viene de los portales del reto). |

### 6.2 Datos pendientes

- **Diviner (LRO), temperatura lunar polar.** (PRP sur descargándose en `data/raw/moon/diviner/`.) En PDS Geosciences:
  `https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/`
  (`data_derived_prp/dlre_prp_south.tab`, ~605 MB, y `data_derived_pcp/`).
  Son tablas PDS4 con su `.xml` (`uv pip install pds4_tools`). Los organizadores
  destacan los productos polares de Diviner para comparar con ambientes terrestres
  extremadamente fríos o con hielo: la dimensión térmica debe usarlos.
- **SLDEM2015 (LOLA + Kaguya de JAXA), latitudes medias de la Luna** (Marius, Tranquillitatis e Imbrium descargándose en `data/raw/moon/sldem2015/`):
  `https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/sldem2015/`.
  Bajar solo los mosaicos de los Montes Marius (~14° N, 304° E) y uno o dos de
  mares lunares, para la prueba ciega.
- **Relieve alrededor de análogos conocidos fuera de México** (validación).
  OJO: NASADEM solo cubre de 60° N a 56° S. Meteor Crater, Death Valley, Atacama,
  Mauna Kea y Lonar sí están cubiertos (bajar con `earthaccess` y cajas pequeñas).
  Haughton, Islandia y los Valles Secos de McMurdo NO: para esos usar Copernicus
  DEM GLO-30 del Copernicus Data Space de ESA (recurso oficial del reto).
- **Sitios fríos con hielo en la Tierra** (Antártida, glaciares, permafrost de alta
  montaña) como candidatos térmicos: MODIS sí los cubre; el relieve, con Copernicus DEM.

### 6.3 Decisión pendiente: geología

La dimensión "materiales" pensaba usar mapas geológicos (GLiM para la Tierra y los
mapas del USGS de la Luna y Marte), pero esos no vienen de los portales del reto.
Opciones: (a) usarlos igual citándolos, (b) reemplazar materiales por albedo y
aridez de fuentes oficiales, (c) dejar la dimensión fuera del MVP. Preguntarle a
Esteban antes de implementarla.

## 7. Escalas y parches

| Escala | Compara | Ventana (128 px) | Fuentes |
| --- | --- | --- | --- |
| 60 m/px | Luna con Tierra | 7.68 km | LOLA polar (y SLDEM para Marius) contra `mexico_60m.tif` |
| **1000 m/px (global)** | **Tierra, Luna y Marte entre sí, en todo el globo** | 128 km | Tierra: SRTMGL30 (Earthdata, 30", de 90° N a 60° S: **sin Antártida**; al norte de 60° N viene rellenado con GTOPO30). Luna: LOLA `ldem_64_float` promediado a ~950 m (**LOLA no publica 32 px/°**; en km). Marte: MOLA MEGDR 128 px/° promediado a ~930 m. Cada parche se remuestrea en su propia proyección azimutal equivalente de Lambert centrada en él (sin distorsión, polos incluidos), con centros repartidos uniformemente en la esfera. |
| ~~500 m/px~~ | Reemplazada por la escala global de 1 km | — | — |

Por qué dos escalas: el relieve global de Marte en los portales oficiales es de
~463 m/px; la Luna permite 60 m/px, donde un cráter de 1.5 km ocupa ~25 píxeles.

- **Formato:** guardar solo la elevación en metros, float16, en
  `data/patches/patches_{body}_{scale}.npy` (memmap, forma N x 128 x 128), más
  `data/patches/meta_{body}_{scale}.parquet` con columnas:
  `patch_id, body, scale_m, lat, lon, crs, x, y, region, holdout` (más
  `elev_mean_m, elev_min_m, elev_max_m, row, col`).
  **El `.npy` guarda la elevación RELATIVA a la media del parche; la absoluta es
  `patch + elev_mean_m`.** Motivo: en float16 una altura absoluta de 5 a 8 km solo
  tiene resolución de 4 a 8 m (escalones de ~4° de pendiente a 60 m/px).
  Generador: `ml/data/make_patches.py --body {moon,earth}`.
- **patch_id:** `{body}-{scale}-{índice de 6 dígitos}`, p. ej. `earth-60-000123`.
  `body` es `earth`, `moon` o `mars`; `scale` es `60` o `500`.
- **Coordenadas:** `lat`, `lon` del centro del parche, planetocéntricas, en grados,
  longitud de -180 a 180 positiva al este, para los tres cuerpos.
- **Filtros:** descartar parches con cualquier NoData o con agua (en la Tierra,
  elevación <= 0 en la costa es una buena primera aproximación; WorldCover de ESA
  si da tiempo).
- **Muestreo:** rejilla sin traslape para el índice de búsqueda; para entrenar se
  puede muestrear con traslape. Objetivos aproximados: Luna 15 mil, Tierra 35 mil a
  60 m; Marte 15 mil, Tierra ~10 mil a 500 m.
- **Luna:** polo sur en su proyección nativa; ya es métrica. Índice: rejilla sin
  traslape de 80° a 90° S (`patches_moon_60`, 4,922). Entrenamiento: todo el archivo
  (hasta ~69° S en las esquinas) con stride 64 (`patches_moon_60_train`, 56,169).
- **Tierra 60 m:** `patches_earth_60`, 54,993 (115 holdout). La caja de NASADEM
  incluye partes del suroeste de EE. UU. y Centroamérica; `region` dice "Mexico"
  para todos salvo Pinacate. **Pendiente antes de H12:** asignar estado/país con
  Natural Earth admin-1 (10m) y citarlo en las referencias.
- **Marte:** regiones objetivo completas y una muestra al azar con |lat| < 60°.
- **Holdout / prueba ciega:** todo parche a menos de 50 km de El Pinacate
  (aprox. 31.77° N, -113.50°) lleva `holdout=True`: queda FUERA del entrenamiento
  pero DENTRO del índice de búsqueda.

## 8. Modelo y entrenamiento

### 8.1 Canales de entrada (calculados en la GPU dentro del dataloader)

Mismo código para los tres cuerpos; el tamaño de píxel se pasa como parámetro.

1. Elevación relativa: elevación menos la media del parche, entre 500 m, recortada.
2. Pendiente en grados, entre 90.
3. Rugosidad: RMS en ventanas de 3x3 del residuo `z − z suavizado` (gaussiana
   σ = 3 px), entre el tamaño de píxel. La desviación 3x3 cruda era casi igual a la pendiente.
4. Curvatura: laplaciano de la elevación suavizada (gaussiana σ = 1.5 px), para
   quitar las franjas de órbitas de LOLA y el ruido de NASADEM (delatan el planeta).
5. Sombreado (hillshade) con azimut del Sol aleatorio.

Aumentaciones: rotaciones de 90°, volteos, recorte y reescalado de ±20%, ruido
gaussiano, escala vertical de ±15% y azimut del Sol aleatorio.

### 8.2 Arquitectura

- Backbone: ResNet-18 preentrenada de torchvision; `conv1` adaptada a 5 canales
  inicializando con el promedio de los pesos RGB.
- Embedding: capa lineal 512 -> 128, normalizada a norma 1. Es lo que se guarda y se busca.
- Cabeza de proyección: MLP 128 -> 128, solo para la pérdida.
- Discriminador de planeta: MLP 128 -> 64 -> n detrás de una capa de inversión de
  gradiente (gradient reversal). **v1: solo Luna y Tierra (2 clases); Marte después
  (3 clases).** Lambda sube de 0 a 1 (curva DANN) durante el entrenamiento. Su
  entrada es el embedding por √128 y usa 10x el lr sin weight decay: con el
  embedding de norma 1 tal cual, se quedaba en el azar aun sin inversión.
- Pérdida: NT-Xent (SimCLR) con temperatura 0.1 + lambda * entropía cruzada del discriminador.
- Lotes balanceados: misma cantidad de parches de cada cuerpo por lote.
- **v2 (obligatorio desde v2 y en la escala de 500 m):** lotes emparejados por
  estratos de (log relieve, pendiente media) (`--matched`, 8x8 estratos, solo los que
  tienen parches de todos los cuerpos), **λ máximo 0.3** (`--lambda-max 0.3`) y
  **cabeza auxiliar** 128 -> 64 -> 2 que predice log(relieve) y pendiente media desde
  el embedding, calculados sobre la vista aumentada (`--aux-weight 0.1`).

### 8.3 Entrenamiento

- AdamW, lr 3e-4 con 128 parches por lote (256 vistas); si se sube a 256 parches
  (512 vistas), lr ~6e-4. Programación coseno, AMP (bf16). **40 épocas el modelo
  principal y 25 la ablación**, con todos los parches (~110 mil, ~867 pasos/época).
- Estimado: ~2 a 2.5 min por época con ~75 mil parches -> 50 épocas en ~2 horas.
- Checkpoint cada época, TensorBoard en `runs/`, semilla fija.
- Alarmas: pérdida que no baja -> bajar lr; discriminador que acierta casi siempre
  -> subir lambda; todos los embeddings iguales (colapso) -> revisar aumentaciones y
  temperatura.
- Después del modelo principal, entrenar la **ablación sin discriminador** (cabe en
  la ventana de tiempo) para comparar los UMAP. En la ablación (`--no-disc`) el
  discriminador se sigue entrenando con lambda = 0 para medir cuánto se separan
  los planetas (en la prueba rápida: ~90-99%).
- Comando: `python -m ml.train --run <nombre> --epochs N [--no-disc] [--version n]`.
  Log por época en `runs/<nombre>/epochs.jsonl` y TensorBoard.

## 9. Artefactos que consume el resto del equipo

**Fuente de verdad: `docs/contratos.md`** (formatos de artefactos, `POST /api/similar`,
puntajes por dimensión y perfiles de misión), con ejemplos en `contracts/`.
Cualquier cambio a esos formatos sigue el protocolo de aviso (§4.1 del `CLAUDE.md` raíz).

## 10. Puntaje por dimensión y perfiles de misión

Ver `docs/contratos.md` §3 y §4. La dimensión `terrain` es el coseno entre
embeddings de la red; `operations` sale de las estadísticas de pendiente y
rugosidad del parche; `thermal`, de Diviner contra MODIS; `materials`, pendiente
(§6.3).

## 11. Sitios objetivo y análogos conocidos

- **Luna, bases del polo sur:** borde del cráter Shackleton (centro aprox.
  89.67° S, 129.78° E) y Mons Mouton, entre los candidatos líderes; también las
  regiones candidatas de Artemis III (Malapert Massif, Nobile Rim, de Gerlache Rim,
  Haworth, etc.). Coordenadas exactas: confirmarlas con Ciencia y pitch.
- **Luna, prueba ciega:** Montes Marius (~14° N, 304° E), campo de domos
  volcánicos, y cráteres en mares lunares. Debería aparecer El Pinacate arriba.
- **Marte:** Jezero, Gale y Arcadia Planitia (hielo), a confirmar con Ciencia y pitch.
- **Análogos conocidos para validar:** Meteor Crater (Arizona), Haughton (Canadá),
  Valles Secos de McMurdo (Antártida), Atacama (Chile), Mauna Kea (Hawái),
  Islandia, Death Valley, campo volcánico de San Francisco (Arizona),
  Lonar (India). El Pinacate es la prueba ciega.

## 12. Validación (la prueba para el jurado)

1. **Fórmula base** (`ml/baseline.py`): vector de ~20 estadísticas por parche
   (relieve, histograma de pendientes, rugosidad, integral hipsométrica,
   curvatura) con distancia euclidiana estandarizada.
2. **Métrica:** para cada consulta, percentil en el que queda el análogo conocido
   entre todos los parches terrestres. Reportar la mediana y cuántos quedan en el
   top 50. Comparar red contra fórmula base. La gráfica "la red ubica mejor los
   análogos conocidos" es la diapositiva central.
3. **Prueba ciega de Pinacate** con los Montes Marius. Si sale bien, es la escena
   del video. Si sale mal, se cuenta con honestidad y se muestra la mejor validación.
4. **Ablación:** UMAP con y sin discriminador. Sin él los planetas salen separados;
   con él, mezclados por tipo de terreno.
5. **Explicabilidad:** Grad-CAM con objetivo de similitud
   (`SimilarityToConceptTarget` de pytorch-grad-cam) sobre el parche terrestre.

## 13. Cronograma del frente de ML

| Horas | Tarea |
| --- | --- |
| H0 a H4 | Parches (60 m primero) y dataloader. Corrida corta de 2 épocas en H4 |
| H4 a H10 | Entrenamiento completo (y ablación en paralelo o enseguida) |
| H10 a H12 | Embeddings, índice FAISS y metadatos para Backend |
| H12 a H16 | Validación contra la fórmula base y prueba ciega. MVP listo en H16 |
| H16 a H20 | Grad-CAM y UMAP (`galaxy.json`) |
| H20 a H24 | Solo errores y apoyo al pitch. Nada nuevo |

Checkpoints del equipo: H3 (parches de la Luna y México), H8 (entrenamiento
corriendo), H12 (búsqueda de punta a punta), H16 (MVP), H20 (congelamiento), H23 (envío).

## 14. Plan B escalonado

- El contrastivo no converge para H10: usar la ResNet-18 preentrenada congelada
  sobre el sombreado, sin entrenar, con la misma búsqueda.
- Se cae la PC o el internet de casa: Kaggle con el dataset subido.
- Nada de la red sirve: la fórmula base sostiene la demo y la red se presenta como experimento.

## 15. Decisiones tomadas durante el hackathon

- Marte pasó de 200 m/px (blend MOLA-HRSC del USGS) a **500 m/px con MOLA MEGDR del
  PDS**, para que todos los datos salgan de los portales del reto.
- Diviner sube de importancia: los organizadores lo destacan para comparar con
  ambientes fríos o con hielo. Agregar candidatos fríos (Antártida, glaciares).
- LOLA viene en km: multiplicar por 1000. GDAL reporta `Offset: 1737.4` (el radio): NO sumarlo, la altura es el valor crudo.
- Parches guardados como elevación relativa a su media (float16) + `elev_mean_m` en los metadatos.
- Dataloader en `ml/model/` (`channels.py`: 5 canales y aumentaciones en GPU;
  `dataset.py`: lotes balanceados desde memmap). ~6,400 vistas/s, no es el cuello de botella.
- **encoder_v1 (2026-11-14, run `main60`):** 40 épocas, Luna + Tierra, 1.4 min/época.
  Contrastiva 0.92 → 0.086; discriminador 70.6% (época 1) → 49.5% (época 40, azar 50%);
  emb_std estable en ~0.066 (sin colapso). La contrastiva se estancó en ~0.25 en las
  épocas 2 a 12 mientras subía lambda y luego bajó sola. Ablación: run `abl60`.
- **v1 falló como buscador** aunque entrenó "bien": con el discriminador a λ = 1, la
  red borró relieve y pendiente (el polo sur lunar es mucho más abrupto que México:
  mediana de relieve 1,100 m contra 240 m) y sus gemelos quedaron peor que al azar
  en relieve (control de sanidad `ml/sanity_relief.py`: el relieve difiere 5.9x, azar
  5.3x, fórmula base 1.5x). La prueba de 4 épocas de v2 bajó a 1.7x. **No basta
  con que el discriminador llegue a 50%: hay que revisar los gemelos.**
- El control de relieve y pendiente es solo de sanidad (favorece a la fórmula por
  construcción). La evaluación principal es el percentil de los análogos conocidos
  y la prueba ciega de Pinacate, con cuatro métodos: fórmula sola, red sola,
  filtro + red (`hybrid`) y azar.
- El clasificador lineal sobre el índice completo está sesgado si la red conserva
  relieve (las distribuciones de relieve difieren entre cuerpos); comparar también
  con una muestra emparejada por estratos.
- **Un entrenamiento a la vez.** A las 13:53 WSL se reinició (probablemente por
  memoria) con la ablación, la prueba de v2 y descargas corriendo juntas; se perdió
  un archivo recién escrito (`fetch_nasadem.py` quedó vacío). Después de un
  reinicio, revisar que no haya archivos truncados (`git ls-files | xargs wc -c`).
- Datos de agencias asociadas que se pueden citar: Kaguya (JAXA) dentro de
  SLDEM2015; ESA (Copernicus DEM, WorldCover) si se usan. CSA RADARSAT contra
  Mini-RF de LRO queda como extra después de H16.

## 16. Reglas de la entrega que afectan al código y las figuras

- Todo lo que vean los jueces va en inglés (gráficas, etiquetas, README).
- Declarar el uso de IA en la página de envío; imágenes o video generados con IA
  llevan marca de agua; nada generado con IA puede usar marca de la NASA.
- Listar todo recurso externo (datasets, librerías, código de terceros) en las referencias.
