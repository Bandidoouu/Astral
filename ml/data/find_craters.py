#!/usr/bin/env python
"""Detecta cráteres simples en un DEM reproyectado y corta parches centrados en ellos.

Para la validación "cráteres simples lunares ↔ Meteor Crater" hacen falta
consultas lunares centradas en cráteres de ~0.8 a 2.5 km (Meteor Crater: 1.2 km,
170 m de profundidad). Sin catálogo oficial a la mano, se detectan con reglas
geomorfológicas sencillas sobre el DEM suavizado:
  - mínimo local (ventana de 31 px),
  - radio del borde R = anillo más alto entre 6 y 25 px del mínimo,
  - profundidad (borde - fondo) >= 0.08 * diámetro y >= 50 m,
  - borde elevado: anillo del borde > anillo a 2R en >= 5 m,
  - borde casi circular: desviación de la altura a lo largo del borde < 0.35 * profundidad,
  - supresión de no máximos a 3R.

  python -m ml.data.find_craters --src data/raw/moon/regions/tranquillitatis_60m.tif \
      --body moon --to-m 1000 --name tranquillitatis --id-offset 230000
"""
import argparse
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from pyproj import CRS, Transformer
from scipy import ndimage

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[2]))


def ring_means(z, r0, c0, rmax):
    yy, xx = np.mgrid[-rmax:rmax + 1, -rmax:rmax + 1]
    rr = np.sqrt(yy ** 2 + xx ** 2).round().astype(int)
    win = z[r0 - rmax:r0 + rmax + 1, c0 - rmax:c0 + rmax + 1]
    sums = np.bincount(rr.ravel(), win.ravel(), minlength=rmax + 2)
    cnt = np.bincount(rr.ravel(), minlength=rmax + 2)
    return sums[:rmax + 1] / np.maximum(cnt[:rmax + 1], 1), win, rr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--body", default="moon")
    ap.add_argument("--to-m", type=float, default=1000.0)
    ap.add_argument("--name", required=True)
    ap.add_argument("--id-offset", type=int, required=True)
    ap.add_argument("--dmin-km", type=float, default=0.8)
    ap.add_argument("--dmax-km", type=float, default=2.5)
    ap.add_argument("--max", type=int, default=60, help="máximo de cráteres a guardar")
    ap.add_argument("--patch", type=int, default=128)
    a = ap.parse_args()

    with rasterio.open(a.src) as ds:
        z = ds.read(1).astype(np.float64)
        nod = ds.nodata
        T, px = ds.transform, ds.res[0]
        crs = CRS.from_wkt(ds.crs.to_wkt())
    valid = z > -30000 if nod is not None else np.ones_like(z, bool)
    z = np.where(valid, z * a.to_m, np.nan)
    zs = ndimage.gaussian_filter(np.nan_to_num(z, nan=np.nanmean(z)), 1.5)
    mins = (zs == ndimage.minimum_filter(zs, size=31)) & valid
    H, W = z.shape
    rmax, half = 60, a.patch // 2
    rs, cs = np.nonzero(mins)
    keep = (rs > rmax) & (rs < H - rmax) & (cs > rmax) & (cs < W - rmax) \
        & (rs > half) & (rs < H - half) & (cs > half) & (cs < W - half)
    found = []
    for r0, c0 in zip(rs[keep], cs[keep]):
        prof, win, rr = ring_means(zs, r0, c0, rmax)
        R = 6 + int(np.argmax(prof[6:26]))
        D = 2 * R * px
        if not (a.dmin_km * 1000 <= D <= a.dmax_km * 1000) or 2 * R > rmax:
            continue
        depth = prof[R] - zs[r0, c0]
        rim_out = prof[R] - prof[min(2 * R, rmax)]
        rim_sd = win[rr == R].std()
        if depth >= max(50.0, 0.08 * D) and rim_out >= 5.0 and rim_sd < 0.35 * depth:
            found.append(dict(r=int(r0), c=int(c0), R_px=R, diameter_m=D, depth_m=float(depth),
                              d_over_D=float(depth / D), rim_sd_m=float(rim_sd)))
    found.sort(key=lambda f: -f["d_over_D"])
    sel = []
    for f in found:                     # supresión de no máximos
        if all(np.hypot(f["r"] - g["r"], f["c"] - g["c"]) > 3 * max(f["R_px"], g["R_px"]) for g in sel):
            sel.append(f)
        if len(sel) == a.max:
            break
    print(f"{len(found)} candidatos -> {len(sel)} cráteres (D {a.dmin_km}-{a.dmax_km} km)")

    to_geo = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)
    patches, rows = [], []
    for i, f in enumerate(sel):
        tile = z[f["r"] - half:f["r"] + half, f["c"] - half:f["c"] + half]
        if np.isnan(tile).any():
            continue
        x, y = T * (f["c"] + 0.5, f["r"] + 0.5)
        lon, lat = to_geo.transform(x, y)
        mean = float(tile.mean())
        patches.append((tile - mean).astype("<f2"))
        rows.append(dict(body=a.body, scale_m=int(px), lat=float(lat),
                         lon=float((lon + 180) % 360 - 180), crs=crs.to_proj4(), x=x, y=y,
                         region=f"{a.name} simple crater", holdout=False, elev_mean_m=mean,
                         elev_min_m=float(tile.min()), elev_max_m=float(tile.max()), **f))
    n = len(patches)
    meta = pd.DataFrame(rows)
    meta.insert(0, "patch_id", [f"{a.body}-{int(px)}-{a.id_offset + i:06d}" for i in range(n)])
    tag = f"{a.body}_{int(px)}_craters_{a.name}"
    meta["src"], meta["src_idx"] = tag, np.arange(n)
    out = ROOT / "data/patches"
    np.save(out / f"patches_{tag}.npy", np.stack(patches))
    meta.to_parquet(out / f"meta_{tag}.parquet", index=False)
    print(meta[["diameter_m", "depth_m", "d_over_D"]].describe().round(2).to_string())

    k = min(12, n)
    fig, ax = plt.subplots(2, 6, figsize=(13, 4.6))
    for j, x in enumerate(ax.flat):
        x.axis("off")
        if j < k:
            t = patches[j].astype(np.float32)
            gy, gx = np.gradient(t, px)
            x.imshow(np.clip(0.7 - 0.5 * (gx - gy) / (1 + np.hypot(gx, gy)), 0, 1), cmap="gray")
            x.set_title(f"D {meta.diameter_m[j] / 1000:.1f} km, d/D {meta.d_over_D[j]:.2f}", fontsize=8)
    plt.suptitle(f"Detected simple craters · {a.name} · 7.68 km patches", fontsize=10)
    plt.tight_layout()
    plt.savefig(ROOT / f"data/artifacts/craters_{a.name}.png", dpi=80)
    print("->", out / f"patches_{tag}.npy", f"({n})")


if __name__ == "__main__":
    main()
