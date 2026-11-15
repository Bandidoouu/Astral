#!/usr/bin/env python
"""Resultados REALES precalculados para la demo (modelo v2) y metadatos de aptitud.

1. Corre la búsqueda real (`ml.search.Searcher`: RRF, perfil general, k = 10) sobre las
   listas curadas y guarda las respuestas en el formato del contrato:
     frontend/src/mocks/precomputed-results.json
   Escalas: 1000 (`same_size` y `gravity_scaled`) y 60 donde aplica (Luna al sur de
   80° S, Tierra dentro de la caja de México). Cada respuesta lleva `precomputed`.
2. Exporta los metadatos de aptitud por cuerpo, listos para servir:
     data/artifacts/suitability/api_moon_south.json   (GET /api/suitability/moon_south)
     data/artifacts/suitability/api_mars.json          (GET /api/suitability/mars)

  python -m ml.demo_results
"""
import datetime as dt
import json
import os
from pathlib import Path

from ml.search import Searcher

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
ART = ROOT / "data/artifacts"
OUT = ROOT / "frontend/src/mocks/precomputed-results.json"
ENCODERS = {"60": "encoder_v2sel.pt", "1000": "encoder_v2_1000.pt"}
K = 10

MARS_SITES = [("jezero", "Jezero crater (Perseverance)", 18.38, 77.58),
              ("gale", "Gale crater (Curiosity)", -5.40, 137.80),
              ("arcadia", "Arcadia Planitia (shallow ice)", 40.0, -160.0),
              ("insight", "Elysium Planitia (InSight)", 4.50, 135.62),
              ("opportunity", "Meridiani Planum (Opportunity)", -1.95, -5.53),
              ("spirit", "Gusev crater (Spirit)", -14.57, 175.47)]
EARTH_SITES = [("mauna_loa", "Mauna Loa, Hawaii (HI-SEAS analog habitat)", 19.48, -155.60),
               ("mdrs", "Mars Desert Research Station, Utah", 38.4063, -110.7918),
               ("el_pinacate", "El Pinacate, Sonora (Apollo training site)", 31.77, -113.50)]
MEXICO_BOX = (-118, 14, -86, 33)


def curated():
    moon = json.loads((ART / "suitability/suitability_moon.json").read_text())["candidates"]
    sites = [dict(id=c["name"].lower().replace(" ", "_").replace("(", "").replace(")", ""),
                  name=c["name"], group=c["group"], body="moon", lat=c["lat"], lon=c["lon"]) for c in moon]
    sites += [dict(id=i, name=n, group="Mars missions and candidates", body="mars", lat=a, lon=b)
              for i, n, a, b in MARS_SITES]
    sites += [dict(id=i, name=n, group="Earth analog stations", body="earth", lat=a, lon=b)
              for i, n, a, b in EARTH_SITES]
    return sites


def has_detail(s):
    if s["body"] == "moon":
        return s["lat"] <= -80
    if s["body"] == "earth":
        lo0, la0, lo1, la1 = MEXICO_BOX
        return lo0 <= s["lon"] <= lo1 and la0 <= s["lat"] <= la1
    return False


def precompute():
    S = Searcher()
    generated = dt.datetime.now().isoformat(timespec="seconds")
    sites = curated()
    for s in sites:
        others = [b for b in ("earth", "moon", "mars") if b != s["body"]]
        runs = {"1000": (1000, "same_size", others), "1000_gravity": (1000, "gravity_scaled", others)}
        if has_detail(s):
            runs["60"] = (60, "same_size", ["earth" if s["body"] == "moon" else "moon"])
        s["responses"] = {}
        for key, (scale, mode, targets) in runs.items():
            r = S.search(s["body"], s["lat"], s["lon"], targets, k=K, profile="general", method="rrf",
                         scale_m=scale, scale_mode=mode)
            r["precomputed"] = dict(source="precomputed with the real ASTRAL search (ml.search.Searcher)",
                                    model="v2", encoder=ENCODERS[str(scale)], release="v2-1km",
                                    method="rrf", profile="general", k=K, generated=generated)
            s["responses"][key] = r
        n = {k: len(v["results"]) for k, v in s["responses"].items()}
        print(f"  {s['body']:<5} {s['name']:<44} {n}")
    doc = dict(precomputed=dict(model="v2", encoders=ENCODERS, release="v2-1km", method="rrf",
                                profile="general", k=K, generated=generated,
                                note="Real model outputs, not illustrative. Earth results only from "
                                     "promising zones (MODIS MCD12C1)."),
               sites=sites)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    print(f"-> {OUT} ({OUT.stat().st_size / 1e6:.2f} MB, {len(sites)} sitios)")


def suitability_api():
    moon = json.loads((ART / "suitability/suitability_moon.json").read_text())
    zones = json.loads((ART / "suitability/recommended_zones.json").read_text())
    moon_api = dict(moon, body="moon", region="south_pole", recommended_zones=zones,
                    images={k: f"/api/suitability/moon_south/{k}" for k in
                            ["landing", "rover", "ice", "temperature", "total"]})
    (ART / "suitability/api_moon_south.json").write_text(json.dumps(moon_api, indent=1, allow_nan=False))

    mars = json.loads((ART / "suitability/suitability_mars.json").read_text())
    import numpy as np
    import rasterio
    with rasterio.open(ART / "suitability/mars_total.tif") as ds:
        tot = ds.read(1)
        lat_top, lon_left, cell = ds.transform.f, ds.transform.c, ds.transform.a
    # zonas recomendadas de Marte: mejores celdas de 2° x 2° (puntaje medio), separadas >= 10°
    k = int(round(2 / cell))
    H, W = (tot.shape[0] // k) * k, (tot.shape[1] // k) * k
    blk = tot[:H, :W].reshape(H // k, k, W // k, k)
    with np.errstate(invalid="ignore"):
        m = np.nanmean(blk, (1, 3))
        cov = np.isfinite(blk).mean((1, 3))
    m[cov < 0.9] = np.nan
    order = np.argsort(-np.nan_to_num(m, nan=-1).ravel())
    picked = []
    for idx in order:
        r, c = divmod(int(idx), m.shape[1])
        if not np.isfinite(m[r, c]):
            break
        la = lat_top - (r + 0.5) * k * cell
        lo = (lon_left + (c + 0.5) * k * cell + 180) % 360 - 180
        if all(abs(la - p["lat"]) >= 10 or abs(((lo - p["lon"]) + 180) % 360 - 180) >= 10 for p in picked):
            picked.append(dict(rank=len(picked) + 1, lat=round(float(la), 2), lon=round(float(lo), 2),
                               total=round(float(m[r, c]), 3), size_deg=2))
        if len(picked) == 15:
            break
    # mismo formato que la Luna: total_p90 (percentil 90 dentro de 50 km) y percentil contra
    # celdas de Marte al azar (60 N a 60 S, donde hay dato de los cuatro criterios)
    lat = lat_top - (np.arange(tot.shape[0]) + 0.5) * cell
    lon = lon_left + (np.arange(tot.shape[1]) + 0.5) * cell
    valid = tot[np.isfinite(tot)]
    for c in mars["candidates"]:
        p1, p2 = np.radians(c["lat"]), np.radians(lat)[:, None]
        cc = np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(np.radians(lon[None] - c["lon"]))
        d = 3396.19 * np.arccos(np.clip(cc, -1, 1))
        v = tot[(d <= 50) & np.isfinite(tot)]
        p90 = float(np.percentile(v, 90)) if v.size else None
        c["total_p90"] = None if p90 is None else round(p90, 3)
        c["percentile_vs_random"] = None if p90 is None else round(100 * float((valid < p90).mean()), 1)
        c["zone"] = "disc"
        c["radius_km"] = 50
    mars["grid"] = dict(mars["grid"], pixel_m=round(cell * np.pi / 180 * 3396190))
    mars_api = dict(mars, body="mars", region="global",
                    recommended_zones=dict(method="top 2x2 deg cells by mean total score, at least 10 deg apart",
                                           zones=picked),
                    images={k: f"/api/suitability/mars/{k}" for k in
                            ["landing", "rover", "elevation", "hydrogen", "total"]})
    (ART / "suitability/api_mars.json").write_text(json.dumps(mars_api, indent=1, allow_nan=False))
    print("->", ART / "suitability/api_moon_south.json", "y api_mars.json;",
          f"zonas de Marte: {len(picked)}, mejor {picked[0] if picked else None}")


def main():
    precompute()
    suitability_api()


if __name__ == "__main__":
    main()
