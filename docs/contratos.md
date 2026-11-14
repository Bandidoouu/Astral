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

**Requisito central:** el punto de consulta puede estar en **cualquiera de los tres
cuerpos** y se devuelven gemelos en los otros dos (o en los que se pidan).

**Petición** (`contracts/similar_request.json`):

```json
{"body": "moon", "lat": -89.5, "lon": 130.0, "target_bodies": ["earth", "mars"],
 "profile": "rover", "k": 10}
```

| Campo | Obligatorio | Significado |
| --- | --- | --- |
| `body`, `lat`, `lon` | sí | Punto de consulta (`earth`, `moon` o `mars`) |
| `target_bodies` | no | Cuerpos donde buscar. Por defecto, los otros dos |
| `profile` | no | Perfil de misión (§4). Por defecto `rover` |
| `k` | no | Resultados **por cada cuerpo destino**. Por defecto 10 |
| `method` | no | `hybrid` (por defecto), `net`, `baseline`. Solo para depurar y para la demo de validación |

**Ya no se manda `scale_m`:** la escala la decide la regla por par
(origen, destino): **Luna ↔ Tierra a 60 m si el lado lunar está al sur de 80° S;
todo lo demás a 500 m.** Cada resultado dice con qué escala se comparó.

**Cómo lo implementa Backend:** con `ml.search.Searcher` (solo numpy, pandas y
faiss): se crea una vez al arrancar y cada petición llama a
`searcher.search(body, lat, lon, target_bodies, k, profile, method)`, que ya
devuelve este JSON. Método por defecto `hybrid`: la fórmula base preselecciona
~500 candidatos físicamente compatibles y la red los reordena.

**Respuesta** (`contracts/similar_response.json`):

```json
{
  "query": {"body": "moon", "lat": -89.5, "lon": 130.0, "profile": "rover",
            "target_bodies": ["earth", "mars"], "method": "hybrid",
            "patches": {"earth": {"patch_id": "moon-60-002461", "scale_m": 60, "distance_km": 0.4},
                        "mars": {"patch_id": "moon-500-010233", "scale_m": 500, "distance_km": 3.1}}},
  "results": [
    {
      "patch_id": "earth-60-000123", "body": "earth", "lat": 31.77, "lon": -113.5,
      "region": "Sonora, Mexico", "scale_m": 60, "score": 0.87,
      "scores": {"terrain": 0.91, "materials": null, "thermal": null, "operations": 0.88},
      "not_comparable": ["gravity", "vacuum", "radiation"]
    }
  ],
  "warnings": []
}
```

- `query.patches[target]`: el parche del cuerpo de origen que se usó para cada
  destino (puede cambiar de escala según el destino) y su distancia al punto pedido.
- `results`: hasta `k` resultados por cuerpo destino, agrupados por `body` y en orden
  de ranking del método. `scale_m` dice con qué escala se comparó.
- `warnings`: avisos legibles, p. ej. punto fuera de cobertura o índice de 500 m aún
  no disponible. El frontend los muestra, no son errores.
- `score`: total ponderado según el perfil (§4). `scores`: cada dimensión de 0 a 1.
- Una dimensión que todavía no existe (p. ej. `materials` antes de decidirla) va como
  `null` y el frontend la muestra como "no disponible".
- `not_comparable` siempre incluye `gravity`, `vacuum` (si interviene la Luna) o
  `atmosphere` (si interviene Marte) y `radiation`.

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

Siempre no comparables: gravedad (Luna 0.17 g, Marte 0.38 g), atmósfera (vacío en la
Luna, ~6 mbar en Marte) y radiación.

## 5. Otros endpoints (propuesta, a confirmar con Backend y Frontend)

| Endpoint | Devuelve | Para |
| --- | --- | --- |
| `GET /api/health` | `{"status": "ok", "encoder_version": 1}` | Todos |
| `GET /api/galaxy?scale=60` | `galaxy.json` (`contracts/galaxy.example.json`) | Frontend 3D |
| `GET /api/patch/{patch_id}/heights` | Binario Float32 128x128 + cabeceras `X-Min`, `X-Max`, `X-M-Per-Px` | Frontend 3D |
| `GET /api/gradcam/{query_id}/{patch_id}` | PNG | Frontend UI |

## 6. Historial de cambios de contrato

| Fecha | Cambio | Afecta a | Confirmó |
| --- | --- | --- | --- |
| 2026-11-14 | Versión inicial | Todos | — |
| 2026-11-14 | Consulta desde cualquier cuerpo: `target_bodies`, `method`, escala automática por par (se quita `scale_m` de la petición), `query.patches`, `scale_m` por resultado, `warnings`; `region` en inglés ("Sonora, Mexico") | Backend, Frontend | Pendiente |
