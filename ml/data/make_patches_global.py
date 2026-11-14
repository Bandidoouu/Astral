#!/usr/bin/env python
"""Parches globales de 128 x 128 a 1 km/px (128 km) para los tres cuerpos.

Cada parche vive en su PROPIA proyección azimutal equivalente de Lambert
(esférica, radio del cuerpo) centrada en él, con el norte hacia arriba: sin
distorsión apreciable en 128 km y sin problemas en los polos. Los centros se
reparten de forma casi uniforme sobre la esfera con una espiral de Fibonacci
(--spacing-km: 128 = casi sin traslape, para el índice; 64 = con traslape, para
entrenar). El DEM global equirectangular se promedia primero a ~1 km (anti-alias)
y luego se muestrea con interpolación bilineal.

Fuentes (docs/datos.md):
  earth: SRTMGL30 (30", de 90° N a 60° S; sin Antártida), metros, océano = NoData
  moon:  LOLA ldem_64_float (64 px/°, km) promediado 2x2 -> ~950 m
  mars:  MOLA MEGDR 128 px/° (metros) promediado 2x2 -> ~930 m

  python -m ml.data.make_patches_global --body moon --spacing-km 128 --limit 200 --out-dir /tmp/x
"""
import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from pyproj import CRS, Transformer
from scipy import ndimage

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[2]))
SCALE = 1000
RADIUS_M = {"earth": 6371000.0, "moon": 1737400.0, "mars": 3396190.0}
SOURCES = {
    # en SRTMGL30 el océano vale 0 (no NoData): water_zero lo marca como agua
    "earth": dict(path="data/raw/earth/srtmgl30/srtmgl30.vrt", to_m=1.0, block=1, region="Earth",
                  water_zero=True),
    "moon": dict(path="data/raw/moon/lola_global/ldem_64_float.lbl", to_m=1000.0, block=2, region="Moon"),
    "mars": dict(path="data/raw/mars/mars_megdr.vrt", to_m=1.0, block=2, region="Mars"),
}
PINACATE = (31.77, -113.50)
HOLDOUT_KM = 50.0


def fibonacci_centers(spacing_km, radius_m, lat_min=-90.0, lat_max=90.0):
    area = 4 * np.pi * (radius_m / 1000) ** 2
    n = int(area / spacing_km ** 2)
    i = np.arange(n) + 0.5
    lat = np.degrees(np.arcsin(1 - 2 * i / n))
    lon = (np.degrees(np.pi * (1 + 5 ** 0.5) * i) + 180) % 360 - 180
    keep = (lat >= lat_min) & (lat <= lat_max)
    return lat[keep], lon[keep]


def laea_inverse(x, y, lat0, lon0, R):
    """Lambert azimutal equivalente esférica inversa (Snyder 1987). Grados."""
    p1, l0 = np.radians(lat0), np.radians(lon0)
    rho = np.hypot(x, y)
    c = 2 * np.arcsin(np.clip(rho / (2 * R), -1, 1))
    with np.errstate(invalid="ignore", divide="ignore"):
        lat = np.arcsin(np.cos(c) * np.sin(p1) + np.where(rho > 0, y * np.sin(c) * np.cos(p1) / rho, 0))
        lon = l0 + np.arctan2(x * np.sin(c), rho * np.cos(p1) * np.cos(c) - y * np.sin(p1) * np.sin(c))
    lat = np.where(rho > 0, lat, p1)
    lon = np.where(rho > 0, lon, l0)
    return np.degrees(lat), (np.degrees(lon) + 180) % 360 - 180


def load_global(src, block, water_zero=False):
    """DEM equirectangular global, promediado en bloques (NaN = NoData)."""
    with rasterio.open(ROOT / src) as ds:
        T, nod = ds.transform, ds.nodata
        crs = CRS.from_wkt(ds.crs.to_wkt())
        # GDAL promedia al leer (respeta NoData): no se carga la resolución completa
        shape = (ds.height // block, ds.width // block)
        z = ds.read(1, out_shape=shape, resampling=Resampling.average)
    if crs.is_projected:
        # equirectangular en metros (LOLA, MOLA): pasar la georreferencia a grados
        tr = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)
        (lo_a, la_a), (lo_b, la_b) = tr.transform(T.c, T.f), tr.transform(T.c + T.a, T.f + T.e)
        lon_deg0, dlon_deg, lat_deg0, dlat_deg = lo_a, lo_b - lo_a, la_a, la_b - la_a
    else:
        lon_deg0, dlon_deg, lat_deg0, dlat_deg = T.c, T.a, T.f, T.e
    # máscara de NoData (uint8) y relleno en su lugar con 0: el DEM se queda en su tipo
    # nativo (int16 en SRTMGL30/MOLA: ~1.5 GB en vez de 6 GB en float32)
    if np.issubdtype(z.dtype, np.floating):
        bad = ~np.isfinite(z) | (z < -1e30)
    else:
        bad = np.zeros(z.shape, bool)
    if nod is not None:
        bad |= z == nod
    if water_zero:
        bad |= z == 0
    nm = bad.astype(np.uint8)
    del bad
    z[nm.astype(bool)] = 0
    return z, nm, (lon_deg0, dlon_deg * block, lat_deg0, dlat_deg * block)



def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--body", choices=list(SOURCES), required=True)
    ap.add_argument("--spacing-km", type=float, default=128.0)
    ap.add_argument("--patch", type=int, default=128)
    ap.add_argument("--max-nodata-frac", type=float, default=0.0,
                   help="Tierra: fracción máxima de océano/NoData (se rellena con 0 m)")
    ap.add_argument("--limit", type=int, default=None, help="solo los primeros N centros (prueba)")
    ap.add_argument("--suffix", default="")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data/patches")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--centers", type=Path, default=None,
                    help="CSV con lat,lon,region: corta parches en esos centros (sitios de validación)")
    ap.add_argument("--px-m", type=float, default=SCALE,
                    help="tamaño de píxel en metros (gravity_scaled: Luna 6x, Marte 2.6x)")
    ap.add_argument("--block", type=int, default=None, help="promedio en bloques al leer (por defecto, el del cuerpo)")
    ap.add_argument("--id-offset", type=int, default=0)
    a = ap.parse_args()
    px_m = a.px_m

    src = SOURCES[a.body]
    R = RADIUS_M[a.body]
    t0 = time.time()
    zf, nm, (lon0, dlon, lat0, dlat) = load_global(src["path"], a.block or src["block"],
                                                  src.get("water_zero", False))
    to_m = src["to_m"]
    H, W = zf.shape
    lat_lo, lat_hi = lat0 + dlat * H, lat0
    valid = zf[nm == 0]
    print(f"[{a.body}] DEM {W}x{H} ({abs(dlon):.4f}°/px, {zf.dtype}), lat {lat_lo:.1f}..{lat_hi:.1f}, "
          f"rango {valid.min() * to_m:.0f}..{valid.max() * to_m:.0f} m, NoData {nm.mean():.1%}, "
          f"cargado en {time.time() - t0:.0f}s")
    del valid

    margin = (a.patch / 2 * px_m / R) * 180 / np.pi * 1.5
    regions = None
    if a.centers:
        cdf = pd.read_csv(a.centers)
        lats, lons, regions = cdf.lat.to_numpy(float), cdf.lon.to_numpy(float), cdf.region.tolist()
    else:
        lats, lons = fibonacci_centers(a.spacing_km, R, lat_lo + margin, lat_hi - margin)
    if a.limit:
        sel = np.random.default_rng(0).choice(len(lats), min(a.limit, len(lats)), replace=False)
        lats, lons = lats[np.sort(sel)], lons[np.sort(sel)]
    print(f"{len(lats)} centros (espaciado {a.spacing_km:.0f} km)")

    half = a.patch / 2
    g = (np.arange(a.patch) - half + 0.5) * px_m
    gx, gy = np.meshgrid(g, -g)                     # fila 0 = norte
    scale_lbl = int(round(px_m))
    tag = f"{a.body}_{scale_lbl}{a.suffix}" if scale_lbl != SCALE else f"{a.body}_{SCALE}{a.suffix}"
    a.out_dir.mkdir(parents=True, exist_ok=True)
    raw = a.out_dir / f"patches_{tag}.raw.tmp"
    rows, stats = [], dict(nodata=0, kept=0)
    gmin, gmax = np.inf, -np.inf
    with open(raw, "wb") as fout:
        for b in range(0, len(lats), a.batch):
            for i_c, (lat_c, lon_c) in enumerate(zip(lats[b:b + a.batch], lons[b:b + a.batch]), b):
                la, lo = laea_inverse(gx, gy, lat_c, lon_c, R)
                r = (la - lat0) / dlat - 0.5
                c = np.mod((lo - lon0) / dlon - 0.5, W)
                coords = np.stack([r.ravel(), c.ravel()])
                frac = ndimage.map_coordinates(nm, coords, order=0, mode="grid-wrap").mean()
                if frac > a.max_nodata_frac + 1e-6:
                    stats["nodata"] += 1
                    continue
                tile = ndimage.map_coordinates(zf, coords, output=np.float32, order=1,
                                               mode="grid-wrap").reshape(a.patch, a.patch) * to_m
                mean = float(tile.mean())
                fout.write((tile - mean).astype("<f2").tobytes())
                gmin, gmax = min(gmin, tile.min()), max(gmax, tile.max())
                holdout = False
                if a.body == "earth":
                    p1, p2 = np.radians(PINACATE[0]), np.radians(lat_c)
                    d = R / 1000 * np.arccos(np.clip(np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2)
                                                     * np.cos(np.radians(lon_c - PINACATE[1])), -1, 1))
                    holdout = d < HOLDOUT_KM + a.patch * px_m / 2000   # el parche toca el área
                rows.append(dict(body=a.body, scale_m=scale_lbl, lat=float(lat_c), lon=float(lon_c),
                                 crs=f"+proj=laea +lat_0={lat_c:.5f} +lon_0={lon_c:.5f} +R={R:.0f} +units=m",
                                 x=0.0, y=0.0, region=regions[i_c] if regions else src["region"],
                                 holdout=bool(holdout),
                                 elev_mean_m=mean, elev_min_m=float(tile.min()),
                                 elev_max_m=float(tile.max()), nodata_frac=float(frac)))
            print(f"  {min(b + a.batch, len(lats))}/{len(lats)}  guardados={len(rows)}  "
                  f"{time.time() - t0:.0f}s", flush=True)

    n = len(rows)
    npy = a.out_dir / f"patches_{tag}.npy"
    with open(npy, "wb") as out, open(raw, "rb") as src_f:
        np.lib.format.write_array_header_1_0(out, {"descr": "<f2", "fortran_order": False,
                                                   "shape": (n, a.patch, a.patch)})
        while chunk := src_f.read(64 << 20):
            out.write(chunk)
    os.remove(raw)
    meta = pd.DataFrame(rows)
    meta.insert(0, "patch_id", [f"{a.body}-{scale_lbl}-{i + a.id_offset:06d}" for i in range(n)])
    meta["src"], meta["src_idx"] = tag, np.arange(n)
    meta.to_parquet(a.out_dir / f"meta_{tag}.parquet", index=False)
    print(json.dumps(dict(body=a.body, n_patches=n, dropped_nodata=stats["nodata"],
                          elev_min_m=round(float(gmin), 1), elev_max_m=round(float(gmax), 1),
                          holdout=int(meta.holdout.sum()) if n else 0,
                          seconds=round(time.time() - t0, 1)), ensure_ascii=False))
    print("->", npy)


if __name__ == "__main__":
    main()
