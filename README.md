# ASTRAL — a planetary Shazam for Moon and Mars analogs

**NASA Space Apps Challenge 2026 · Team Dinamita Buena Onda**
Challenge: *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*

> Click any point on Earth, the Moon or Mars. ASTRAL's own neural network — trained by
> us on NASA elevation data, **not** an LLM API — finds its twins on the other two
> worlds, scores how alike they are in seven separate dimensions, and says honestly
> what Earth can never reproduce: gravity, vacuum or atmosphere, radiation.

## Why it matters

Astronauts train on Earth for places they have never been. NASA trained the Apollo
crews at **El Pinacate, Sonora (1965–1970)** because its volcanic terrain looked like
the Moon — a choice made by expert eyes. ASTRAL makes that search systematic and
global, and proposes **new** analog sites for the Artemis south-pole bases and for Mars.

**Our test:** El Pinacate is hidden from training. When asked about lunar volcanic
terrain (Montes Marius), does the network find it on its own?

## What it does

- **Search from any body to the other two.** Pick a point anywhere on Earth, the Moon or
  Mars; results come back for the other two bodies (or the ones you choose).
- **Two scales.** *Global, 1 km/px* (128 km patches) for all three bodies, everywhere.
  *Detail, 60 m/px* (7.7 km patches) between the lunar south pole (south of 80° S) and
  Mexico, where we have high-resolution elevation for both.
- **Gravity scaling (optional).** Landforms built under lower gravity are larger, so
  `gravity_scaled` compares Earth windows with Moon windows 6× larger and Mars windows
  2.6× larger (the gravity ratios), using the same model.
- **Promising Earth zones.** Earth results only come from bare ground, deserts, sparse
  shrubland, grassland and permanent ice (MODIS land cover); forests, cropland, cities,
  wetlands and water are excluded. Clicking outside these zones still works, with a warning.
- **Base-suitability layers** for the lunar south pole and Mars, built with transparent
  rules (not the network), with NASA candidate sites overlaid.

## How it works

1. **Terrain patches.** Elevation is resampled into 128×128 patches in a local
   equal-area projection centered on each patch (no polar distortion). Five channels:
   relative elevation, slope, roughness, curvature and hillshade.
2. **Our network.** A ResNet-18 encoder trained with self-supervised contrastive
   learning (SimCLR) maps each patch to a 128-d embedding. A planet discriminator behind
   gradient reversal pushes the embedding toward *terrain type* rather than *which
   planet*, while batches matched by relief and slope and an auxiliary relief head keep
   it from erasing real topography.
3. **Search.** Terrain ranking fuses the network and a 20-statistic terrain formula by
   reciprocal rank fusion (RRF, k = 60, fixed). FAISS indexes every patch.
4. **Seven dimensions, scored separately (0–1).** Missing data is reported as **no data**
   and never counts toward the total; values are never invented. Mission profiles
   (general, rover, ISRU, habitat, EVA, astrobiology) weight them; terrain never weighs
   more than 0.3.

| Dimension | Earth | Moon | Mars |
| --- | --- | --- | --- |
| `terrain` | Our network + formula (RRF) on SRTMGL30 / NASADEM | LOLA | MOLA |
| `operations` | Slope and roughness statistics of the patch | same | same |
| `thermal` | MODIS MOD11C3 land-surface temperature | LRO Diviner (global and south-polar products) | no data |
| `albedo` | MODIS MCD43C3 | LOLA normal albedo | no data |
| `ice` | MODIS MOD10CM snow/ice cover | Diviner surface-stable ice | Mars Odyssey GRS hydrogen |
| `soil` | MODIS apparent thermal inertia (percentile on Earth) | Diviner rock abundance (percentile on the Moon) | no data |
| `aridity` | NASA GPM IMERG precipitation | 1.0 (no liquid water) | 1.0 |

Each result also lists what is **not comparable**: dust and wind, subsurface, gravity,
vacuum or atmosphere, radiation.

## Results

All numbers come from validation sets fixed **before** choosing a model; the
El Pinacate blind test was run once per model.

**Blind test — Montes Marius (Moon) → El Pinacate (hidden from training)**

| Scale | Network | 20-statistic formula | Random |
| --- | --- | --- | --- |
| 60 m (55,444 Earth patches) | median rank **147**; top 50 in **49 / 195** queries | median rank 320; top 50 in 12 / 195 | median rank 345; top 50 in 0 / 195 |
| 1 km (7,669 Earth patches) | median percentile **0.48 %** | 15.4 % | 8.8 % |

At 60 m El Pinacate covers 115 patches, so even a random ordering reaches one of them
early (rank 345): the formula barely beats random, while the network halves the rank and
puts El Pinacate in the top 50 for a quarter of the queries.

**Known analogs at 1 km (network only, median percentile among 7,669 Earth patches)**

| Query → known Earth analog | Network | Formula | Random |
| --- | --- | --- | --- |
| Olympus Mons → Mauna Loa | **rank 1** (7 / 7 queries in top 50) | rank 1,720 | 12.0 % |
| Kasei and Ares Valles → Channeled Scablands | **1.9 %** | 20.3 % | 9.3 % |
| Olympia Undae dunes → Sahara / Namib sand seas | 1.1 % | 0.35 % | 3.0 % |
| Montes Marius → San Francisco volcanic field | **0.14 %** | 2.6 % | 8.1 % |
| Lunar maria → Columbia River / Deccan basalts | 25.8 % (worse than random) | 10.8 % | 4.4 % |

**Suitability layers.** On Mars (MOLA slope and elevation, Mars Odyssey hydrogen), the
plains where InSight, Opportunity and Spirit landed score above the 90th percentile of
the planet (92.7, 95.3 and 99.8), and Arcadia Planitia, a shallow-ice candidate, scores
95.1. Jezero and Gale sit near the 45th percentile: they were chosen for their science,
not for ease of landing. On the Moon, Faustini, Haworth, Mons Mouton and Amundsen rims
score highest among the Artemis III candidates; Shackleton and Malapert score low,
likely because illumination — which we do not model — is their main advantage.

## Honest limitations

- **Lunar maria vs flood basalts fails** at 1 km: eroded terrestrial basalts do not look
  like flat maria to the network (worse than random). We report it rather than hide it.
- **Planet invariance is partial.** A linear classifier can still tell the planets apart
  in our 60 m embedding (97 % on relief-matched samples). Our best model is not the most
  invariant one, so invariance is not what explains its success.
- **Suitability layers are suggestions, not site selections:** illumination and Earth
  visibility (communications) are not in the challenge data portals, so they are missing.
  On Mars, thermal inertia, albedo, minerals, dust and radiation are not included.
- Coverage: SRTMGL30 has no Antarctica; the 60 m scale covers only the lunar south pole
  and Mexico; the Earth mask uses current land cover (e.g. the Deccan Traps are cropland
  today and are excluded).
- Earth can never reproduce gravity, vacuum or the Martian atmosphere, radiation, or
  lunar/Martian dust: every result says so.

## Repository

| Folder | What | Team |
| --- | --- | --- |
| [`ml/`](ml/) | Patches, network, training, embeddings, validation, suitability layers | Esteban |
| [`backend/`](backend/) | FastAPI: similarity search, scores and suitability endpoints | Angel, Tamara, Ethan |
| [`frontend/`](frontend/) | 3D globes, analog arcs, result cards, mission profiles | Hanna, Violeta |
| [`docs/`](docs/) | Architecture, data provenance and inter-module contracts (Spanish) | All |
| [`contracts/`](contracts/) | Example JSON for every API / artifact contract | All |

Search artifacts (indexes, embeddings, encoders, suitability layers) are published as a
[GitHub release](https://github.com/Bandidoouu/Astral/releases/tag/v2-1km-r3).

## References

### Datasets (NASA unless noted)

- **LRO LOLA** — south-polar DEM `LDEM_75S_60M`, global DEM `ldem_64`, normal albedo
  `ldam`; NASA PDS Geosciences Node.
- **SLDEM2015** — LOLA + **JAXA** SELENE/Kaguya Terrain Camera merged lunar DEM; NASA PDS.
- **LRO Diviner** — global cumulative products (GCP), polar resource products (PRP),
  rock abundance; NASA PDS Geosciences Node.
- **LRO LROC WAC** color mosaic — NASA Scientific Visualization Studio *CGI Moon Kit*.
- **MGS MOLA MEGDR** (128 px/deg) — NASA PDS Geosciences Node.
- **Mars Odyssey GRS** — water-equivalent hydrogen map (Boynton et al., 2007); NASA PDS.
- **Viking MDIM 2.1 color mosaic** — NASA Mars Trek.
- **SRTMGL30 v002** and **NASADEM_HGT v001** — NASA Earthdata (LP DAAC).
- **MODIS** MOD11C3 (land-surface temperature), MCD43C3 (albedo), MOD10CM (snow cover),
  MCD12C1 (land cover) — NASA Earthdata.
- **GPM IMERG** monthly V07 precipitation — NASA Earthdata (GES DISC).
- **Blue Marble: Next Generation** — NASA Earth Observatory, via NASA GIBS.
- **Natural Earth** admin-1 boundaries (public domain) — only for readable region names.

Provenance, exact products and download commands: [`docs/datos.md`](docs/datos.md).

### Software

PyTorch and torchvision (ResNet-18 ImageNet weights), FAISS, NumPy, SciPy, pandas,
PyArrow, scikit-learn, umap-learn, pytorch-grad-cam, GDAL, rasterio, pyproj, GeoPandas,
Shapely, h5py, earthaccess, Matplotlib, Pillow · FastAPI, Uvicorn, httpx, pytest ·
React, Three.js, React Three Fiber, drei, lucide-react, Vite, TypeScript.

### Methods

- Chen et al. (2020), *A Simple Framework for Contrastive Learning of Visual
  Representations* (SimCLR).
- Ganin et al. (2016), *Domain-Adversarial Training of Neural Networks* (gradient reversal).
- He et al. (2016), *Deep Residual Learning for Image Recognition* (ResNet).
- Cormack et al. (2009), *Reciprocal Rank Fusion*.
- Selvaraju et al. (2017), *Grad-CAM*.

### Use of AI

Generative AI coding assistants were used during development, as declared on our
submission page. The neural network that finds the analogs is our own, trained by us.
