#!/usr/bin/env python
"""Precalcula la búsqueda offline de 1 km para TODOS los parches del índice (los tres
cuerpos) consultando la API REAL (backend con release v2-1km-r4). No toca ML.

Por cada parche de origen: POST /api/similar en su centro, hacia los otros dos cuerpos,
k = 10, método rrf, perfil general, scale_m 1000, same_size. El orden (RRF de terreno) no
depende del perfil; el porcentaje sí, y se recalcula en el navegador con las siete
dimensiones guardadas (mismos pesos que ml/search.py PROFILES).

Salida en frontend/public/data/offline1km/:
  catalog.json        columnas por parche: patch_id, cuerpo, lat, lon, región, cobertura,
                      atributos (10, redondeados a 3 decimales como la API)
  results_{body}_{NNN}.bin  bloques de 256 parches de origen de ese cuerpo (orden del catálogo); por
                      cada cuerpo destino (orden earth, moon, mars sin el origen), 10 x
                      [uint16 índice del parche resultado, 7 x uint16 puntaje x 10000];
                      65535 = sin dato / relleno. Little-endian.

  python frontend/tools/precompute_offline_grid.py http://127.0.0.1:8000 \
      data/artifacts/release/v2-1km-r4
"""
import concurrent.futures as cf
import datetime as dt
import json
import struct
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

API, REL = sys.argv[1].rstrip("/"), Path(sys.argv[2])
# optional 3rd argument: gravity_scaled (Moon windows 6x, Mars 2.6x; artifacts *_1000_gravity)
MODE = sys.argv[3] if len(sys.argv) > 3 else "same_size"
TAG = "_gravity" if MODE == "gravity_scaled" else ""
OUT = Path(__file__).resolve().parents[1] / f"public/data/offline1km{TAG}"
BODIES = ["earth", "moon", "mars"]
DIMS = ["terrain", "operations", "thermal", "albedo", "ice", "soil", "aridity"]
ATTRS = ["tmax_k", "tmin_k", "trange_k", "albedo", "ice_distance_km", "ice_frac", "soil_raw",
         "soil_pct", "precip_mm", "h2o_wt_pct"]
K, NULL = 10, 65535
KEEP = (7, 10, 15, 16)     # clases IGBP prometedoras (ml/features/earth_landcover.py)


def post(payload):
    req = urllib.request.Request(f"{API}/api/similar", json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1)


CHUNK = 256   # parches de origen por archivo (~80 KB): la primera búsqueda baja solo uno


def write_chunks(body, rows):
    for old in OUT.glob(f"results_{body}*.bin"):
        old.unlink()
    for c in range(0, len(rows), CHUNK):
        (OUT / f"results_{body}_{c // CHUNK:03d}.bin").write_bytes(b"".join(rows[c:c + CHUNK]))


def num(v):
    return None if v is None or not np.isfinite(v) else round(float(v), 3)


def main():
    meta = pd.read_parquet(REL / f"meta_1000{TAG}.parquet")
    feats = pd.read_parquet(REL / f"features_1000{TAG}.parquet").reindex(columns=["patch_id"] + ATTRS)
    assert (feats.patch_id.values == meta.patch_id.values).all()
    index = {pid: i for i, pid in enumerate(meta.patch_id)}
    regions = sorted(meta.region.astype(str).unique())
    lcs = sorted(x for x in meta.lc_name.dropna().unique())
    lc_class = meta.lc_class.fillna(-1).astype(int).to_numpy()
    catalog = dict(
        format="astral-offline-1km-v1", chunk=CHUNK,
        precomputed=dict(source="precomputed with the real ASTRAL search via the backend API", model="v2",
                         encoder="encoder_v2_1000.pt", release="v2-1km-r4", method="rrf", k=K,
                         scale_m=1000, scale_mode=MODE,
                         generated=dt.datetime.now().isoformat(timespec="seconds")),
        bodies=BODIES, dims=DIMS, attr_cols=ATTRS, regions=regions, land_cover=lcs,
        patch_id=meta.patch_id.tolist(), body=[BODIES.index(b) for b in meta.body],
        lat=[round(float(x), 4) for x in meta.lat], lon=[round(float(x), 4) for x in meta.lon],
        region=[regions.index(str(r)) for r in meta.region],
        lc=[lcs.index(x) if isinstance(x, str) else -1 for x in meta.lc_name],
        lc_code=lc_class.tolist(),
        scale_m=[int(x) for x in meta.scale_m],     # pixel size per patch: window_km = 128 * scale_m / 1000
        attrs=[[num(v) for v in row] for row in feats[ATTRS].to_numpy(np.float64)],
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "catalog.json").write_text(json.dumps(catalog, separators=(",", ":"), allow_nan=False))

    def run(i):
        b = meta.body.iat[i]
        targets = [t for t in BODIES if t != b]
        r = post(dict(body=b, lat=float(meta.lat.iat[i]), lon=float(meta.lon.iat[i]), target_bodies=targets,
                      k=K, profile="general", method="rrf", scale_m=1000, scale_mode=MODE))
        qp = {t: r["query"]["patches"][t]["patch_id"] for t in targets}
        assert all(p == meta.patch_id.iat[i] for p in qp.values()), (i, qp)
        buf = bytearray()
        for t in targets:
            res = [x for x in r["results"] if x["body"] == t][:K]
            for x in res:
                buf += struct.pack("<H", index[x["patch_id"]])
                buf += struct.pack("<7H", *[NULL if x["scores"][d] is None else int(round(x["scores"][d] * 10000))
                                            for d in DIMS])
            buf += struct.pack("<8H", *([NULL] * 8)) * (K - len(res))
        return i, bytes(buf)

    t0 = time.time()
    blocks = [None] * len(meta)
    with cf.ThreadPoolExecutor(4) as ex:
        for n, (i, buf) in enumerate(ex.map(run, range(len(meta))), 1):
            blocks[i] = buf
            if n % 2000 == 0:
                print(f"  {n}/{len(meta)}  {time.time() - t0:.0f}s", flush=True)
    for b in BODIES:
        rows = [blocks[i] for i in range(len(meta)) if meta.body.iat[i] == b]
        write_chunks(b, rows)
    sizes = {p.name: round(p.stat().st_size / 1e6, 2) for p in sorted(OUT.iterdir())}
    print("->", OUT, sizes, f"total {sum(sizes.values()):.2f} MB", f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
