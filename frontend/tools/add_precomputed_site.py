#!/usr/bin/env python
"""Agrega sitios curados a src/mocks/precomputed-results.json consultando la API REAL
(backend con release v2-1km-r4). Mismo formato y mismos parámetros que ml/demo_results.py
(RRF, perfil general, k = 10; 1000 same_size y gravity_scaled). No toca ML.

  python frontend/tools/add_precomputed_site.py http://127.0.0.1:8000
"""
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

API = sys.argv[1].rstrip("/")
PATH = Path(__file__).resolve().parents[1] / "src/mocks/precomputed-results.json"
SITES = [
    dict(id="olympus_mons", name="Olympus Mons", group="Mars missions and candidates", body="mars",
         lat=18.65, lon=-133.8),
    dict(id="montes_marius", name="Montes Marius (lunar volcanic domes)", group="Lunar validation sites",
         body="moon", lat=14.0, lon=-56.0),
]


def post(payload):
    req = urllib.request.Request(f"{API}/api/similar", json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


doc = json.loads(PATH.read_text())
template = doc["sites"][0]["responses"]["1000"]["precomputed"]
generated = dt.datetime.now().isoformat(timespec="seconds")
doc["sites"] = [s for s in doc["sites"] if s["id"] not in {x["id"] for x in SITES}]
for site in SITES:
    others = [b for b in ("earth", "moon", "mars") if b != site["body"]]
    site["responses"] = {}
    for key, mode in (("1000", "same_size"), ("1000_gravity", "gravity_scaled")):
        r = post(dict(body=site["body"], lat=site["lat"], lon=site["lon"], target_bodies=others, k=10,
                      profile="general", method="rrf", scale_m=1000, scale_mode=mode))
        r["precomputed"] = dict(template, generated=generated,
                                source="precomputed with the real ASTRAL search via the backend API")
        site["responses"][key] = r
    doc["sites"].append(site)
    print(site["name"], {k: [x["region"] for x in v["results"] if x["body"] == "earth"][:4] for k, v in site["responses"].items()})
PATH.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
print("->", PATH, len(doc["sites"]), "sitios")
