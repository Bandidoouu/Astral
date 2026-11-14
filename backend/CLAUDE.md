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
- Commits pequeños, en inglés, **sin co-autores de IA**.

## 4. Correr

```bash
cd backend
uv venv && uv pip install -r requirements.txt   # o pip, dentro de un venv
uvicorn app.main:app --reload --port 8000
```
