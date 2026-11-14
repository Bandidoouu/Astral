# ASTRAL · Módulo `frontend/` (React Three Fiber)

Las reglas generales del equipo están en el `CLAUDE.md` de la raíz (qué es ASTRAL,
aviso de cambios, nada de co-autores de IA) y **también aplican aquí**.

## 1. Quién y qué

- **Hanna (3D):** globos de la Tierra, la Luna y Marte, capas, arcos entre un sitio y
  sus gemelos, la "galaxia" (UMAP 3D de `galaxy.json`) y la vista de detalle del
  relieve (alturas de parches).
- **Gris (UI):** tarjetas de resultados, radar de puntajes por dimensión, selector de
  perfil de misión, idioma (inglés por defecto, español opcional), la explicación de
  "en qué se parece y en qué no" (`not_comparable`).
- **Es lo que ve el jurado:** todo texto visible va **en inglés** (con traducción
  opcional al español). Nada generado con IA puede usar marca de la NASA.

## 2. Estructura

```text
frontend/
├── public/              # texturas de los globos, íconos
└── src/
    ├── scenes/          # Hanna: Globe, Arcs, Galaxy, TerrainDetail (R3F)
    ├── components/      # Gris: ResultCard, RadarChart, ProfileSelector, LanguageToggle
    ├── api/             # cliente de la API, tipos sacados de docs/contratos.md
    ├── i18n/            # en.json (por defecto), es.json
    └── mocks/           # usa los ejemplos de ../contracts/ mientras la API no esté lista
```

Stack sugerido: Vite + React + TypeScript + `@react-three/fiber` + `@react-three/drei`.
La URL de la API va en `VITE_API_URL` (por defecto `http://localhost:8000`).

## 3. Reglas del módulo

- **Los formatos salen de `docs/contratos.md`.** Los tipos de `src/api/` se escriben a
  partir de ahí; si algo no cuadra, se avisa a ML/Backend, no se "adivina" el campo.
- **Mocks primero:** hasta H12 se trabaja con `contracts/*.json`. Cambiar del mock a la
  API real debe ser una sola variable.
- Una dimensión con valor `null` se muestra como "not available", no como 0.
- Siempre mostrar los límites (`not_comparable`: gravedad, vacío/atmósfera,
  radiación): el jurado valora que se reconozcan.
- Commits pequeños, en inglés, **sin co-autores de IA**.

## 4. Correr

```bash
cd frontend
npm install
npm run dev
```
