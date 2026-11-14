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

`{scale}` es `60` (Luna contra Tierra) o `500` (Marte contra Tierra).

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

Busca los gemelos terrestres de un sitio de la Luna o de Marte.

**Petición** (`contracts/similar_request.json`):

```json
{"body": "moon", "lat": -89.5, "lon": 130.0, "scale_m": 60, "profile": "rover", "k": 10}
```

**Respuesta** (`contracts/similar_response.json`):

```json
{
  "query": {"body": "moon", "lat": -89.5, "lon": 130.0, "scale_m": 60, "profile": "rover",
            "patch_id": "moon-60-002461"},
  "results": [
    {
      "patch_id": "earth-60-000123", "body": "earth", "lat": 31.77, "lon": -113.5,
      "region": "Sonora, Mexico", "score": 0.87,
      "scores": {"terrain": 0.91, "materials": 0.78, "thermal": 0.35, "operations": 0.88},
      "not_comparable": ["gravity", "vacuum", "radiation"]
    }
  ]
}
```

- `query.patch_id`: el parche de la Luna o de Marte más cercano al punto pedido.
- `score`: total ponderado según el perfil (§4). `scores`: cada dimensión de 0 a 1.
- Una dimensión que todavía no existe (p. ej. `materials` antes de decidirla) va como
  `null` y el frontend la muestra como "no disponible".
- `not_comparable` siempre incluye `gravity`, `vacuum` (en Marte: `atmosphere`) y `radiation`.

## 4. Puntaje por dimensión y perfiles de misión

| Dimensión | Cálculo | Quién lo calcula |
| --- | --- | --- |
| `terrain` | Coseno entre embeddings de la red (FAISS) | ML (índice) + Backend (consulta) |
| `operations` | Pendiente media, fracción del parche bajo 8° (aterrizaje) y bajo 15° (rover), rugosidad | Backend con estadísticas que entrega ML |
| `thermal` | Diferencia normalizada de temperatura máxima, mínima y rango diario (Diviner contra MODIS) | Backend |
| `materials` | Decisión pendiente (`ml/CLAUDE.md` §6.3) | Por definir |

Total = suma ponderada según el perfil (pesos iniciales, ajustables por el equipo):

| Perfil | terrain | materials | thermal | operations |
| --- | --- | --- | --- | --- |
| `rover` | 0.45 | 0.10 | 0.05 | 0.40 |
| `isru` | 0.20 | 0.50 | 0.20 | 0.10 |
| `habitat` | 0.25 | 0.20 | 0.25 | 0.30 |
| `eva` | 0.40 | 0.40 | 0.05 | 0.15 |
| `astrobiology` (solo Marte) | 0.25 | 0.50 | 0.25 | 0.00 |

Si una dimensión es `null`, su peso se reparte proporcionalmente entre las demás.

**Normalización de `operations` (Backend).** El parche se describe con las
estadísticas crudas que ML guarda en `meta_{scale}.parquet` y
`baseline_feat_{scale}.npy`/`.json`: pendiente media (`slope_mean`, grados),
fracción bajo 8° (`slope_frac_0_2 + slope_frac_2_5 + slope_frac_5_8`), fracción
bajo 15° (la anterior `+ slope_frac_8_15`) y rugosidad (`expm1(log_rough_mean)`,
metros). Para un par query/result:

```text
s_slope = exp(-|Δslope_mean| / 10°)
s_land  = exp(-|Δfrac_under_8| / 0.20)
s_rover = exp(-|Δfrac_under_15| / 0.20)
s_rough = exp(-|Δroughness_m| / scale_m)

operations = 0.20*s_slope + 0.25*s_land + 0.30*s_rover + 0.25*s_rough
```

Todas las componentes quedan en 0-1. Si falta cualquiera de las cuatro
estadísticas en alguno de los dos parches, `operations = null`.

**Normalización de `thermal` (Backend).** Se compara `tmax_k`, `tmin_k` y
`trange_k` (Diviner en la Luna, MODIS en la Tierra; Marte sin TES = `null`):

```text
thermal = mean(exp(-|ΔT| / 50 K))  sobre tmax, tmin y rango
```

Si falta `tmax_k` o `tmin_k` en cualquiera de los dos parches, `thermal = null`.

Siempre no comparables: gravedad (Luna 0.17 g, Marte 0.38 g), atmósfera (vacío en la
Luna, ~6 mbar en Marte) y radiación. En la respuesta, `not_comparable` se arma con
los cuerpos del par: Luna→Tierra = `["gravity", "vacuum", "radiation"]`; si el par
involucra Marte se incluye `"atmosphere"`; si involucra Luna y Marte, ambos.

## 5. Otros endpoints (propuesta, a confirmar con Backend y Frontend)

| Endpoint | Devuelve | Para |
| --- | --- | --- |
| `GET /api/health` | `{"status": "ok", "encoder_version": 1}` | Todos |
| `GET /api/galaxy?scale=60` | `galaxy.json` (`contracts/galaxy.example.json`) | Frontend 3D |
| `GET /api/patch/{patch_id}/heights` | Binario Float32 little-endian 128x128 + cabeceras `X-Min`, `X-Max`, `X-M-Per-Px`, `X-Width`, `X-Height`, `X-Dtype`, `X-Endianness` | Frontend 3D |
| `GET /api/gradcam/{query_id}/{patch_id}` | PNG | Frontend UI |

- **`galaxy.json`:** el backend busca primero `galaxy_{scale}.json`, luego
  `galaxy.json` y, si no existen, devuelve el ejemplo de `contracts/` como mock.
  Las escalas válidas son `60`, `500` y `1000`.
- **Alturas:** el cuerpo de la respuesta son los bytes crudos; las cabeceras
  `X-*` son accesibles desde el navegador (CORS las expone). El archivo
  `heights/{patch_id}.json` (con el formato de `contracts/heights.example.json`)
  es el *sidecar* que el backend valida y usa para llenar las cabeceras; no es
  la respuesta HTTP.

## 6. Historial de cambios de contrato

| Fecha | Cambio | Afecta a | Confirmó |
| --- | --- | --- | --- |
| 2026-11-14 | Versión inicial | Todos | — |
| 2026-11-14 | Definir normalización de `operations` y `thermal`, formato binario de `heights` con sidecar, y resolución `galaxy_{scale}.json` → `galaxy.json` → mock | Backend, Frontend, ML | Pendiente |
