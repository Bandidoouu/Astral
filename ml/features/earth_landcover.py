#!/usr/bin/env python
"""Zonas prometedoras de la Tierra con MODIS MCD12C1 (cobertura del suelo, IGBP, 0.05°).

Recomendación de un mentor: los gemelos terrestres de la Luna y Marte solo salen de
zonas donde un análogo tiene sentido. Clases IGBP:

  se quedan  7 matorral disperso (open shrublands), 10 pastizal, 15 nieve y hielo
             permanente, 16 suelo desnudo y desiertos (barren)
  se van     0 agua, 1-5 bosques y selvas, 11 humedales, 12 cultivos, 13 urbano,
             14 mosaico de cultivo y vegetación
  también se van (no están en la lista de las que se quedan): 6 matorral cerrado,
             8 sabana arbolada, 9 sabana

Un parche es prometedor si al menos la mitad de su área (porcentajes por clase de
`Land_Cover_Type_1_Percent`, celdas dentro de su ventana) es de clases que se quedan.
El agua (océano incluido) cuenta como no prometedora.

  python -m ml.features.earth_landcover --build
  python -m ml.features.earth_landcover --annotate data/artifacts/meta_60.parquet
"""
import argparse
import os
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[2]))
RAW = ROOT / "data/raw/earth/landcover"
OUT = ROOT / "data/artifacts/earth_landcover_005deg.tif"    # lo lee la búsqueda
TMP = ROOT / "data/features/tmp"

KEEP = (7, 10, 15, 16)
NAMES = {0: "water", 1: "evergreen needleleaf forest", 2: "evergreen broadleaf forest",
         3: "deciduous needleleaf forest", 4: "deciduous broadleaf forest", 5: "mixed forest",
         6: "closed shrubland", 7: "open shrubland", 8: "woody savanna", 9: "savanna",
         10: "grassland", 11: "permanent wetland", 12: "cropland", 13: "urban",
         14: "cropland/natural mosaic", 15: "permanent snow and ice", 16: "barren"}
MIN_FRAC = 0.5
EARTH_KM = 6371.0


def _sds(name):
    hdf = sorted(RAW.glob("MCD12C1.A2023001*.hdf"))[0]
    TMP.mkdir(parents=True, exist_ok=True)
    tmp = TMP / f"lc_{name}.tif"
    subprocess.run(["gdal_translate", "-q", f'HDF4_EOS:EOS_GRID:"{hdf}":MOD12C1:{name}', str(tmp)],
                   check=True)
    with rasterio.open(tmp) as ds:
        a = ds.read()
    tmp.unlink()
    return a


def build():
    major = _sds("Majority_Land_Cover_Type_1")[0].astype(np.uint8)          # (3600, 7200)
    pct = _sds("Land_Cover_Type_1_Percent").astype(np.float32)              # (17, 3600, 7200)
    keep = pct[list(KEEP)].sum(0) / 100.0
    prof = dict(driver="GTiff", height=3600, width=7200, count=2, dtype="uint8",
                crs="EPSG:4326", transform=from_origin(-180, 90, 0.05, 0.05),
                compress="deflate", tiled=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(OUT, "w", **prof) as ds:
        ds.write(major, 1)
        ds.write(np.round(keep * 100).astype(np.uint8), 2)
        ds.set_band_description(1, "igbp_majority_class")
        ds.set_band_description(2, "promising_pct")
    land = major != 0
    print(f"-> {OUT}; tierra firme prometedora (por área de celda): "
          f"{100 * (keep[land] >= MIN_FRAC).mean():.1f}% de las celdas de tierra")


class LandCover:
    def __init__(self, path=OUT):
        with rasterio.open(path) as ds:
            self.major = ds.read(1)
            self.keep = ds.read(2).astype(np.float32) / 100.0

    @staticmethod
    def _rc(lat, lon):
        r = np.clip(((90 - np.asarray(lat)) / 0.05).astype(int), 0, 3599)
        c = np.clip((((np.asarray(lon) + 180) % 360) / 0.05).astype(int), 0, 7199)
        return r, c

    def at(self, lat, lon):
        """Clase IGBP del punto: dict(code, name, promising)."""
        r, c = self._rc(lat, lon)
        code = int(self.major[r, c])
        return dict(code=code, name=NAMES.get(code, "unknown"), promising=code in KEEP)

    def patch_frac(self, lat, lon, half_km):
        """Fracción prometedora media dentro de la ventana (cuadrada) del parche."""
        dlat = np.degrees(half_km / EARTH_KM)
        dlon = dlat / max(np.cos(np.radians(lat)), 0.05)
        r0, c0 = self._rc(lat + dlat, lon - dlon)
        r1, c1 = self._rc(lat - dlat, lon + dlon)
        rows = np.arange(r0, r1 + 1)
        cols = np.arange(c0, c0 + int(round(2 * dlon / 0.05)) + 1) % 7200
        w = np.cos(np.radians(90 - (rows + 0.5) * 0.05))[:, None]
        k = self.keep[np.ix_(rows, cols)]
        return float((k * w).sum() / (w.sum() * len(cols)))


def annotate(meta, lc=None):
    """Agrega lc_class, lc_name, promising_frac y promising a los parches terrestres."""
    lc = lc or LandCover()
    meta = meta.copy()
    meta["lc_class"] = -1
    meta["lc_name"] = None
    meta["promising_frac"] = np.nan
    meta["promising"] = True                      # Luna y Marte no se filtran
    e = np.flatnonzero(meta.body.to_numpy() == "earth")
    if len(e):
        half_km = 64 * meta.scale_m.to_numpy()[e] / 1000
        lat, lon = meta.lat.to_numpy()[e], meta.lon.to_numpy()[e]
        r, c = lc._rc(lat, lon)
        codes = lc.major[r, c].astype(int)
        frac = np.array([lc.patch_frac(a, b, h) for a, b, h in zip(lat, lon, half_km)])
        meta.iloc[e, meta.columns.get_loc("lc_class")] = codes
        meta.iloc[e, meta.columns.get_loc("lc_name")] = [NAMES.get(x, "unknown") for x in codes]
        meta.iloc[e, meta.columns.get_loc("promising_frac")] = frac
        meta.iloc[e, meta.columns.get_loc("promising")] = frac >= MIN_FRAC
    return meta


def report(meta):
    e = meta[meta.body == "earth"]
    if not len(e):
        return
    print(f"  Tierra: {e.promising.sum():,} de {len(e):,} parches prometedores "
          f"({100 * e.promising.mean():.1f}%)")
    vc = e.lc_name.value_counts(normalize=True).head(8)
    print("  clase mayoritaria en el centro:", ", ".join(f"{k} {100 * v:.0f}%" for k, v in vc.items()))
    if "holdout" in e:
        h = e[e.holdout]
        if len(h):
            print(f"  El Pinacate (holdout): {h.promising.sum()} de {len(h)} prometedores")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--annotate", nargs="*", default=[], type=Path)
    a = ap.parse_args()
    if a.build:
        build()
    lc = LandCover() if a.annotate else None
    for p in a.annotate:
        m = annotate(pd.read_parquet(p), lc)
        m.to_parquet(p)
        print(p)
        report(m)


if __name__ == "__main__":
    main()
