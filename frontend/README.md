# ASTRAL frontend

React + TypeScript + React Three Fiber. Select an origin on Earth, the Moon or
Mars and compare matches on the other worlds through terrain, operations,
thermal, albedo, ice, soil and aridity dimensions.

**Default mode is an illustrative UI demo.** Scores are fixed examples, not
recomputed when coordinates or profiles change. The search fixture is copied from
`main@ccc87b9`; the additional lunar example is fictional.
Unavailable dimensions remain null. No neural model runs in the browser.

## Run

Node.js 22.18+ (tested with 24.21) and npm:

```sh
cd frontend
npm ci
npm run dev
npm test
npm run build
```

On Windows PowerShell use `npm.cmd` if execution policy blocks npm.ps1.
Open the Vite URL. Keep the lockfile with dependency changes.

## Collaboration

Hanna owns [src/scenes/](src/scenes/); Violeta owns [src/ui/](src/ui/).
[App.tsx](src/App.tsx) injects the scene renderers into the UI using
[shared props](src/shared/visualization.ts).
API, fixtures, shared types and project configuration require coordinated edits.
See the [collaboration guide and ready-to-use prompts](WORKING_TOGETHER.md)
and [module instructions](AGENTS.md).

## API integration

Copy [.env.example](.env.example) to .env.local, set `VITE_DATA_MODE=api`, and
restart Vite. `VITE_API_URL` defaults to `http://localhost:8000`.
The backend must allow the frontend origin through CORS.
API failures remain visible errors; there is no silent fallback to demo data.

This implementation follows the `main@ccc87b9` contract pulled on 2026-11-14:

- Any origin, explicit `target_bodies`, `k` per target, default global scale 1000 m/px.
- Scale 60 m/px only between the lunar south pole (latitude < -80°) and Mexico
  (latitude 14..33°, longitude -118..-86°); no Mars detail index.
- Results grouped by target in returned ranking order; score does not determine rank.
- Dimensions terrain/operations/thermal/albedo/ice/soil/aridity, default profile general, nulls, no_data, optional weights,
  origin patches, raw attributes and warnings are displayed without recomputation.
- The backend chooses the search method. Astrobiology is offered for Mars origins.
- Galaxy endpoint: `GET /api/galaxy?scale=60|1000`.
  The bundled four-point galaxy example is only used at scale 60.

Lunar suitability uses proposed endpoints `GET /api/suitability/moon_south`
(metadata) and `GET /api/suitability/moon_south/{criterion}` (PNG).
`VITE_SUITABILITY_URL` can override that base. The UI shows exported polar figures,
criterion weights, rules, missing inputs and candidate comparisons. These are
not georeferenced globe textures. No lunar raster is bundled in demo mode.

## Included and pending

Included: selectable schematic globes, orbit controls, arcs, profiles, destinations,
scales, result cards, radar, attribute comparison, loading/error/empty states,
responsive UI and a fallback when WebGL is unavailable.

The atlas uses a fixed composition with visual orbit guides and the Moon near
Earth. Rings provide spatial context; dashed connections show analog matches.
There is no Sun, orbital clock or distance-scale mode. Sizes and spacing serve
the interface and are not physical scale or current orbital positions.

Missions offer investigation questions for rover mobility, resources, habitats,
surface traverses and astrobiology. Planetary origins target Earth analogs when
choosing a mission; Earth origins compare with Moon and Mars. Match evidence
explains individual dimensions and missing observations, and exports an
investigation brief as Markdown. Mission exercises are proposals, not validated
site recommendations. Demo rankings are real precomputed model outputs for curated sites; live ranking belongs to the API.

Search markers and cards focus the camera on a match;
camera flights respect reduced-motion preferences. Stars are decorative.

Before frontend work, pull origin/main while preserving local changes, as requested
by the user. 

Included since then: official NASA globe textures and layers (visible, relief, shadows,
topography, Moon and Mars suitability overlays), the real terrain galaxy, base
suitability for the Moon **and Mars** (weights, rules and candidates; the bundled ML
export is shown if the data service is not connected), Grad-CAM figures for the curated
1 km pairs, the compared-patch footprint (`window_km`) on the globe, and real precomputed
model results in demo mode.

Pending: Spanish translation, guided tour and a `gravity_scaled` control (the backend
does not forward `scale_mode` yet). Mars suitability PNGs per criterion need the backend
endpoint `GET /api/suitability/mars/{criterion}`.
Passing UI/contract checks does not validate scientific similarity or model quality.

Sources linked in the interface: [Earthdata](https://search.earthdata.nasa.gov/),
[LRO](https://pds-geosciences.wustl.edu/missions/lro/),
[MOLA](https://pds-geosciences.wustl.edu/missions/mgs/mola.html), and the
[challenge resources](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/?tab=resources).

Libraries and versions: [package.json](package.json).
