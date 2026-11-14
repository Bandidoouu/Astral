# Datos de ASTRAL: fuentes oficiales

**Regla del equipo:** todo dato que use la red, el backend o el frontend sale de los
recursos oficiales que lista el reto. No estamos limitados a ellos, pero **sí tenemos
que usarlos**, y cualquier fuente fuera de la lista se justifica y se cita.
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
| **NASA LRO Diviner** | https://www.diviner.ucla.edu · datos en PDS Geosciences | **Temperatura polar lunar: dimensión `thermal`** (los organizadores lo destacan para comparar con ambientes fríos o con hielo) | ⚠️ **Pendiente, prioridad alta** |
| ESA Copernicus Data Space Ecosystem | https://dataspace.copernicus.eu | Copernicus DEM GLO-30 para análogos fuera de la cobertura de NASADEM (Haughton, Islandia, Valles Secos de McMurdo) | 🔲 Pendiente (validación) |
| ESA Open Science Catalog | https://opensciencedata.esa.int | Opcional | — |
| JAXA G-Portal | https://gportal.jaxa.jp | Opcional: temperatura o nieve de GCOM-C (SGLI) como segunda fuente térmica de sitios fríos | — |
| CSA RADARSAT Constellation (RCM) / RADARSAT-1 | Enlaces en la página del reto | Opcional después de H16: radar SAR terrestre contra Mini-RF de LRO | — |
| CSA SAR Python Tutorial | Enlace en la página del reto | Referencia si se hace lo de RADARSAT | — |

**Mínimo para la entrega:** Earthdata Search, PDS, LRO y **Diviner** (NASA), más al
menos **un recurso de agencia asociada**: Copernicus DEM de la ESA es el más natural
porque ya lo necesitamos para validar.

## 2. Inventario descargado (procedencia verificada)

| Dato | Producto | Portal | Archivo local |
| --- | --- | --- | --- |
| Luna, relieve polar 60 m | LOLA GDR `LDEM_75S_60M` (`LRO-L-LOLA-4-GDR-V1.0`) | PDS Geosciences (LRO) | `data/raw/moon/ldem_75s_60m_float.{img,lbl}` |
| Marte, relieve global 128 px/° | MOLA MEGDR `urn:nasa:pds:mgs_mola_topography_derived:data_meg128` | PDS Geosciences | `data/raw/mars/megt*hb.{img,xml}`, `mars_megdr.vrt` |
| Tierra, relieve 30 m | NASADEM_HGT v001 (411 mosaicos, caja -118, 14, -86, 33) | NASA Earthdata (LP DAAC) | `data/raw/earth/dem/*.zip` → `mexico_{60,500}m.tif` |
| Tierra, temperatura | MODIS Terra MOD11C3 v061, mensual 0.05°, 2023 | NASA Earthdata (LP DAAC) | `data/raw/earth/lst/*.hdf` |

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

```python
# Tierra: NASADEM y MODIS (NASA Earthdata, mismo catálogo que Earthdata Search)
import earthaccess
earthaccess.login(strategy="netrc")
mx = (-118, 14, -86, 33)
dem = earthaccess.search_data(short_name="NASADEM_HGT", bounding_box=mx)
earthaccess.download(dem, "./dem")
lst = earthaccess.search_data(short_name="MOD11C3", temporal=("2023-01-01", "2023-12-31"))
earthaccess.download(lst, "./lst")
```

## 3. Pendientes, en orden de prioridad

1. **Diviner polar (LRO, PDS Geosciences):**
   `https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/`
   (`data_derived_prp/dlre_prp_south.tab` y `data_derived_pcp/`). Sin esto la
   dimensión `thermal` no tiene lado lunar.
2. **SLDEM2015 (LOLA + Kaguya de JAXA, PDS Geosciences):** mosaicos de los Montes
   Marius para la prueba ciega de El Pinacate.
   `https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/sldem2015/`
3. **Copernicus DEM GLO-30 (ESA, Copernicus Data Space):** Haughton, Islandia, Valles
   Secos de McMurdo. **Es nuestro recurso de agencia asociada.**
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

## 5. Fuentes fuera de la lista (permitidas, pero se citan)

| Fuente | Para qué | Nota |
| --- | --- | --- |
| Natural Earth admin-1 (10m) | Nombre del estado/país en `region` (solo etiquetas) | Dominio público; citar en referencias |
| Pesos de ImageNet (torchvision) | Inicialización de la ResNet-18 | Citar en referencias |
| GLiM / mapas geológicos del USGS | Dimensión `materials` | **Decisión pendiente** (`ml/CLAUDE.md` §6.3) |
