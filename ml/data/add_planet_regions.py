#!/usr/bin/env python
"""Asigna `region` legible a los parches de la Luna y Marte con la nomenclatura oficial
de la IAU (Gazetteer of Planetary Nomenclature, USGS; ver docs/datos.md §5).

Regla (la misma para los dos cuerpos):
  1. Entre los accidentes con nombre (sin rasgos de albedo ni satélites) con diámetro
     >= 80% del lado del parche (60 m: 6 km; 1 km: 100 km; gravity: 270-620 km), el más PEQUEÑO que contenga
     el centro del parche (distancia <= radio)  ->  "Mare Imbrium, Moon"
  2. Si ninguno lo contiene, el de menor distancia/radio a <= 300 km  ->  "near Copernicus, Moon"
  3. Si no, se repite con accidentes de >= 20 km; si tampoco, se queda "Moon" / "Mars".
Solo cambia la columna `region` de las filas de la Luna y Marte. Modifica los parquet en su lugar.

  python -m ml.data.add_planet_regions --meta data/artifacts/meta_1000.parquet
"""
import argparse
import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[2]))
NOM = ROOT / "data/raw/nomenclature"
RADIUS_KM = {"moon": 1737.4, "mars": 3396.19}
SKIP_TYPES = ("Albedo", "Satellite", "Landing site")
_CACHE = {}


def features(body):
    if body not in _CACHE:
        g = gpd.read_file(NOM / body.upper() / f"{body.upper()}_nomenclature_center_pts.shp")
        g = pd.DataFrame(g.drop(columns="geometry"))
        g = g[~g["type"].astype(str).str.startswith(SKIP_TYPES) & (g["diameter"] > 0)]
        g = g[g["approval"].astype(str).str.contains("Adopted", case=False, na=True)]
        _CACHE[body] = g.reset_index(drop=True)
    return _CACHE[body]


def label(body, lat, lon, min_diam_km):
    g = features(body)
    g = g[g["diameter"] >= min_diam_km]
    R = RADIUS_KM[body]
    p1, p2 = np.radians(lat), np.radians(g["center_lat"].to_numpy())
    c = np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(np.radians(g["center_lon"].to_numpy() - lon))
    d = R * np.arccos(np.clip(c, -1, 1))
    r = g["diameter"].to_numpy() / 2
    inside = np.flatnonzero(d <= r)
    name = body.capitalize()
    if inside.size:
        return f"{g['clean_name'].iat[inside[np.argmin(r[inside])]]}, {name}"
    j = int(np.argmin(d / r))
    if d[j] <= 300:
        return f"near {g['clean_name'].iat[j]}, {name}"
    if min_diam_km > 20:                     # tierras altas sin accidentes grandes cerca
        return label(body, lat, lon, 20)
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", type=Path, nargs="+", required=True)
    a = ap.parse_args()
    for p in a.meta:
        m = pd.read_parquet(p)
        rows = np.flatnonzero(m.body.isin(["moon", "mars"]).to_numpy())
        if not rows.size:
            continue
        labels = [label(m.body.iat[i], m.lat.iat[i], m.lon.iat[i], max(5.0, 0.8 * 128 * m.scale_m.iat[i] / 1000))
                  for i in rows]
        m.iloc[rows, m.columns.get_loc("region")] = labels
        m.to_parquet(p, index=False)
        s = pd.Series(labels)
        print(f"{p.name}: {len(rows):,} parches; con nombre {100 * (~s.isin(['Moon', 'Mars'])).mean():.0f}%; "
              f"ejemplos {s.value_counts().head(4).to_dict()}")


if __name__ == "__main__":
    main()
