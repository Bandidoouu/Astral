# Contratos entre módulos

**Este archivo es la fuente de verdad** de todo lo que un módulo le entrega a otro.
Si el código y este archivo no coinciden, el error está en el código.

- Cada contrato tiene un ejemplo real en `contracts/`. Backend lo usa para
  probar y frontend lo usa como *mock* mientras la API real no esté lista.
- **Cambiar un contrato = protocolo de aviso** (`CLAUDE.md` raíz, §4.1): rama, push,
  PR con el antes/después, aviso al integrante afectado y su confirmación antes de
  fusionar. En el mismo PR se actualizan este archivo y el ejemplo de `contracts/`.
- Convenciones: llaves JSON en **inglés y snake_case**; puntajes de **0 a 1**;
  unidades en **metros y kelvin**; coordenadas en grados, latitud planetocéntrica y
  **longitud de -180 a 180 positiva al este** para los tres cuerpos.

## 1. Artefactos de ML → Backend y Frontend

ML los genera en `data/artifacts/` (fuera de git).

| Archivo | Formato | Lo consume |
| --- | --- | --- |
| `encoder_v{n}.pt` | `state_dict` del encoder (PyTorch). Se carga con `ml.model.net.Encoder` | Backend (solo si embebe consultas nuevas) |
| `emb_{scale}.npy` | float32, N x 128, norma 1, **mismo orden de filas que `meta_{scale}.parquet`** | Backend |
| `index_{scale}.faiss` | `faiss.IndexFlatIP` (producto punto = coseno, búsqueda exacta) | Backend |
| `meta_{scale}.parquet` | Metadatos de todos los parches de esa escala, todos los cuerpos (columnas en §2) | Backend |
| `galaxy.json` | Lista de `{id, body, x, y, z}`: UMAP 3D de una submuestra de ~30 mil parches | Frontend 3D (vía backend o archivo estático) |
| `gradcam/{query_id}__{patch_id}.png` | Mapa de calor sobre el parche terrestre para una consulta | Backend → Frontend UI |
| `heights/{patch_id}.bin` + `.json` | Float32 little-endian 128x128 (elevación absoluta, m) + `{min, max, m_per_px}` | Frontend 3D (vista de detalle) |

`{scale}` es `1000` (escala global, los tres cuerpos) o `60` (detalle Luna ↔ Tierra).

**Cómo llegan los artefactos al backend:** ML los publica con un número de versión
(`encoder_v1`, etc.) y avisa por el chat del equipo. *Pendiente acordar el medio
(zip en Drive o copia por Tailscale desde `astral-gpu`).*

## 2. Metadatos de cada parche (`meta_{scale}.parquet`)

| Columna | Tipo | Significado |
| --- | --- | --- |
| `patch_id` | str | `{body}-{scale}-{6 dígitos}`, p. ej. `earth-60-000123` |
| `body` | str | `earth`, `moon` o `mars` |
| `scale_m` | int | Tamaño de píxel en metros (60 o 500) |
| `lat`, `lon` | float | Centro del parche, grados |
| `crs`, `x`, `y` | str, float | Proyección nativa y centro en metros |
| `region` | str | Nombre legible (estado/país en la Tierra; región en la Luna o Marte) |
| `holdout` | bool | `True` = fuera del entrenamiento (prueba ciega de El Pinacate) |
| `elev_mean_m`, `elev_min_m`, `elev_max_m` | float | Elevación del parche, metros |

## 3. API: `POST /api/similar`

**Requisito central:** el usuario hace clic en **cualquier punto** de la Tierra, la
Luna o Marte y recibe gemelos en los otros dos cuerpos (o en los que pida).

**Petición** (`contracts/similar_request.json`):

```json
{"body": "moon", "lat": -89.5, "lon": 130.0, "target_bodies": ["earth", "mars"],
 "scale_m": 1000, "profile": "general", "k": 10}
```

| Campo | Obligatorio | Significado |
| --- | --- | --- |
| `body`, `lat`, `lon` | sí | Punto de consulta (`earth`, `moon` o `mars`) |
| `target_bodies` | no | Cuerpos donde buscar. Por defecto, los otros dos |
| `scale_m` | no | `1000` (por defecto): escala global, parches de 128 km, los tres cuerpos, cualquier punto. `60`: detalle, parches de 7.68 km, **solo Luna ↔ Tierra y solo dentro de su cobertura** (Luna al sur de 80° S; Tierra en la caja de México, -118 a -86° y 14 a 33°) |
| `profile` | no | Perfil de misión (§4). Por defecto `rover` |
| `k` | no | Resultados **por cada cuerpo destino**. Por defecto 10 |
| `method` | no | `hybrid` (por defecto), `net`, `baseline`. Solo para depurar y para la demo de validación |

**Cada búsqueda indica su escala** en `scale_m`. Si se pide 60 fuera de su
cobertura, o con Marte como origen o destino, **no se inventan resultados**: ese
destino vuelve vacío con un aviso en `warnings`, y el frontend puede ofrecer
repetir la búsqueda a 1000. Cada resultado repite su `scale_m`.

**Cómo lo implementa Backend:** con `ml.search.Searcher` (solo numpy, pandas y
faiss): se crea una vez al arrancar y cada petición llama a
`searcher.search(body, lat, lon, target_bodies, k, profile, method, scale_m=scale_m)`, que ya
devuelve este JSON. Método por defecto `hybrid`: la fórmula base preselecciona
~500 candidatos físicamente compatibles y la red los reordena.

**Respuesta** (`contracts/similar_response.json`):

```json
{
  "query": {"body": "moon", "lat": -89.5, "lon": 130.0, "profile": "rover", "scale_m": 1000,
            "target_bodies": ["earth", "mars"], "method": "hybrid",
            "patches": {"earth": {"patch_id": "moon-1000-002461", "scale_m": 1000, "distance_km": 21.4},
                        "mars": {"patch_id": "moon-1000-002461", "scale_m": 1000, "distance_km": 21.4}}},
  "results": [
    {
      "patch_id": "earth-1000-004123", "body": "earth", "lat": 31.77, "lon": -113.5,
      "region": "Sonora, Mexico", "scale_m": 1000, "score": 0.81,
      "scores": {"terrain": 0.91, "operations": 0.88, "thermal": 0.42, "albedo": null},
      "no_data": ["albedo"],
      "weights_used": {"terrain": 0.5, "operations": 0.444, "thermal": 0.056},
      "attributes": {"tmax_k": 331.2, "tmin_k": 268.9, "trange_k": 62.3, "albedo": null,
                     "ice_distance_km": null},
      "not_comparable": ["gravity", "vacuum", "radiation"]
    }
  ],
  "warnings": []
}
```

- `query.patches[target]`: el parche del cuerpo de origen que se usó para cada
  destino y su distancia al punto pedido (a 1000 m, el centro de parche más cercano
  puede estar a decenas de km: los parches miden 128 km).
- `results`: hasta `k` resultados por cuerpo destino, agrupados por `body` y en orden
  de ranking del método. `scale_m` dice con qué escala se comparó.
- `warnings`: avisos legibles, p. ej. punto fuera de cobertura o índice de 500 m aún
  no disponible, o escala de 60 m pedida fuera de cobertura. El frontend los
  muestra, no son errores.
- **Requisito central: la búsqueda no es solo de forma.** La red se encarga
  únicamente de `terrain`; las demás dimensiones se calculan aparte con datos de los
  portales oficiales (§4).
- `scores`: cada dimensión de 0 a 1, **o `null` = "sin dato"** (no hay medición en
  alguno de los dos lugares). **Nunca se inventa un valor.** `no_data` lista las
  dimensiones en `null`; el frontend las muestra como "Sin dato" / "No data".
- `score`: total ponderado por el perfil (§4) **solo con las dimensiones que tienen
  dato**; sus pesos se renormalizan y se devuelven en `weights_used`.
- `attributes`: valores crudos del parche resultado (kelvin, albedo sin unidades,
  km), también `null` si faltan. `query.attributes` trae los del punto consultado.
- `not_comparable` siempre incluye `dust_and_wind`, `subsurface`, `gravity`,
  `vacuum` (si interviene la Luna) o `atmosphere` (si interviene Marte) y `radiation`.

## 4. Puntaje por dimensión y perfiles de misión

| Dimensión | Cálculo | Datos |
| --- | --- | --- |
| `terrain` | Ranking de forma: **fusión RRF** (k = 60 fijo) de la red y la fórmula base; el puntaje mostrado es el coseno de la red | Red de ASTRAL + fórmula base |
| `operations` | Parecido de pendiente media, fracción del parche bajo 8° (aterrizaje) y bajo 15° (rover) y rugosidad | El relieve de cada parche |
| `thermal` | Parecido de temperatura máxima, mínima y rango: `exp(-|ΔT| / 50 K)` promediado | Tierra: MODIS MOD11C3 (LST 2023). Luna: Diviner (PRP polar + GCP global). Marte: TES (bloque 4) |
| `albedo` | Parecido de albedo: `exp(-|Δalbedo| / 0.1)` | Tierra: MODIS MCD43C3 (infrarrojo cercano). Luna: LOLA `ldam` (1064 nm). Marte: TES |
| `ice` | Parecido de la fracción de hielo: `exp(-|Δ| / 0.2)` | Tierra: nieve y hielo de MODIS MOD10CM (promedio anual). Luna: hielo estable **en superficie** de Diviner (PRP en el polo; máxima < 110 K de la GCP en el resto). Marte: hidrógeno de Mars Odyssey (bloque 4) |
| `soil` (roca contra polvo) | Percentil de "rocosidad" **dentro de cada cuerpo**, `1 - |Δpercentil|` (son magnitudes físicas distintas) | Tierra: inercia térmica aparente de MODIS, (1 − albedo) / (T día − T noche). Luna: abundancia de rocas de Diviner (solo entre 60° N y 60° S). Marte: inercia térmica de TES |
| `aridity` | Parecido de precipitación anual: `exp(-|ΔP| / 250 mm)` | Tierra: NASA GPM IMERG 2023. Luna y Marte: 0 mm por definición física (sin precipitación líquida) |
| ~~`materials`~~ | Minerales: fuera de alcance; deseable (EMIT contra CRISM, solo Tierra–Marte) | — |

**Atributos solo del sitio** (no son una comparación): `ice_distance_km` en la Luna,
distancia a las zonas donde Diviner indica hielo estable a ≤ 1 m de profundidad.

Los atributos por parche salen de `features_{scale}.parquet` y son los que se
devuelven en `attributes`: `tmax_k`, `tmin_k`, `trange_k`, `albedo`,
`ice_distance_km`, `ice_frac`, `soil_raw`, `soil_pct` y `precip_mm`.

**Normalización de `operations` (Backend).** Con `w = {pendiente media: 0.20,
fracción < 8°: 0.25, fracción < 15°: 0.30, rugosidad: 0.25}`:

```text
exp(-|Δpendiente_media| / 10°) * 0.20
+ exp(-|Δfracción_<8°| / 0.20) * 0.25
+ exp(-|Δfracción_<15°| / 0.20) * 0.30
+ exp(-|Δrugosidad| / scale_m) * 0.25
```

Total = suma ponderada según el perfil **con las dimensiones que tienen dato**
(pesos iniciales, ajustables por el equipo):

**Perfil por defecto: `general`, todas las dimensiones con el mismo peso.** Ningún
perfil le da más de 0.3 al terreno.

| Perfil | terrain | operations | thermal | albedo | ice | soil | aridity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **`general`** (por defecto) | 1/7 | 1/7 | 1/7 | 1/7 | 1/7 | 1/7 | 1/7 |
| `rover` | 0.30 | 0.30 | 0.05 | 0.05 | 0.05 | 0.15 | 0.10 |
| `isru` | 0.10 | 0.10 | 0.10 | 0.15 | 0.35 | 0.15 | 0.05 |
| `habitat` | 0.15 | 0.25 | 0.25 | 0.05 | 0.15 | 0.10 | 0.05 |
| `eva` | 0.30 | 0.20 | 0.05 | 0.15 | 0.05 | 0.20 | 0.05 |
| `astrobiology` | 0.10 | 0.00 | 0.15 | 0.10 | 0.30 | 0.10 | 0.25 |

## 4b. Capa de aptitud para base (polo sur lunar; Marte después)

Reglas transparentes, **no la red**. Cada criterio de 0 a 1 con pesos visibles; ML
exporta un raster por criterio y uno del total en `data/artifacts/suitability/`
(GeoTIFF en estereográfica polar sur + PNG para el frontend + JSON con pesos, reglas
y el puntaje de los candidatos de la NASA). **Es una sugerencia, no una elección
final:** faltan iluminación y visibilidad de la Tierra, que no están en los portales.

**Lo que nunca se puede comparar** (va en `not_comparable` de cada resultado):
`dust_and_wind` (polvo y viento), `subsurface` (subsuelo), `gravity` (Luna 0.17 g,
Marte 0.38 g), `vacuum` o `atmosphere` (vacío en la Luna, ~6 mbar en Marte) y
`radiation`. La lista se elige por el cuerpo no terrestre del par, igual que
`ml.search.NOT_COMPARABLE`: la Luna aporta `vacuum` y Marte (o la Tierra) aporta
`atmosphere`; `dust_and_wind`, `subsurface`, `gravity` y `radiation` van siempre.

## 5. Otros endpoints (propuesta, a confirmar con Backend y Frontend)

| Endpoint | Devuelve | Para |
| --- | --- | --- |
| `GET /api/health` | `{"status": "ok", "encoder_version": 1}` | Todos |
| `GET /api/galaxy?scale=60` | `galaxy.json` (`contracts/galaxy.example.json`) | Frontend 3D |
| `GET /api/patch/{patch_id}/heights` | Binario Float32 128x128 + cabeceras `X-Min`, `X-Max`, `X-M-Per-Px` | Frontend 3D |
| `GET /api/gradcam/{query_id}/{patch_id}` | PNG | Frontend UI |

- **`galaxy`**: se busca `galaxy_{scale}.json`; si no existe, `galaxy.json`; si
  tampoco, el ejemplo de `contracts/`. Así el frontend nunca se queda sin globos.
- **`heights`**: el cuerpo es Float32 little-endian, 128×128, con las cabeceras
  `X-Min`, `X-Max` y `X-M-Per-Px`; `contracts/heights.example.json` documenta el
  mismo formato como sidecar. Sin cabeceras válidas se responde 500, no un binario
  a medias.

## 6. Historial de cambios de contrato

| Fecha | Cambio | Afecta a | Confirmó |
| --- | --- | --- | --- |
| 2026-11-14 | Versión inicial | Todos | — |
| 2026-11-14 | Dimensiones `ice`, `soil`, `aridity`; perfil por defecto `general` (pesos iguales; terreno ≤ 0.3 en todos los perfiles); `not_comparable` agrega `dust_and_wind` y `subsurface` | Backend, Frontend | Pendiente |
| 2026-11-14 | `scores` con `terrain`, `operations`, `thermal`, `albedo` (sale `materials`); `null` = sin dato, `no_data`, `weights_used`, `attributes`; ranking de terreno por fusión RRF; capa de aptitud lunar (§4b) | Backend, Frontend | Pendiente |
| 2026-11-14 | Consulta desde cualquier punto de cualquier cuerpo: `target_bodies`, `method`, `scale_m` en la petición (1000 global por defecto, 60 de detalle solo dentro de cobertura; reemplaza a la escala de 500 m), `query.patches`, `scale_m` por resultado, `warnings`; `region` en inglés ("Sonora, Mexico") | Backend, Frontend | Pendiente |
| 2026-11-14 | Normalización explícita de `operations`; atributos por parche en `features_{scale}.parquet`; formato binario de `heights` con sidecar; resolución `galaxy_{scale}.json` → `galaxy.json` → ejemplo | Backend, Frontend, ML | Pendiente |
