#!/usr/bin/env python
"""Zonas recomendadas: las N mejores zonas de la capa de aptitud lunar (polo sur).

Se suaviza el puntaje total con una media de 5 x 5 celdas (2.4 km) para premiar zonas,
no píxeles sueltos; se eligen los máximos separados al menos --min-sep-km; para cada
zona se dan coordenadas, el puntaje total y por criterio (media en un radio de 2 km),
y una frase con el porqué construida con los criterios más fuertes y el más débil.
Mismas advertencias que la capa: faltan iluminación y visibilidad de la Tierra.

  python -m ml.recommended_zones --n 15
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from scipy import ndimage

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
S = ROOT / "data/artifacts/suitability"
CRIT = ["landing", "rover", "ice", "temperature"]
PHRASE = {"landing": "gentle slopes for landing (most of the area under 8°)",
          "rover": "drivable terrain (slopes under 15°)",
          "ice": "close to surface-accessible stable ice",
          "temperature": "temperatures compatible with sunlit operations"}
WEAK = {"landing": "limited flat ground for landing",
        "rover": "steeper terrain for rovers",
        "ice": "farther from stable ice",
        "temperature": "very cold or shadowed (likely little sunlight)"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--min-sep-km", type=float, default=15.0)
    a = ap.parse_args()
    layers = {}
    for k in CRIT + ["total"]:
        with rasterio.open(S / f"moon_south_{k}.tif") as ds:
            layers[k] = ds.read(1)
            T, crs = ds.transform, CRS.from_wkt(ds.crs.to_wkt())
    px_km = T.a / 1000
    tot = layers["total"]
    valid = np.isfinite(tot)
    sm = ndimage.uniform_filter(np.nan_to_num(tot), 5) / np.maximum(
        ndimage.uniform_filter(valid.astype(float), 5), 1e-6)
    sm[ndimage.uniform_filter(valid.astype(float), 5) < 0.99] = -1   # zonas completas
    to_geo = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)
    info = json.loads((S / "suitability_moon.json").read_text())
    order = np.argsort(sm.ravel())[::-1]
    sep = a.min_sep_km / px_km
    picks, rr, cc = [], *np.mgrid[0:tot.shape[0], 0:tot.shape[1]]
    for flat in order:
        r, c = divmod(int(flat), tot.shape[1])
        if sm[r, c] <= 0:
            break
        if all(np.hypot(r - p[0], c - p[1]) >= sep for p in picks):
            picks.append((r, c))
        if len(picks) == a.n:
            break
    zones = []
    for i, (r, c) in enumerate(picks, 1):
        m = (rr - r) ** 2 + (cc - c) ** 2 <= (2.0 / px_km) ** 2
        sc = {k: round(float(np.nanmean(layers[k][m])), 3) for k in CRIT}
        x, y = T * (c + 0.5, r + 0.5)
        lon, lat = to_geo.transform(x, y)
        strong = sorted(CRIT, key=lambda k: -sc[k] * info["weights"][k])[:2]
        weak = min(CRIT, key=lambda k: sc[k])
        why = f"Strong on {PHRASE[strong[0]]} and {PHRASE[strong[1]]}"
        why += f"; weakest point: {WEAK[weak]}." if sc[weak] < 0.7 else "; no weak criterion."
        zones.append(dict(rank=i, lat=round(float(lat), 4), lon=round(float(lon), 4),
                          total=round(float(sm[r, c]), 3), scores=sc, why=why))
        print(f"{i:2d}  {lat:7.3f} {lon:8.3f}  total {sm[r, c]:.3f}  {sc}")
    out = dict(description="Top suitability zones, lunar south pole (transparent rules, not the network)",
               weights=info["weights"], rules=info["rules"], min_separation_km=a.min_sep_km,
               zone_radius_km=2.0, missing=info["missing"], caveat=info["caveat"], zones=zones)
    (S / "recommended_zones.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("->", S / "recommended_zones.json")


if __name__ == "__main__":
    main()
