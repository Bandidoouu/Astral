# Globe textures (Earth, Moon, Mars)

One folder per body. All maps are equirectangular (2:1), longitude -180 to 180 left to
right, north up, so they wrap a `SphereGeometry` directly. Each folder has a `README.md`
with source, license and resolution, plus `height.json` (min/max height in meters).

Layers (like moon3dmap.com): **Visible** = `color_*k.jpg`; **Relief** = `height_4k.png`
as `displacementMap` + `normal_4k.jpg` as `normalMap`; **Shadows** = `hillshade_4k.jpg`;
**Topography** = `topography_4k.jpg` + `topography_legend.png`; **Suitability** (Moon,
Mars) = `suitability_4k.png` (RGBA, transparent where there is no data) +
`suitability_legend.png`.

Regenerate: `python -m ml.textures` (needs the raw mosaics in `data/raw/textures/`, see
`docs/datos.md` §4).
