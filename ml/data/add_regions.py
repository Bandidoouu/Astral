#!/usr/bin/env python
"""Asigna `region` = "Estado, País" a los parches terrestres con Natural Earth admin-1.

Natural Earth (dominio público) no es un portal del reto; se usa solo para
etiquetas legibles y se cita en las referencias (docs/datos.md §5).

Los centros que caen fuera de todo polígono (costa, pequeños desfases) toman el
estado más cercano. Modifica el parquet en su lugar.

  python -m ml.data.add_regions --meta data/patches/meta_earth_60.parquet
"""
import argparse
import os
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[2]))
NE = ROOT / "data/raw/earth/naturalearth/ne_10m_admin_1_states_provinces.shp"
COUNTRY_SHORT = {"United States of America": "USA"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", type=Path, default=ROOT / "data/patches/meta_earth_60.parquet")
    ap.add_argument("--max-nearest-km", type=float, default=30.0)
    a = ap.parse_args()

    meta = pd.read_parquet(a.meta)
    assert (meta.body == "earth").all()
    states = gpd.read_file(NE)[["name", "admin", "geometry"]].to_crs("EPSG:4326")
    pts = gpd.GeoDataFrame(meta[["patch_id"]].copy(),
                           geometry=gpd.points_from_xy(meta.lon, meta.lat), crs="EPSG:4326")

    j = gpd.sjoin(pts, states, how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    miss = j["name"].isna()
    if miss.any():
        # estado más cercano, en metros (Lambert de México)
        near = gpd.sjoin_nearest(pts[miss].to_crs("EPSG:6372"), states.to_crs("EPSG:6372"),
                                 how="left", distance_col="dist_m")
        near = near[~near.index.duplicated(keep="first")]
        far = near["dist_m"] > a.max_nearest_km * 1000
        j.loc[near.index, ["name", "admin"]] = near[["name", "admin"]].values
        print(f"{miss.sum()} centros fuera de polígono -> estado más cercano "
              f"({far.sum()} a más de {a.max_nearest_km} km)")

    country = j["admin"].map(lambda c: COUNTRY_SHORT.get(c, c))
    meta["region"] = (j["name"] + ", " + country).values
    meta["country"] = country.values
    meta.to_parquet(a.meta, index=False)

    print(meta["country"].value_counts().to_string())
    print("\nPinacate (holdout):", meta.loc[meta.holdout, "region"].value_counts().to_dict())
    print("\nTop estados:\n" + meta["region"].value_counts().head(8).to_string())


if __name__ == "__main__":
    main()
