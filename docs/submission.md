# Space Apps 2026 submission texts (copy-paste)

> Internal note (Spanish): textos para la página de envío. Todos los números salen de
> artefactos guardados (`data/artifacts/eval_60_v2sel.json`, `val_1000_v2_1000.json`,
> `suitability/*.json`, `frontend/src/mocks/precomputed-results.json`). Si un número
> cambia, se corrige aquí y en el README en el mismo commit.

## Links

- **Live site (no server needed):** https://bandidoouu.github.io/Astral/
- **Code:** https://github.com/Bandidoouu/Astral
- **Search artifacts (indexes, embeddings, encoders, suitability layers):** https://github.com/Bandidoouu/Astral/releases/tag/v2-1km-r4

## Project name

**ASTRAL — a planetary Shazam for Moon and Mars analogs**

## High-level summary (short)

ASTRAL lets anyone click any point on Earth, the Moon or Mars and find its terrain twins
on the other two worlds. Our own neural network, trained on NASA elevation data (LOLA,
MOLA, SRTM), compares landforms across planets, and seven separate dimensions —
terrain, operations, temperature, albedo, ice, soil and aridity — explain what is alike
and what is not. Hidden from training, El Pinacate (where NASA trained the Apollo crews)
ranks 147 of 55,444 Earth patches for lunar volcanic terrain, against 320 for a terrain
formula; Olympus Mons finds Mauna Loa in first place out of 7,669.

## Project details (long)

**What it does.** ASTRAL is a 3D "astral map" of Earth, the Moon and Mars. Pick a site
on any of the three bodies and it returns ranked analog sites on the other two, at two
scales: a global 1 km/px scale (128 km windows) covering all three bodies everywhere,
and a 60 m/px detail scale between the lunar south pole (south of 80° S) and Mexico.
An optional gravity-scaled mode compares Earth windows with Moon windows 6× larger and
Mars windows 2.6× larger, because landforms built under lower gravity are larger.

**How it works.** Elevation is cut into 128×128 patches, each resampled in its own
equal-area projection (no polar distortion), with five channels: relative elevation,
slope, roughness, curvature and hillshade. A ResNet-18 encoder trained by us with
self-supervised contrastive learning (SimCLR) maps each patch to a 128-dimension
embedding. A planet discriminator behind gradient reversal pushes the embedding toward
terrain type rather than planet identity, while relief-matched batches and an
auxiliary relief head keep real topography. Terrain ranking fuses the network with a
20-statistic terrain formula by reciprocal rank fusion. The other six dimensions are
computed separately from NASA data and scored 0–1; missing data is shown as "no data"
and never counts toward the total. Mission profiles (rover, ISRU, habitat, EVA,
astrobiology) weight the dimensions, and terrain never weighs more than 30 %.

**Promising Earth zones.** Earth results only come from bare ground, deserts, sparse
shrubland, grassland and permanent ice (MODIS land cover). This keeps 49.6 % of Earth
patches at 60 m and 49.9 % at 1 km.

**Base-suitability layers.** For the lunar south pole (LOLA slope, Diviner ice and
temperature) and for Mars (MOLA slope and elevation, Mars Odyssey hydrogen) we build
transparent rule-based layers, with weights visible, and compare NASA candidate sites
against them. They are suggestions, not site selections: illumination and Earth
visibility (communications) are not in the challenge data portals.

**Results (validation sets fixed before choosing a model; blind test run once per model).**
- Blind test, 60 m: for Montes Marius (lunar volcanic domes), El Pinacate — never seen
  in training — reaches median rank **147 of 55,444** Earth patches with our network,
  versus 320 for the terrain formula and 345 for random; it is in the top 50 for
  **49 of 195** queries (formula 12, random 0).
- Blind test, 1 km: median percentile **0.48 %** (formula 15.4 %, random 8.8 %).
- Olympus Mons → Mauna Loa: **rank 1 of 7,669** with the network alone (7 of 7 queries
  in the top 50); the formula puts it at rank 1,720.
- Kasei and Ares Valles → Channeled Scablands: 1.9 % (formula 20.3 %). Montes Marius →
  San Francisco volcanic field: 0.14 % (formula 2.6 %).
- The lunar south-pole candidate Faustini rim returns a patch 12 km from the center of
  El Pinacate as its third Earth match at 60 m.
- Mars suitability: the plains where InSight, Opportunity and Spirit landed score in
  the 92.7th, 95.3rd and 99.8th percentiles of Mars; Arcadia Planitia (shallow ice) the
  95.1st. Moon: Faustini (93.3) and Haworth (91.3) rims score highest among the Artemis
  III candidates.

**Honest limitations.** Lunar maria → terrestrial flood basalts fails at 1 km (25.8 %,
worse than random at 4.4 %): eroded basalts do not look like flat maria. Planet
invariance is partial: a linear classifier still separates the planets 97 % of the time
on relief-matched samples at 60 m, and our best model is not the most invariant one.
Suitability layers lack illumination and communications; on Mars they lack thermal
inertia, albedo, minerals, dust and radiation. SRTMGL30 has no Antarctica. Earth can
never reproduce gravity, vacuum or the Martian atmosphere, radiation or regolith dust,
and every result says so.

**Why it matters.** NASA chose El Pinacate by expert eye in the 1960s. ASTRAL makes
the search for analog sites systematic, global and explainable, and proposes new
candidates — for example, several Sonoran and Chihuahuan desert sites as twins of the
Haworth and Faustini rims, Artemis III candidate regions.

**Tools.** Python (PyTorch, FAISS, GDAL, rasterio), FastAPI backend, React Three Fiber
frontend. Search artifacts are published as GitHub releases.

**How the live site works (precomputed).**
The site at **https://bandidoouu.github.io/Astral/** runs with no server. Our real network
(model v2, release `v2-1km-r4`) was run beforehand, through the same search API, on
**every 1 km patch of Earth, the Moon and Mars** (18,808 patches): the top 10 matches toward
each of the other two bodies, with all seven dimension scores. The site looks up those
answers for the patch nearest to your click and recomputes the mission-profile score in the
browser with the same formula as the API (the ranking itself, terrain similarity, does not
depend on the profile). **Checked: 300 of 300 random clicks, with random profiles, match the
live API** (same order, same scores, same percentages).

**Offline limits.** Detail (60 m) is available only for the eight curated lunar south-pole sites
(Shackleton, Mons Mouton, Malapert Massif and the Haworth, Nobile, de Gerlache, Faustini and
Amundsen rims) and El Pinacate; Grad-CAM figures only for the
curated sites (the gravity-scaled mode is also precomputed for all 18,648 patches); the Earth land-cover notice uses the nearest
patch center instead of the exact clicked point. For anything else, run the backend:

```bash
gh release download v2-1km-r4 -R Bandidoouu/Astral -p 'astral-v2-1km-r4.tar.gz*'
sha256sum -c astral-v2-1km-r4.tar.gz.sha256 && tar -xzf astral-v2-1km-r4.tar.gz
pip install -r backend/requirements.txt          # plus PyTorch only to re-embed (not needed to search)
cd backend && ASTRAL_ARTIFACTS=$PWD/../v2-1km-r4 uvicorn app.main:app --port 8000
cd ../frontend && npm ci && VITE_DATA_MODE=api VITE_API_URL=http://127.0.0.1:8000 npm run dev
```


## NASA data used and how

| Data | How we use it |
| --- | --- |
| LRO LOLA south-polar DEM `LDEM_75S_60M` and global DEM `ldem_64` (PDS Geosciences) | Moon terrain patches at 60 m and 1 km; slope for the lunar suitability layer; height and normal maps of the 3D globe |
| LRO LOLA normal albedo `ldam` | `albedo` dimension on the Moon |
| LRO Diviner GCP, PRP south and rock abundance (PDS Geosciences) | `thermal`, `ice` and `soil` dimensions on the Moon; ice and temperature criteria of the lunar suitability layer |
| LRO LROC WAC color mosaic (NASA SVS CGI Moon Kit) | Visible texture of the Moon globe |
| MGS MOLA MEGDR 128 px/deg (PDS Geosciences) | Mars terrain patches; slope and elevation criteria of the Mars suitability layer; Mars globe relief |
| Mars Odyssey GRS water-equivalent hydrogen (PDS Geosciences) | `ice` dimension on Mars and hydrogen criterion of the Mars suitability layer |
| Viking MDIM 2.1 color mosaic (NASA Mars Trek) | Visible texture of the Mars globe |
| SRTMGL30 v002 and NASADEM_HGT v001 (Earthdata, LP DAAC) | Earth terrain patches at 1 km (global) and 60 m (Mexico and analog sites); Earth globe relief |
| MODIS MOD11C3, MCD43C3, MOD10CM, MCD12C1 (Earthdata) | Earth `thermal`, `albedo`, `ice` and `soil` (apparent thermal inertia) dimensions; promising-zone land-cover mask |
| GPM IMERG monthly V07 (Earthdata, GES DISC) | Earth `aridity` dimension |
| Blue Marble: Next Generation (NASA GIBS) | Visible texture of the Earth globe |

## Space agency partner data

- **JAXA:** SLDEM2015 merges LRO LOLA with the SELENE (Kaguya) Terrain Camera DEM from
  JAXA. We use its tiles over Montes Marius, Mare Tranquillitatis and Mare Imbrium for
  the 60 m lunar test queries (blind test of El Pinacate and crater validation).

## Other resources

- **Natural Earth** admin-1 boundaries (public domain): readable state/country names.
- **IAU / USGS Gazetteer of Planetary Nomenclature**: readable feature names on the
  Moon and Mars (e.g. "Olympus Mons, Mars").
- ImageNet-pretrained ResNet-18 weights from torchvision (starting point of our encoder).
- Software: PyTorch, torchvision, FAISS, NumPy, SciPy, pandas, PyArrow, scikit-learn,
  umap-learn, pytorch-grad-cam, GDAL, rasterio, pyproj, GeoPandas, Shapely, h5py,
  earthaccess, Matplotlib, Pillow, FastAPI, Uvicorn, React, Three.js, React Three Fiber,
  drei, Vite, TypeScript.

## Use of artificial intelligence

We used AI coding assistants (Anthropic Claude Code and OpenAI Codex) to help write and
review code and documentation. The neural network that finds the analogs is our own: we
designed, trained and validated it on NASA data, and it does not call any LLM or
external AI API at run time. No imagery in the app was generated by AI: globe textures
come from NASA missions or are rendered by us from NASA elevation data. (If the team's
video uses any AI-generated image, it must carry a watermark and be declared here.)

## References

- Chen, T. et al. (2020). A Simple Framework for Contrastive Learning of Visual
  Representations. ICML.
- Ganin, Y. et al. (2016). Domain-Adversarial Training of Neural Networks. JMLR.
- He, K. et al. (2016). Deep Residual Learning for Image Recognition. CVPR.
- Cormack, G., Clarke, C. & Büttcher, S. (2009). Reciprocal Rank Fusion outperforms
  Condorcet and individual rank learning methods. SIGIR.
- Selvaraju, R. et al. (2017). Grad-CAM: Visual Explanations from Deep Networks. ICCV.
- Boynton, W. V. et al. (2007). Concentration of H, Si, Cl, K, Fe, and Th in the low- and
  mid-latitude regions of Mars. JGR Planets.
- Barker, M. K. et al. (2016). A new lunar digital elevation model from the Lunar Orbiter
  Laser Altimeter and SELENE Terrain Camera (SLDEM2015). Icarus.
- Dataset provenance and download commands: `docs/datos.md` in our repository.
