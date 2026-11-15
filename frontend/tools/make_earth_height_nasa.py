#!/usr/bin/env python
"""Rejilla de relieve de respaldo de la Tierra (formato ATH1) con datos NASA.

Reemplaza a la antigua rejilla ETOPO (NOAA): NASA SRTMGL30 v002 (Earthdata), promediada
a 1440 x 720 (0.25°). SRTMGL30 cubre de 90° N a 60° S: el océano vale 0 m y el sur de
60° S (Antártida) se rellena con 0 m, igual que en `public/textures/earth/height.json`.

  python frontend/tools/make_earth_height_nasa.py data/raw/earth/srtmgl30/srtmgl30.vrt \
      frontend/src/scenes/assets/earth.height.gz
"""
import gzip
import struct
import sys

import numpy as np
import rasterio
from rasterio.enums import Resampling

W, H = 1440, 720
src, out = sys.argv[1], sys.argv[2]
with rasterio.open(src) as ds:
    rows = int(round(H * (ds.bounds.top - ds.bounds.bottom) / 180))
    z = ds.read(1, out_shape=(rows, W), resampling=Resampling.average).astype(np.float32)
    nod = ds.nodata
if nod is not None:
    z[z == nod] = 0
grid = np.zeros((H, W), np.float32)
grid[:rows] = z
grid = np.clip(np.round(grid), -15000, 30000).astype("<i2")
with gzip.open(out, "wb") as f:
    f.write(b"ATH1" + struct.pack("<HH", W, H) + grid.tobytes())
print(out, W, H, int(grid.min()), int(grid.max()))
