#!/usr/bin/env python
"""Globe feature labels (frontend/src/scenes/assets/globe-labels.json).

Moon and Mars: IAU Gazetteer of Planetary Nomenclature (USGS), center points, no albedo or
satellite features; tier by diameter (Mars 1: >= 900 km, 2: 400-900 km, 3: 180-400 km; Moon scaled by radius, x0.51) plus a
few key exploration sites (tier 2). Earth: Natural Earth ne_10m_geography_regions_polys
(continents, deserts, ranges, plateaus, plains, tundra, basins), tier by SCALERANK
(1: 0-1, 2: 2, 3: 3), label point = representative point of the polygon.

  python frontend/tools/make_globe_labels.py
"""
import json
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[2]
NOM = ROOT / "data/raw/nomenclature"
NE = ROOT / "data/raw/earth/naturalearth/regions/ne_10m_geography_regions_polys.shp"
OUT = ROOT / "frontend/src/scenes/assets/globe-labels.json"
SKIP = ("Albedo", "Satellite", "Landing site")
SITES = {"moon": ["Shackleton", "Faustini", "Haworth", "Malapert", "Mons Mouton", "Amundsen"],
         "mars": ["Jezero", "Gale", "Gusev", "Arcadia Planitia", "Meridiani Planum"]}
CAP = {1: 12, 2: 60, 3: 120}


def planet(body):
    g = gpd.read_file(NOM / body.upper() / f"{body.upper()}_nomenclature_center_pts.shp")
    g = g[~g["type"].astype(str).str.startswith(SKIP) & (g["diameter"] > 0)]
    g = g[g["approval"].astype(str).str.contains("Adopted", case=False, na=True)]
    out, seen = [], set()
    k = 1.0 if body == "mars" else 0.51          # thresholds scale with the body radius (Moon/Mars)
    for tier, lo, hi in ((1, 900 * k, 1e9), (2, 400 * k, 900 * k), (3, 180 * k, 400 * k)):
        sel = g[(g["diameter"] >= lo) & (g["diameter"] < hi)].sort_values("diameter", ascending=False).head(CAP[tier])
        for _, r in sel.iterrows():
            if r["clean_name"] in seen:
                continue
            seen.add(r["clean_name"])
            out.append(dict(body=body, name=r["clean_name"], lat=round(float(r["center_lat"]), 2),
                            lon=round(((float(r["center_lon"]) + 180) % 360) - 180, 2), tier=tier))
    for name in SITES[body]:
        r = g[g["clean_name"] == name]
        if len(r) and name not in seen:
            r = r.iloc[0]
            out.append(dict(body=body, name=name, lat=round(float(r["center_lat"]), 2),
                            lon=round(((float(r["center_lon"]) + 180) % 360) - 180, 2), tier=2, site=True))
    return out


def nice(s):
    if not s.isupper():
        return s
    small = {"of", "the", "and", "de", "del"}
    return " ".join(w.lower() if w.lower() in small and i else w.capitalize() for i, w in enumerate(s.split()))


def earth():
    g = gpd.read_file(NE)
    keep = {"Continent", "Desert", "Range/mtn", "Plateau", "Plain", "Tundra", "Basin", "Lowland"}
    g = g[g["FEATURECLA"].isin(keep) & (g["SCALERANK"] <= 3)]
    out, seen = [], set()
    for tier, ranks in ((1, (0, 1)), (2, (2,)), (3, (3,))):
        order = {"Continent": 0, "Desert": 1, "Range/mtn": 2, "Plateau": 3}
        sel = g[g["SCALERANK"].isin(ranks)].assign(_o=lambda d: d["FEATURECLA"].map(order).fillna(9)).sort_values(["_o", "SCALERANK"]).head(CAP[tier])
        for _, r in sel.iterrows():
            name = nice(str(r["NAME_EN"] or r["NAME"]))
            if name in seen:
                continue
            seen.add(name)
            p = r.geometry.representative_point()
            out.append(dict(body="earth", name=name, lat=round(p.y, 2),
                            lon=round(p.x, 2), tier=tier))
    return out


labels = planet("moon") + planet("mars") + earth()
OUT.write_text(json.dumps(labels, ensure_ascii=False, separators=(",", ":")))
from collections import Counter
print(OUT, len(labels), Counter((l["body"], l["tier"]) for l in labels), f"{OUT.stat().st_size / 1e3:.0f} KB")
