# ASTRAL · Módulo `backend/` (API FastAPI)

Las reglas generales del equipo están en el `CLAUDE.md` de la raíz (qué es ASTRAL,
aviso de cambios, nada de co-autores de IA) y **también aplican aquí**.

## 1. Quién y qué

- **Dueños:** Angel, Tamara, Ethan. ML (Esteban + Claude) también puede modificar
  este módulo, avisando con el protocolo §4.1 del `CLAUDE.md` raíz.
- **Responsabilidad:** servir los resultados de la red al frontend. Carga los
  artefactos de ML, busca los gemelos en FAISS, calcula los puntajes por dimensión
  y por perfil de misión, y expone los endpoints de `docs/contratos.md` §3 y §5.
- **No hace:** entrenar, regenerar embeddings ni cambiar el índice. Si algo de eso
  hace falta, se le pide a ML.

## 1b. Lo que cambió (requisitos centrales, ver `docs/contratos.md`)

- **Clic en cualquier punto de cualquier cuerpo:** la petición trae `body`, `lat`,
  `lon` y opcionalmente `target_bodies` (por defecto, los otros dos cuerpos).
- **Escala en cada búsqueda:** `scale_m` = `1000` (global, los tres cuerpos, por
  defecto) o `60` (detalle, solo Luna ↔ Tierra y solo dentro de su cobertura: Luna al
  sur de 80° S, Tierra en la caja -118 a -86° y 14 a 33°). Fuera de cobertura no se
  inventan resultados: ese destino vuelve vacío con un aviso en `warnings`.
- **La búsqueda no es solo de forma:** `scores` trae `terrain`, `operations`,
  `thermal` y `albedo` por separado. **`null` = "sin dato"**; no cuenta en el total y
  los pesos usados vienen en `weights_used`. `materials` ya no existe.
- **Capa de aptitud lunar** (reglas transparentes): rasters del polo sur por
  criterio y total, más un JSON con pesos, reglas y candidatos de la NASA.

### Cómo implementar `POST /api/similar`

No reimplementen la búsqueda: usen `ml.search.Searcher` (solo numpy, pandas y faiss).

```python
from ml.search import Searcher
searcher = Searcher()            # una vez al arrancar; lee data/artifacts/

@app.post("/api/similar")
def similar(req: SimilarRequest):
    return searcher.search(req.body, req.lat, req.lon, req.target_bodies, req.k,
                           req.profile, method="rrf", scale_m=req.scale_m)
```

Devuelve ya el JSON del contrato. El ranking de terreno por defecto es la fusión
RRF de la red y la fórmula base (`method="rrf"`).

### Artefactos que lee el `Searcher` (en `data/artifacts/`, por escala)

`meta_{scale}.parquet`, `emb_{scale}.npy`, `baseline_feat_{scale}.npy` + `.json` y
`features_{scale}.parquet` (temperatura, albedo, hielo). Hoy existe la escala 60;
la de 1000 llega con el modelo global. Si falta una escala, el `Searcher` responde
con un aviso en `warnings`, no con un error.

### Capa de aptitud lunar (`data/artifacts/suitability/`)

`moon_south_{landing,rover,ice,temperature,total}.tif` (GeoTIFF, estereográfica polar
sur de LOLA, 480 m) y `.png` (para mostrar directo), más `suitability_moon.json` (pesos,
reglas, candidatos de la NASA y sus puntajes). Endpoint sugerido:
`GET /api/suitability/moon_south/{criterion}` (PNG) y `GET /api/suitability/moon_south`
(el JSON).

## 2. Estructura

```text
backend/
├── app/
│   ├── main.py          # crea la app FastAPI, CORS, incluye los routers
│   ├── api/             # routers: similar.py, galaxy.py, patches.py, health.py
│   ├── services/        # lógica: search.py (FAISS), scoring.py (dimensiones y perfiles),
│   │                    #         thermal.py (Diviner/MODIS), artifacts.py (carga única)
│   └── core/            # config.py: rutas y variables de entorno
├── tests/               # pruebas contra los ejemplos de contracts/
└── requirements.txt     # fastapi, uvicorn, faiss-cpu, numpy, pandas, pyarrow
```

## 3. Reglas del módulo

- **Los formatos salen de `docs/contratos.md`.** Las respuestas deben validar contra
  los ejemplos de `contracts/`; hay que tener una prueba que lo verifique.
- **Arrancar con mocks:** hasta que ML entregue artefactos (H10 a H12), los
  endpoints devuelven los ejemplos de `contracts/`. Así el frontend avanza sin esperar.
- Los artefactos se leen desde `ASTRAL_ARTIFACTS` (por defecto `../data/artifacts`).
  Se cargan **una sola vez** al arrancar (no en cada petición).
- Si el backend necesita un campo nuevo de ML (p. ej. otra estadística por parche),
  se pide con el protocolo de aviso; no se calcula por fuera con otra fórmula.
- Nada de rutas absolutas en el código. CORS abierto para el servidor de desarrollo
  del frontend.
- **Nunca rellenar un dato faltante** (ni con 0 ni con promedios): si el `Searcher`
  devuelve `null`, se manda `null`.
- Commits pequeños, en inglés, **sin co-autores de IA**.

## 4. Correr

```bash
cd backend
uv venv && uv pip install -r requirements.txt   # o pip, dentro de un venv
uvicorn app.main:app --reload --port 8000
```
