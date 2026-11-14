#!/usr/bin/env python
"""Rejillas lunares para las dimensiones térmica y de hielo (Diviner, LRO).

1) Global (Diviner GCP, celdas de 0.5°, temperatura bolométrica en 96 horas locales):
     tmax, tmin, trange por celda. Solo si >= 60% de las horas locales tienen dato;
     si no, NaN ("sin dato"). -> data/features/moon_thermal_global_05deg.tif
2) Polo sur (Diviner PRP sur, triángulos de ~0.5 km): temperatura media y máxima
   anual, y profundidad de hielo estable (ice_depth; -999 = no estable), en la rejilla
   estereográfica polar de LOLA a 480 m (8 x 60 m). Hielo estable "accesible" =
   0 <= ice_depth <= 1 m. Distancia (km) a la celda con hielo estable más cercana.
     -> data/features/moon_polar_south_480m.tif
   La PRP no trae temperatura mínima: en el polo la mínima sale de la GCP.

  python -m ml.features.moon_thermal
"""
import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pyproj import CRS, Transformer
from rasterio.transform import from_origin
from scipy import ndimage

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[2]))
OUT = ROOT / "data/features"
POLAR_REF = ROOT / "data/raw/moon/ldem_75s_60m_float.lbl"
POLAR_PX = 480.0
ICE_MAX_DEPTH_M = 1.0
MIN_LT_COVERAGE = 0.6


def write(path, bands, transform, crs, w, h):
    prof = dict(driver="GTiff", height=h, width=w, count=len(bands), dtype="float32", crs=crs,
                transform=transform, nodata=np.nan, compress="deflate", tiled=True)
    with rasterio.open(path, "w", **prof) as ds:
        for i, (name, a) in enumerate(bands, 1):
            ds.write(a.astype(np.float32), i)
            ds.set_band_description(i, name)
            v = a[np.isfinite(a)]
            print(f"  {name:<16} min {v.min():8.2f}  mediana {np.median(v):8.2f}  máx {v.max():8.2f}"
                  f"  con dato {100 * v.size / a.size:5.1f}%")
    print("->", path)


def global_gcp():
    tmax = np.full((360, 720), np.nan, np.float32)
    tmin, n = tmax.copy(), np.zeros((360, 720), np.int16)
    for f in sorted(glob.glob(str(ROOT / "data/raw/moon/diviner_gcp/global_cumul_avg_cyl_*.tab"))):
        d = pd.read_csv(f, skipinitialspace=True, usecols=["clon", "clat", "ltim", "tbol"])
        d = d[d.tbol > 0]                          # -9998 / -9999 = inválido
        g = d.groupby(["clat", "clon"]).tbol.agg(["max", "min", "count"]).reset_index()
        r = ((90 - g.clat) / 0.5 - 0.5).round().astype(int).to_numpy()
        c = ((g.clon + 180) / 0.5 - 0.5).round().astype(int).to_numpy()
        tmax[r, c], tmin[r, c], n[r, c] = g["max"], g["min"], g["count"]
        print(f"  {Path(f).name}: {len(g)} celdas")
    poor = n < MIN_LT_COVERAGE * 96
    print(f"  celdas con < {int(MIN_LT_COVERAGE * 100)}% de horas locales -> sin dato: {int(poor.sum())}")
    tmax[poor] = np.nan
    tmin[poor] = np.nan
    write(OUT / "moon_thermal_global_05deg.tif",
          [("tmax_k", tmax), ("tmin_k", tmin), ("trange_k", tmax - tmin), ("n_localtimes", n.astype(np.float32))],
          from_origin(-180, 90, 0.5, 0.5), "+proj=longlat +R=1737400 +no_defs", 720, 360)


def polar_prp():
    with rasterio.open(POLAR_REF) as ref:
        crs = CRS.from_wkt(ref.crs.to_wkt())
        x0, y0 = ref.transform.c, ref.transform.f
        size = int(round(ref.width * ref.res[0] / POLAR_PX))
    d = pd.read_csv(ROOT / "data/raw/moon/diviner/dlre_prp_south.tab", skipinitialspace=True,
                    usecols=["tri_clon", "tri_clat", "temp_avg", "temp_max", "ice_depth"])
    print(f"  PRP: {len(d)} triángulos")
    x, y = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True).transform(
        d.tri_clon.to_numpy(), d.tri_clat.to_numpy())
    c = ((x - x0) / POLAR_PX).astype(int)
    r = ((y0 - y) / POLAR_PX).astype(int)
    ok = (r >= 0) & (r < size) & (c >= 0) & (c < size)
    idx = r[ok] * size + c[ok]
    cnt = np.bincount(idx, minlength=size * size)

    def mean_of(v, valid):
        s = np.bincount(idx[valid], v[valid], minlength=size * size)
        k = np.bincount(idx[valid], minlength=size * size)
        out = np.where(k > 0, s / np.maximum(k, 1), np.nan)
        return out.reshape(size, size)

    tavg = d.temp_avg.to_numpy()[ok]
    tmx = d.temp_max.to_numpy()[ok]
    ice = d.ice_depth.to_numpy()[ok]
    tavg_g = mean_of(tavg, tavg > 0)
    tmax_g = mean_of(tmx, tmx > 0)
    stable = (ice >= 0) & (ice <= ICE_MAX_DEPTH_M)
    ice_frac = (np.bincount(idx, stable.astype(float), minlength=size * size)
                / np.maximum(cnt, 1)).reshape(size, size)
    covered = (cnt > 0).reshape(size, size)
    ice_frac[~covered] = np.nan
    ice_cell = np.nan_to_num(ice_frac) > 0
    dist_km = ndimage.distance_transform_edt(~ice_cell) * POLAR_PX / 1000
    dist_km = dist_km.astype(np.float32)
    dist_km[~covered] = np.nan
    print(f"  celdas con hielo estable a <= {ICE_MAX_DEPTH_M} m: {int(ice_cell.sum())} "
          f"({ice_cell.sum() * (POLAR_PX / 1000) ** 2:.0f} km²)")
    write(OUT / "moon_polar_south_480m.tif",
          [("tavg_k", tavg_g), ("tmax_k", tmax_g), ("ice_stable_frac", ice_frac),
           ("ice_distance_km", dist_km)],
          from_origin(x0, y0, POLAR_PX, POLAR_PX), crs.to_wkt(), size, size)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("[Diviner GCP global]")
    global_gcp()
    print("[Diviner PRP polo sur]")
    polar_prp()


if __name__ == "__main__":
    main()
