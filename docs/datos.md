# Datos de ASTRAL: fuentes oficiales

**Regla del equipo:** todo dato que use la red, el backend o el frontend sale de los
recursos que lista el reto. No estamos limitados a ellos, y cualquier fuente fuera
de la lista se justifica y se cita.

**Lo único obligatorio es usar datos de la NASA, y ya se cumple** (LOLA, MOLA,
NASADEM y MODIS). Diviner y los recursos de agencias asociadas (ESA, JAXA, CSA)
**no son obligatorios**: suman porque los organizadores los destacan, pero son
opcionales.
Antes de bajar algo nuevo, agrégalo a este archivo con su portal, su enlace y el
comando exacto (reproducibilidad = puntos de *Validity*).

> Aviso del reto: la NASA no respalda entidades que no sean del gobierno de EE. UU.
> Para sitios que no son de la NASA (ESA, JAXA, CSA) hay que respetar sus propias
> condiciones de uso de datos.

## 1. Lista oficial del reto y cómo la usamos

| Recurso oficial | Enlace | Uso en ASTRAL | Estado |
| --- | --- | --- | --- |
| **NASA Earthdata Search** | https://search.earthdata.nasa.gov | Relieve de la Tierra (NASADEM) y temperatura (MODIS MOD11C3) | ✅ Descargado |
| **NASA Worldview** | https://worldview.earthdata.nasa.gov | Imagen satelital real de cada análogo en la tarjeta de resultados (frontend) | 🔲 Pendiente (frontend) |
| **NASA PDS** | https://pds.nasa.gov · nodo de Geociencias: https://pds-geosciences.wustl.edu | Relieve de Marte (MOLA MEGDR) y de la Luna (LOLA) | ✅ Descargado |
| **NASA LRO** | https://lunar.gsfc.nasa.gov | LOLA (relieve polar 60 m); Mini-RF (radar) como extra | ✅ LOLA descargado |
| **NASA LRO Diviner** | https://www.diviner.ucla.edu · datos en PDS Geosciences | Temperatura polar lunar para la dimensión `thermal` (los organizadores lo destacan para comparar con ambientes fríos o con hielo; opcional) | ⏳ Descargando (PRP sur) |
| ESA Copernicus Data Space Ecosystem | https://dataspace.copernicus.eu | Copernicus DEM GLO-30 para análogos fuera de la cobertura de NASADEM (Haughton, Islandia, Valles Secos de McMurdo) | 🔲 Pendiente (validación) |
| ESA Open Science Catalog | https://opensciencedata.esa.int | Opcional | — |
| JAXA G-Portal | https://gportal.jaxa.jp | Opcional: temperatura o nieve de GCOM-C (SGLI) como segunda fuente térmica de sitios fríos | — |
| CSA RADARSAT Constellation (RCM) / RADARSAT-1 | Enlaces en la página del reto | Opcional después de H16: radar SAR terrestre contra Mini-RF de LRO | — |
| CSA SAR Python Tutorial | Enlace en la página del reto | Referencia si se hace lo de RADARSAT | — |

**Mínimo para la entrega:** datos de la NASA (ya se cumple con Earthdata y PDS/LRO).
Diviner y las agencias asociadas son opcionales. **Ya usamos datos de JAXA** sin
pasar por G-Portal: SLDEM2015 combina LOLA con la cámara de terreno de Kaguya
(SELENE) de JAXA, y así se cita. Copernicus DEM de la ESA se agregaría solo si
validamos con análogos fuera de la cobertura de NASADEM.

## 2. Inventario descargado (procedencia verificada)

| Dato | Producto | Portal | Archivo local |
| --- | --- | --- | --- |
| Luna, relieve polar 60 m | LOLA GDR `LDEM_75S_60M` (`LRO-L-LOLA-4-GDR-V1.0`) | PDS Geosciences (LRO) | `data/raw/moon/ldem_75s_60m_float.{img,lbl}` |
| Marte, relieve global 128 px/° | MOLA MEGDR `urn:nasa:pds:mgs_mola_topography_derived:data_meg128` | PDS Geosciences | `data/raw/mars/megt*hb.{img,xml}`, `mars_megdr.vrt` |
| Tierra, relieve 30 m | NASADEM_HGT v001 (411 mosaicos, caja -118, 14, -86, 33) | NASA Earthdata (LP DAAC) | `data/raw/earth/dem/*.zip` → `mexico_{60,500}m.tif` |
| Tierra, temperatura | MODIS Terra MOD11C3 v061, mensual 0.05°, 2023 | NASA Earthdata (LP DAAC) | `data/raw/earth/lst/*.hdf` |

| Luna, temperatura polar sur | Diviner PRP sur, `dlre_prp_south` (`urn:nasa:pds:lro_diviner_derived1`) | PDS Geosciences (LRO) | `data/raw/moon/diviner/dlre_prp_south.{tab,xml,lbl}` |
| Luna, relieve latitudes medias 512 px/° (~59 m) | SLDEM2015 (LOLA + Kaguya TC de **JAXA**): mosaicos `00n_30n_270_315` (Montes Marius), `00n_30n_000_045` (Mare Tranquillitatis), `30n_60n_315_360` (Mare Imbrium) | PDS Geosciences (LRO) | `data/raw/moon/sldem2015/sldem2015_512_*_float.{img,lbl,xml}` |

| Luna, relieve global 64 px/° (~474 m) | LOLA GDR cilíndrico `ldem_64_float` (km) | PDS Geosciences (LRO) | `data/raw/moon/lola_global/ldem_64_float.{img,lbl,xml}` |
| Tierra, análogos conocidos | NASADEM_HGT: Arizona (Meteor Crater y campo volcánico de San Francisco, caja -112.4, 34.7, -110.6, 35.8) y Death Valley (-117.5, 35.8, -116.4, 37.0) | NASA Earthdata | `data/raw/earth/analogs/{arizona,deathvalley}/` |

| Tierra, relieve global 30" (~0.93 km) | SRTMGL30 v002, 27 mosaicos. **Cobertura real: de 90° N a 60° S, sin Antártida** (los metadatos de la colección dicen 60° N a 56° S, lo medido por SRTM; al norte de 60° N viene rellenado con GTOPO30). Enteros de 16 bits big-endian, sin cabecera; **el océano vale 0** (no NoData) | NASA Earthdata (LP DAAC) | `data/raw/earth/srtmgl30/` (`dem/*.DEM` + `.HDR` que escribimos, `srtmgl30.vrt`) |

| Luna, temperatura global | Diviner GCP (`global_cumul_avg_cyl_*_002`, 18 tablas, celdas de 0.5°, temperatura bolométrica en 96 horas locales) | PDS Geosciences (LRO) | `data/raw/moon/diviner_gcp/` |
| Luna, albedo | LOLA `ldam_50s_1000m_float` (polo sur, 1 km) y `ldam_10_float` (global, 10 px/°): **son albedo** (el `.lbl` dice "albedo map (brightness)", 1064 nm) | PDS Geosciences (LRO) | `data/raw/moon/lola_albedo/` |
| Tierra, albedo | MODIS MCD43C3 v061, un día por mes de 2023 (12 × 177 MB), albedo de cielo blanco bandas 2 y 5 | NASA Earthdata (LP DAAC) | `data/raw/earth/albedo/` |
| Tierra, cobertura del suelo (zonas prometedoras) | MODIS MCD12C1 v061, anual 0.05°, 2023, clase IGBP mayoritaria (`Majority_Land_Cover_Type_1`), 1.2 GB | NASA Earthdata (LP DAAC) | `data/raw/earth/landcover/MCD12C1.A2023001*.hdf` |
| Marte, hidrógeno (agua equivalente) | Mars Odyssey GRS, `ody-m-grs-5-elements-v1`, mapa suavizado 5x5° `h2o_sr_5x5` (% en peso de H2O equivalente, Boynton et al. 2007) | PDS Geosciences | `data/raw/mars/grs/h2o_sr_5x5.{tab,lbl}` |

**Diviner GDR L3** (`data_derived_gdr_l3/cylindrical`) trae abundancia de rocas y
temperaturas **nocturnas** del regolito, no la máxima diurna; por eso la temperatura
lunar global sale de la **GCP** (máxima, mínima y rango sobre las 96 horas locales).
La PRP sur no trae temperatura mínima: en el polo la mínima también sale de la GCP.
El GDAL de rasterio no lee HDF4 (MODIS): se convierte con el `gdal_translate` del sistema.

**Escala global de 1 km:** Tierra con SRTMGL30; Luna con LOLA `ldem_64_float` promediado
a ~950 m (**LOLA no publica una versión de 32 px/°**: solo 4, 16, 64, 128, 256, 512 y
1024); Marte con MOLA MEGDR 128 px/° promediado a ~930 m. No hizo falta bajar nada más.

**Fuera de la lista oficial, apartado:** `data/raw/_no_oficial/jezero.tif` (blend
MOLA-HRSC del USGS). No se usa.

### Comandos exactos con los que se bajó

```bash
# Luna: LOLA polar 60 m (PDS Geosciences)
B=https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/float_img
wget -c $B/ldem_75s_60m_float.img $B/ldem_75s_60m_float.lbl

# Marte: MOLA MEGDR 128 px/grado (PDS Geosciences)
B=https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg128
for lat in 88n 44n 00n 44s; do for lon in 000 090 180 270; do
  wget -c $B/megt${lat}${lon}hb.img $B/megt${lat}${lon}hb.xml; done; done
```

```bash
# Luna: Diviner, producto polar del sur (PDS Geosciences)
B=https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp
wget -c $B/dlre_prp_south.tab $B/dlre_prp_south.xml $B/dlre_prp_south.lbl

# Luna: SLDEM2015, Montes Marius + dos mares (PDS Geosciences; incluye Kaguya de JAXA)
B=https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/sldem2015/tiles/float_img
for t in 00n_30n_270_315 00n_30n_000_045 30n_60n_315_360; do for e in img lbl xml; do
  wget -c $B/sldem2015_512_${t}_float.$e; done; done
```

```bash
# Luna: LOLA global cilíndrico 64 px/grado, en km (PDS Geosciences)
B=https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/float_img
wget -c $B/ldem_64_float.lbl $B/ldem_64_float.xml $B/ldem_64_float.img

# Tierra: NASADEM alrededor de análogos conocidos (NASA Earthdata)
python -m ml.data.fetch_nasadem --name arizona --bbox -112.4 34.7 -110.6 35.8
python -m ml.data.fetch_nasadem --name deathvalley --bbox -117.5 35.8 -116.4 37.0
```

```bash
# Tierra: SRTMGL30 global (NASA Earthdata) + cabeceras EHdr para que GDAL lea los .DEM
python -c "import earthaccess as e; e.login(strategy='netrc'); e.download(e.search_data(short_name='SRTMGL30'), 'data/raw/earth/srtmgl30')"
cd data/raw/earth/srtmgl30 && mkdir -p dem && for z in *.zip; do unzip -o -q $z -d dem; done
# por cada dem/XNNNYMM.DEM: .HDR con BYTEORDER M, NROWS 6000, NCOLS 4800, NBITS 16,
# PIXELTYPE SIGNEDINT, NODATA -9999, ULXMAP lon+1/240, ULYMAP lat-1/240, XDIM=YDIM=1/120
gdalbuildvrt -a_srs EPSG:4326 srtmgl30.vrt dem/*.DEM
```

```python
# Tierra: NASADEM y MODIS (NASA Earthdata, mismo catálogo que Earthdata Search)
import earthaccess
earthaccess.login(strategy="netrc")
mx = (-118, 14, -86, 33)
dem = earthaccess.search_data(short_name="NASADEM_HGT", bounding_box=mx)
earthaccess.download(dem, "./dem")
lst = earthaccess.search_data(short_name="MOD11C3", temporal=("2023-01-01", "2023-12-31"))
earthaccess.download(lst, "./lst")
lc = earthaccess.search_data(short_name="MCD12C1", version="061", temporal=("2023-01-01", "2023-01-02"))
earthaccess.download(lc, "./landcover")
```

## 3. Pendientes, en orden de prioridad

1. ~~Diviner PRP sur~~ y ~~SLDEM2015 (Marius + mares)~~: descargándose (§2).
   Falta procesarlos: Diviner → dimensión `thermal`; SLDEM2015 → parches de la prueba ciega.
2. Diviner `data_derived_pcp/` (productos polares acumulados), si el PRP no alcanza.
3. **Copernicus DEM GLO-30 (ESA, opcional):** Haughton, Islandia, Valles Secos de
   McMurdo, solo si validamos fuera de la cobertura de NASADEM.
4. **NASADEM alrededor de análogos conocidos** (Earthdata): Meteor Crater, Death
   Valley, Atacama, Mauna Kea, Lonar, campo volcánico de San Francisco.
5. **Worldview / GIBS (frontend):** imagen real de cada análogo para las tarjetas.

## 4. Imágenes y texturas del frontend

Las texturas de los globos y las imágenes de las tarjetas también deben salir de
fuentes oficiales:

- **Tierra:** NASA Worldview / GIBS (p. ej. Blue Marble o color verdadero MODIS/VIIRS).
- **Luna:** mosaicos de LRO (LROC WAC) o un sombreado hecho por nosotros con LOLA.
- **Marte:** sombreado hecho por nosotros con MOLA MEGDR, o mosaicos del PDS.

Nada generado con IA puede usar marca de la NASA; imágenes generadas con IA llevan
marca de agua (reglas del reto).

**Texturas de los globos (descargadas, en `frontend/public/textures/{earth,moon,mars}/`,
detalle en su `README.md`; fuentes crudas en `data/raw/textures/`, fuera de git):**

| Cuerpo | Capa | Fuente | Enlace |
| --- | --- | --- | --- |
| Luna | Color | NASA SVS *CGI Moon Kit* (id 4720): mosaico de color LROC WAC con polos rellenos, `lroc_color_poles_8k.tif` | https://svs.gsfc.nasa.gov/4720 |
| Marte | Color | NASA Mars Trek, `Mars_Viking_MDIM21_ClrMosaic_global_232m` (mosaico Viking a color), teselas WMTS nivel 4 (32 × 16) | https://trek.nasa.gov/mars/ |
| Tierra | Color | NASA GIBS WMS, capa `BlueMarble_NextGeneration` (Blue Marble, NASA Earth Observatory) | https://gibs.earthdata.nasa.gov |
| Los tres | Altura, normales, sombreado, topografía | Hechos por nosotros con LOLA `ldem_64`, MOLA MEGDR y SRTMGL30 (ya en el inventario) | — |
| Luna, Marte | Aptitud | Nuestras capas de aptitud (`ml/suitability_moon.py`, `ml/suitability_mars.py`) | — |


## 4b. Contexto físico de "Where the analogy stops" (frontend)

Valores tal como los publican las fuentes (citas textuales), en `frontend/src/ui/planetFacts.ts`:

| Dato | Tierra | Luna | Marte | Fuente |
| --- | --- | --- | --- | --- |
| Gravedad en superficie | 9.820 m/s² (media) | 1.62 m/s² | 3.73 m/s² (media) | NASA Planetary Fact Sheets: https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html, …/moonfact.html (tabla comparativa), …/marsfact.html |
| Presión en superficie | 1014 mb | 3 × 10⁻¹⁵ bar (noche) | 6.36 mb al radio medio (4.0 a 8.7 mb según estación) | Ídem |
| Duración del día | 24.0000 h | 708.7 h (tabla comparativa) | 24.6597 h | Ídem; la Luna, de https://nssdc.gsfc.nasa.gov/planetary/factsheet/ |
| Dosis de radiación en superficie | pendiente | 1369 μSv/día (dosis equivalente) | pendiente | Luna: Zhang et al. 2020, *First measurements of the radiation dose on the lunar surface*, Sci. Adv. 6, eaaz1334, doi:10.1126/sciadv.aaz1334 (texto completo abierto: PMC7518862): "LND measured an average dose equivalent of 1369 μSv/day on the surface of the Moon". El mismo artículo compara con **LRO/CRaTER**: "CRaTER measured a dose rate of 13.29 μGy/hour (reported by the CRaTER team as converted to water and to the lunar surface) … while LND measured … 13.2 ± 1.4 μGy/hour converted to water" |

- **Marte (MSL/RAD):** la referencia es Hassler et al. 2014, Science 343, 1244797
  (doi:10.1126/science.1244797; NTRS 20180007641), pero su resumen no trae la cifra y el texto
  completo no fue accesible en la sesión (science.org y las revistas de los artículos de
  comparación bloquean la descarga automática). La celda queda **"pending citation"** hasta
  copiar la cifra de una fuente verificada; no se usa un valor de memoria.
- **Tierra:** igual, sin dosis de referencia verificada (UNSCEAR y NRC bloquean la descarga).
- **Presión del sitio terrestre:** fórmula barométrica estándar (atmósfera estándar ISA,
  troposfera): p = 1013.25 hPa · (1 − 2.25577·10⁻⁵ · h)^5.25588, con h = elevación del sitio
  en el mapa de altura NASA SRTMGL30 que usa el globo (rejilla de ~10 km). Se muestra como
  "closest Earth gets".
- Polvo y viento, y subsuelo: etiquetas sin número ("not modeled; future work").

## 5. Fuentes fuera de la lista (permitidas, pero se citan)

- **Gazetteer of Planetary Nomenclature (IAU WGPSN / USGS Astrogeology), puntos centrales
  de la Luna y Marte** (`MOON_nomenclature_center_pts.zip`, `MARS_nomenclature_center_pts.zip`,
  https://planetarynames.wr.usgs.gov): solo para nombrar regiones legibles en la Luna y
  Marte (p. ej. "Mare Imbrium"). Es la nomenclatura oficial de la IAU, publicada por el
  USGS; no aporta datos al modelo. Archivo local: `data/raw/nomenclature/`.

| Fuente | Para qué | Nota |
| --- | --- | --- |
| Natural Earth admin-1 (10m), `https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip` | `region` = "Estado, País" y columna `country` (`ml/data/add_regions.py`) | Dominio público; descargado en `data/raw/earth/naturalearth/`; citar en referencias |
| Pesos de ImageNet (torchvision) | Inicialización de la ResNet-18 | Citar en referencias |
| GLiM / mapas geológicos del USGS | Dimensión `materials` | **Decisión pendiente** (`ml/CLAUDE.md` §6.3) |
