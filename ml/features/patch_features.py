#!/usr/bin/env python
"""Características no geométricas por parche (todas con datos de los portales oficiales).

Para cada parche de data/artifacts/meta_{scale}.parquet se muestrea su huella real
(malla de 9 x 9 puntos en su proyección azimutal local) sobre cada rejilla y se
promedia; si menos de la mitad de los puntos tienen dato, el valor es NaN
("sin dato"). Nunca se rellena ni se interpola fuera de la cobertura.

  Tierra: tmax_k, tmin_k, trange_k (MODIS MOD11C3), albedo (MODIS MCD43C3, NIR)
  Luna:   tmax_k, tmin_k, trange_k (Diviner GCP; en el polo sur, tmax de la PRP),
          tavg_k (PRP, solo polo sur), albedo (LOLA ldam: polar 1 km o global 10 px/°),
          ice_distance_km (PRP: distancia mínima a hielo estable a <= 1 m, solo polo sur)
  Marte:  pendiente (bloque 4) -> todo NaN por ahora

Salida: data/artifacts/features_{scale}.parquet (patch_id + columnas, mismo orden que meta).
Con --meta/--out sirve para cualquier conjunto de parches (entrenamiento, evaluación).

  python -m ml.features.patch_features --scale 60
  python -m ml.features.patch_features --meta data/patches/meta_moon_60_train.parquet \
      --out data/patches/features_moon_60_train.parquet
"""
import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pyproj import CRS, Transformer

from ml.data.make_patches_global import RADIUS_M, laea_inverse

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[2]))
F = ROOT / "data/features"
COLS = ["tmax_k", "tmin_k", "trange_k", "tavg_k", "albedo", "ice_distance_km",
        "ice_frac", "soil_raw", "soil_pct", "precip_mm"]
# Luna y Marte: sin precipitación líquida por definición física (no es un dato inventado)
PRECIP_BY_DEFINITION = {"moon": 0.0, "mars": 0.0}


class Grid:
    """Rejilla cualquiera (geográfica o proyectada) leída completa en memoria."""

    def __init__(self, path, band, body, scale=1.0):
        with rasterio.open(path) as ds:
            self.a = ds.read(band).astype(np.float32)
            self.T = ds.transform
            nod = ds.nodata
            crs = CRS.from_wkt(ds.crs.to_wkt())
        if nod is not None and np.isfinite(nod):
            self.a[self.a == nod] = np.nan
        self.a[self.a < -1e30] = np.nan
        self.a *= scale
        geo = CRS.from_proj4(f"+proj=longlat +R={RADIUS_M[body]:.0f} +no_defs") \
            if body != "earth" else CRS.from_epsg(4326)
        self.tr = None if crs.is_geographic else Transformer.from_crs(geo, crs, always_xy=True)

    def sample(self, lon, lat):
        if self.tr is not None:
            x, y = self.tr.transform(lon, lat)
        else:
            x, y = lon, lat
        c = np.floor((x - self.T.c) / self.T.a).astype(int)
        r = np.floor((y - self.T.f) / self.T.e).astype(int)
        H, W = self.a.shape
        ok = (r >= 0) & (r < H) & (c >= 0) & (c < W)
        out = np.full(np.shape(lon), np.nan, np.float32)
        out[ok] = self.a[r[ok], c[ok]]
        return out


def footprint(lat, lon, scale_m, body, n=9, patch=128):
    half = patch * scale_m / 2
    g = np.linspace(-half, half, n)
    gx, gy = np.meshgrid(g, g)
    return laea_inverse(gx.ravel(), gy.ravel(), lat, lon, RADIUS_M[body])


def reduce(vals, how="mean", min_frac=0.5):
    ok = np.isfinite(vals)
    if ok.mean() < min_frac:
        return np.nan
    return float(np.nanmin(vals) if how == "min" else np.nanmean(vals))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=60)
    ap.add_argument("--tag", default="")
    ap.add_argument("--meta", type=Path, default=None, help="parquet de metadatos cualquiera")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    art = ROOT / "data/artifacts"
    meta_path = a.meta or art / f"meta_{a.scale}{a.tag}.parquet"
    out_path = a.out or art / f"features_{a.scale}{a.tag}.parquet"
    meta = pd.read_parquet(meta_path)
    out = pd.DataFrame({"patch_id": meta.patch_id})
    for c in COLS:
        out[c] = np.nan

    grids = {
        "earth": {"tmax_k": Grid(F / "earth_climate_005deg.tif", 1, "earth"),
                  "tmin_k": Grid(F / "earth_climate_005deg.tif", 2, "earth"),
                  "trange_k": Grid(F / "earth_climate_005deg.tif", 3, "earth"),
                  "albedo": Grid(F / "earth_climate_005deg.tif", 4, "earth"),
                  "ice_frac": Grid(F / "earth_extra_005deg.tif", 1, "earth"),
                  "soil_raw": Grid(F / "earth_extra_005deg.tif", 3, "earth"),
                  "precip_mm": Grid(F / "earth_extra_005deg.tif", 4, "earth")},
        "moon": {"tmax_k": Grid(F / "moon_thermal_global_05deg.tif", 1, "moon"),
                 "tmin_k": Grid(F / "moon_thermal_global_05deg.tif", 2, "moon"),
                 "trange_k": Grid(F / "moon_thermal_global_05deg.tif", 3, "moon"),
                 "albedo": Grid(ROOT / "data/raw/moon/lola_albedo/ldam_10_float.lbl", 1, "moon"),
                 "polar_tavg": Grid(F / "moon_polar_south_480m.tif", 1, "moon"),
                 "polar_tmax": Grid(F / "moon_polar_south_480m.tif", 2, "moon"),
                 "polar_ice": Grid(F / "moon_polar_south_480m.tif", 4, "moon"),
                 "polar_albedo": Grid(ROOT / "data/raw/moon/lola_albedo/ldam_50s_1000m_float.lbl", 1, "moon"),
                 "ice_frac": Grid(F / "moon_thermal_global_05deg.tif", 5, "moon"),
                 "polar_ice_surface": Grid(F / "moon_polar_south_480m.tif", 5, "moon"),
                 # abundancia de rocas de Diviner (DN x 0.001), solo entre 60° N y 60° S
                 "soil_raw": Grid(ROOT / "data/raw/moon/diviner_ra/dgdr_ra_avg_cyl_032_img.lbl", 1,
                                  "moon", scale=0.001)},
    }
    for i, row in enumerate(meta.itertuples()):
        if row.body not in grids:
            continue                                       # Marte: bloque 4
        G = grids[row.body]
        la, lo = footprint(row.lat, row.lon, row.scale_m, row.body)
        if row.body == "earth":
            for c in ["tmax_k", "tmin_k", "trange_k", "albedo", "ice_frac", "soil_raw", "precip_mm"]:
                out.iat[i, out.columns.get_loc(c)] = reduce(G[c].sample(lo, la))
        else:
            vals = {c: reduce(G[c].sample(lo, la)) for c in ["tmax_k", "tmin_k", "albedo",
                                                             "ice_frac", "soil_raw"]}
            vals["precip_mm"] = PRECIP_BY_DEFINITION[row.body]
            if row.lat <= -76:                             # cobertura de la PRP sur
                pt = reduce(G["polar_tmax"].sample(lo, la))
                if np.isfinite(pt):
                    vals["tmax_k"] = pt
                vals["tavg_k"] = reduce(G["polar_tavg"].sample(lo, la))
                vals["ice_distance_km"] = reduce(G["polar_ice"].sample(lo, la), "min")
                pa = reduce(G["polar_albedo"].sample(lo, la))
                if np.isfinite(pa):
                    vals["albedo"] = pa
                pi = reduce(G["polar_ice_surface"].sample(lo, la))
                if np.isfinite(pi):
                    vals["ice_frac"] = pi
            if np.isfinite(vals["tmax_k"]) and np.isfinite(vals["tmin_k"]):
                vals["trange_k"] = vals["tmax_k"] - vals["tmin_k"]
            for c, v in vals.items():
                out.iat[i, out.columns.get_loc(c)] = v
        if i % 10000 == 0:
            print(f"  {i}/{len(meta)}", flush=True)

    # percentil de "rocosidad" dentro de cada cuerpo (ATI y abundancia de rocas no son
    # la misma magnitud física: se compara qué tan rocoso es un lugar PARA SU CUERPO)
    # percentil contra la distribución GLOBAL del cuerpo (ml.features.reference), no
    # dentro de este archivo: el mismo valor da el mismo percentil en cualquier conjunto
    from ml.features.reference import percentile
    body = meta.body.to_numpy()
    for b in np.unique(body):
        m = body == b
        out.loc[m, "soil_pct"] = percentile(b, "soil_raw", out.loc[m, "soil_raw"].to_numpy())
    out.to_parquet(out_path, index=False)
    summ = out.assign(body=meta.body.values).groupby("body")[COLS].agg(
        lambda s: f"{s.notna().mean():.0%} | med {s.median():.2f}" if s.notna().any() else "sin dato")
    print(summ.T.to_string())
    print("->", out_path)


if __name__ == "__main__":
    main()
