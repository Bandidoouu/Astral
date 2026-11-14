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

## 1b. Lo que cambió (requisitos centrales, ver `docs/contratos.md`)

- **Clic en cualquier punto de los tres globos** (Tierra, Luna y Marte): se manda
  `body`, `lat`, `lon` y se muestran gemelos en los otros dos cuerpos (o en los que el
  usuario elija con `target_bodies`). Los resultados vienen agrupados por `body`.
- **Escala:** selector "Global (1 km)" / "Detail (60 m)". El detalle de 60 m **solo
  se ofrece dentro de su cobertura**: Luna al sur de 80° S y Tierra en México y
  alrededores (-118 a -86°, 14 a 33°), y solo entre Luna y Tierra. Fuera de ella,
  desactivar la opción o mostrar el aviso que llega en `warnings`.
- **Puntajes por dimensión por separado (siete):** `terrain`, `operations`,
  `thermal`, `albedo`, `ice`, `soil` (roca contra polvo) y `aridity`. Perfil por
  defecto `general`. Mostrar también `not_comparable` (polvo y viento, subsuelo,
  gravedad, vacío/atmósfera, radiación). Si una viene en `null`, mostrar **"No data" / "Sin dato"**, nunca 0, y
  no dibujarla en el radar como cero. El total ya viene calculado (`score`) con las
  dimensiones que tienen dato; `weights_used` dice cuánto pesó cada una.
- `attributes` trae valores crudos para la tarjeta (temperatura máxima y mínima en
  kelvin, albedo, distancia al hielo en km); también pueden venir en `null`.
- **Capa de aptitud lunar** (Hanna): superponer sobre el polo sur los PNG
  `moon_south_{landing,rover,ice,temperature,total}.png`, con leyenda de 0 a 1, los
  pesos visibles y los candidatos de la NASA de `suitability_moon.json`. Texto
  obligatorio junto a la capa: *"Suggestion, not a final site selection: illumination
  and Earth visibility are not included."*

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
- Una dimensión con valor `null` se muestra como "No data" / "Sin dato", no como 0.
- Siempre mostrar los límites (`not_comparable`: gravedad, vacío/atmósfera,
  radiación): el jurado valora que se reconozcan.
- Commits pequeños, en inglés, **sin co-autores de IA**.

## 4. Correr

```bash
cd frontend
npm install
npm run dev
```
