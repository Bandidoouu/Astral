#!/usr/bin/env python
"""Corta parches de elevación 128x128 a 60 m/px (Luna polo sur y México).

Salida (ver CLAUDE.md, sección 7):
  data/patches/patches_{body}_60.npy    float16, N x 128 x 128
  data/patches/meta_{body}_60.parquet   patch_id, body, scale_m, lat, lon, crs,
                                        x, y, region, holdout, elev_mean_m, ...

IMPORTANTE: el .npy guarda la elevación RELATIVA a la media del parche (m).
La elevación absoluta es patch + elev_mean_m. Motivo: en float16 una altura
absoluta de 5000 m solo tiene resolución de 4 m (8 m a 8000 m), lo que mete
escalones de ~4° en la pendiente a 60 m/px. Relativa al parche, la resolución
es <= 0.5 m para relieves de hasta 1 km.

Ejemplos:
  python ml/data/make_patches.py --body moon
  python ml/data/make_patches.py --body earth
  # muestra pequeña (ventana en unidades de parche: fila0 fila1 col0 col1)
  python ml/data/make_patches.py --body moon --tile-window 55 64 55 64 --out-dir /tmp/x
"""
import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window
from pyproj import CRS, Geod, Transformer

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path.home() / "astral"))
SCALE_M = 60
PINACATE = (31.77, -113.50)  # lat, lon
HOLDOUT_KM = 50.0

SOURCES = {
    "moon": dict(path="data/raw/moon/ldem_75s_60m_float.lbl", to_m=1000.0,
                 region="Lunar south pole"),
    "earth": dict(path="data/raw/earth/mexico_60m.tif", to_m=1.0,
                  region="Mexico"),
}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--body", choices=list(SOURCES), required=True)
    p.add_argument("--patch", type=int, default=128)
    p.add_argument("--stride", type=int, default=128,
                   help="128 = rejilla sin traslape (índice); <128 = con traslape")
    p.add_argument("--moon-max-lat", type=float, default=-80.0,
                   help="Luna: solo parches con centro al sur de esta latitud")
    p.add_argument("--max-water-frac", type=float, default=0.0,
                   help="Tierra: fracción máxima de píxeles con elevación <= 0")
    p.add_argument("--tile-window", type=int, nargs=4, metavar=("R0", "R1", "C0", "C1"),
                   help="procesar solo estas filas/columnas de parches (prueba)")
    p.add_argument("--out-dir", type=Path, default=ROOT / "data/patches")
    p.add_argument("--suffix", default="", help="sufijo para los archivos de salida")
    return p.parse_args()


def write_npy_from_raw(raw_path, npy_path, n, patch):
    """Convierte el binario crudo float16 en un .npy con cabecera."""
    header = {"descr": "<f2", "fortran_order": False, "shape": (n, patch, patch)}
    with open(npy_path, "wb") as out, open(raw_path, "rb") as src:
        np.lib.format.write_array_header_1_0(out, header)
        while chunk := src.read(64 << 20):
            out.write(chunk)
    os.remove(raw_path)


def main():
    a = parse_args()
    src = SOURCES[a.body]
    P, S = a.patch, a.stride
    a.out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{a.body}_{SCALE_M}{a.suffix}"
    raw_path = a.out_dir / f"patches_{tag}.raw.tmp"
    npy_path = a.out_dir / f"patches_{tag}.npy"
    meta_path = a.out_dir / f"meta_{tag}.parquet"

    geod = Geod(ellps="WGS84")
    rows_meta = []
    stats = dict(grid=0, nodata=0, water=0, outside=0)
    gmin, gmax, gsum, gcount = np.inf, -np.inf, 0.0, 0

    with rasterio.Env(GDAL_CACHEMAX=1024), rasterio.open(ROOT / src["path"]) as ds:
        assert abs(ds.res[0] - SCALE_M) < 1e-6 and abs(ds.res[1] - SCALE_M) < 1e-6, ds.res
        crs = CRS.from_wkt(ds.crs.to_wkt())
        to_geo = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)
        crs_str = ds.crs.to_string() if ds.crs.to_epsg() else crs.to_proj4()
        nodata = ds.nodata
        n_r = (ds.height - P) // S + 1
        n_c = (ds.width - P) // S + 1
        r0, r1, c0, c1 = a.tile_window or (0, n_r, 0, n_c)
        r1, c1 = min(r1, n_r), min(c1, n_c)
        print(f"[{a.body}] raster {ds.width}x{ds.height}, rejilla {n_r}x{n_c}, "
              f"procesando filas {r0}-{r1} cols {c0}-{c1}, nodata={nodata}")
        T = ds.transform
        t0 = time.time()
        with open(raw_path, "wb") as fout:
            for r in range(r0, r1):
                y_off = r * S
                col_off = c0 * S
                width = (c1 - 1 - c0) * S + P
                strip = ds.read(1, window=Window(col_off, y_off, width, P))
                # centros de los parches de esta fila
                cols = np.arange(c0, c1)
                cx_pix = cols * S + P / 2.0
                cy_pix = np.full_like(cx_pix, y_off + P / 2.0)
                xs, ys = T * (cx_pix, cy_pix)
                lons, lats = to_geo.transform(xs, ys)
                lons = (np.asarray(lons) + 180.0) % 360.0 - 180.0
                lats = np.asarray(lats)
                for k, c in enumerate(cols):
                    stats["grid"] += 1
                    if a.body == "moon" and lats[k] > a.moon_max_lat:
                        stats["outside"] += 1
                        continue
                    x0 = (c - c0) * S
                    tile = strip[:, x0:x0 + P]
                    if nodata is not None and (np.isnan(tile).any() or
                                               (tile <= nodata * 0.999 if nodata < 0
                                                else tile == nodata).any()):
                        stats["nodata"] += 1
                        continue
                    elev = tile.astype(np.float64) * src["to_m"]
                    if a.body == "moon":
                        # Sanidad: LOLA viene en km relativos a 1737.4 km.
                        assert np.abs(tile).max() < 25, "¿LOLA no viene en km?"
                    if a.body == "earth" and (elev <= 0).mean() > a.max_water_frac:
                        stats["water"] += 1
                        continue
                    mean = float(elev.mean())
                    fout.write((elev - mean).astype("<f2").tobytes())
                    gmin, gmax = min(gmin, elev.min()), max(gmax, elev.max())
                    gsum += elev.sum(); gcount += elev.size
                    holdout = False
                    if a.body == "earth":
                        _, _, d = geod.inv(PINACATE[1], PINACATE[0], lons[k], lats[k])
                        holdout = d / 1000.0 < HOLDOUT_KM
                    rows_meta.append(dict(
                        body=a.body, scale_m=SCALE_M, lat=float(lats[k]), lon=float(lons[k]),
                        crs=crs_str, x=float(xs[k]), y=float(ys[k]),
                        region="El Pinacate, Sonora" if holdout else src["region"],
                        holdout=holdout, elev_mean_m=mean,
                        elev_min_m=float(elev.min()), elev_max_m=float(elev.max()),
                        row=int(y_off), col=int(c * S)))
                if (r - r0) % 20 == 0:
                    print(f"  fila {r}/{r1}  parches={len(rows_meta)}  "
                          f"{time.time() - t0:.0f}s", flush=True)

    n = len(rows_meta)
    if n == 0:
        os.remove(raw_path)
        raise SystemExit(f"Sin parches válidos. {stats}")
    write_npy_from_raw(raw_path, npy_path, n, P)
    meta = pd.DataFrame(rows_meta)
    meta.insert(0, "patch_id", [f"{a.body}-{SCALE_M}-{i:06d}" for i in range(n)])
    meta.to_parquet(meta_path, index=False)

    summary = dict(body=a.body, n_patches=n, **stats,
                   elev_min_m=round(gmin, 1), elev_max_m=round(gmax, 1),
                   elev_mean_m=round(gsum / gcount, 1),
                   holdout=int(meta.holdout.sum()),
                   lat_range=[round(meta.lat.min(), 3), round(meta.lat.max(), 3)],
                   lon_range=[round(meta.lon.min(), 3), round(meta.lon.max(), 3)],
                   seconds=round(time.time() - t0, 1))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"-> {npy_path}\n-> {meta_path}")


if __name__ == "__main__":
    main()
