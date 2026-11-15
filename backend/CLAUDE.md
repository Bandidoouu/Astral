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

## 1b. Requisitos centrales (ver `docs/contratos.md`)

- **Clic en cualquier punto de cualquier cuerpo:** la petición trae `body`, `lat`,
  `lon` y opcionalmente `target_bodies` (por defecto, los otros dos cuerpos).
- **Escala en cada búsqueda:** `scale_m` = `1000` (global, los tres cuerpos, por
  defecto) o `60` (detalle, solo Luna ↔ Tierra y solo dentro de su cobertura: Luna al
  sur de 80° S, Tierra en la caja -118 a -86° y 14 a 33°). Fuera de cobertura no se
  inventan resultados: ese destino vuelve vacío con un aviso en `warnings`.
- **La búsqueda cubre todas las dimensiones posibles, no solo la forma:** `scores`
  trae `terrain`, `operations`, `thermal`, `albedo`, `ice`, `soil` y `aridity` por
  separado. Perfil por defecto `general` (pesos iguales). **`null` = "sin dato"**; no cuenta en el total y
  los pesos usados vienen en `weights_used`. `materials` ya no existe.
- **Capa de aptitud lunar** (reglas transparentes): rasters del polo sur por
  criterio y total, más un JSON con pesos, reglas y candidatos de la NASA.

### Cómo implementar `POST /api/similar`

No reimplementen la búsqueda ni instancien `Searcher` en cada petición: usen el singleton de `app.services.search_service.get_searcher()`.

```python
from app.core.schemas import SimilarRequest
from app.services.search_service import get_searcher

@router.post("/similar")
def find_similar(req: SimilarRequest):
    searcher = get_searcher()
    if searcher is not None:
        return searcher.search(
            body=req.body, lat=req.lat, lon=req.lon,
            target_bodies=req.target_bodies, k=req.k, profile=req.profile,
            method=req.method or "rrf", scale_m=req.scale_m
        )
    # Si searcher es None, hacer fallback estricto al mock de contracts/similar_response.json
```

### Artefactos que lee el `Searcher` (en `data/artifacts/`, por escala)

`meta_{scale}.parquet`, `emb_{scale}.npy`, `baseline_feat_{scale}.npy` + `.json` y
`features_{scale}.parquet` (temperatura, albedo, hielo). Si falta una escala, el `Searcher`
responde con un aviso en `warnings`, no con un error.

### Capa de aptitud lunar (`data/artifacts/suitability/`)

`moon_south_{landing,rover,ice,temperature,total}.tif` y `.png` (para mostrar directo), más `suitability_moon.json`. Endpoints:
`GET /api/suitability/moon_south/{criterion}` (PNG) y `GET /api/suitability/moon_south` (JSON).

## 2. Estructura

```text
backend/
├── app/
│   ├── main.py              # crea la app FastAPI, CORS, incluye los routers
│   ├── api/                 # routers: similar.py, galaxy.py, patches.py, health.py, suitability.py
│   ├── core/                # config.py (get_artifacts_dir, get_contracts_dir), schemas.py (Pydantic)
│   └── services/            # search_service.py (singleton Searcher), scoring.py, thermal.py
├── tests/                   # pruebas: test_api.py, test_contracts.py, test_scoring.py, ...
├── pytest.ini
└── requirements.txt         # fastapi, uvicorn, faiss-cpu, numpy, pandas, pyarrow
```

## 3. Reglas de arquitectura para IAs y desarrolladores

1. **Gestión del Searcher de ML:**
   - Usar **únicamente** `get_searcher()` de `app.services.search_service`.
   - Inicializa `Searcher(art=get_artifacts_dir())`. Nunca usar `root=...` ni instanciar `Searcher()` directamente.
   - Si los artefactos no existen en disco, `get_searcher()` retorna `None`. Los endpoints deben responder con mocks compatibles de `contracts/`, garantizando que el frontend **nunca se bloquee**.
2. **Esquemas Pydantic (`app/core/schemas.py`):**
   - Usar tipado estricto con `Literal[...]` (`CelestialBody = Literal["earth", "moon", "mars"]`, `ScaleM = Literal[60, 1000]`, `MissionProfile`, etc.).
   - Mantener las validaciones de rango numérico (`ge`, `le`) para que FastAPI responda HTTP 422 automáticamente en peticiones malformadas.
3. **Rutas dinámicas y variables de entorno:**
   - Usar **siempre** `get_artifacts_dir()` y `get_contracts_dir()` de `app.core.config`.
   - **Prohibido** congelar rutas en constantes a nivel de módulo o usar rutas absolutas, ya que rompen tests con fixtures como `artifacts_dir` (`ASTRAL_ARTIFACTS`).
4. **Validación de endpoints con archivos del sistema:**
   - Todo endpoint que sirva archivos según parámetros de ruta (ej. `{criterion}`) debe validar contra una lista blanca fija (`landing`, `rover`, `ice`, `temperature`, `total`) para impedir *path traversal*.
5. **Alineación con contratos (`docs/contratos.md` y `contracts/`):**
   - Las respuestas mock y reales deben coincidir exactamente con la estructura esperada: llaves `query`, `results`, `warnings`, `scores` (`null` = sin dato), `attributes`, `not_comparable`.
   - Nunca rellenar datos faltantes con 0 o promedios: si falta, se envía `null`.
6. **Pruebas obligatorias:**
   - Toda adición o cambio debe acompañarse de pruebas en `backend/tests/` y correr con `pytest` sin errores antes de finalizar.
7. **Identidad y autoría (Regla de oro §4.2):**
   - **Prohibido** agregar `Co-Authored-By: Claude`, `Copilot`, `ChatGPT`, `Gemini` o firmas de IA en commits, PRs o archivos.
   - Commits concisos, en inglés, usando únicamente la identidad configurada en git.

## 4. Correr y probar

```bash
cd backend
uv venv && uv pip install -r requirements.txt   # o pip, dentro de un venv
pytest                                         # correr la suite de pruebas
uvicorn app.main:app --reload --port 8000      # servidor de desarrollo
```
