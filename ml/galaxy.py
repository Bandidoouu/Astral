#!/usr/bin/env python
"""Galaxia de terreno: UMAP 3D de los embeddings del índice (contrato `galaxy.json`).

Salida: data/artifacts/galaxy_{scale}.json = lista de {id, body, x, y, z} (centrada y
escalada a ~±5). 1 km: todos los parches (Tierra, Luna, Marte). 60 m: toda la Luna +
una submuestra al azar de la Tierra hasta ~30 mil puntos. UMAP con distancia coseno,
semilla fija. Mismos embeddings que la búsqueda (no recalcula nada de la red).

  python -m ml.galaxy --scale 1000
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))
ART = ROOT / "data/artifacts"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, nargs="+", default=[1000, 60])
    ap.add_argument("--max-points", type=int, default=30000)
    a = ap.parse_args()
    import umap
    for s in a.scale:
        meta = pd.read_parquet(ART / f"meta_{s}.parquet")
        emb = np.load(ART / f"emb_{s}.npy")
        idx = np.arange(len(meta))
        if len(idx) > a.max_points:
            rng = np.random.default_rng(0)
            keep = []
            others = idx[meta.body.to_numpy() != "earth"]
            earth = idx[meta.body.to_numpy() == "earth"]
            keep = np.concatenate([others, rng.choice(earth, a.max_points - len(others), replace=False)])
            idx = np.sort(keep)
        xyz = umap.UMAP(n_components=3, n_neighbors=30, min_dist=0.1, metric="cosine",
                        random_state=0).fit_transform(emb[idx])
        xyz = xyz - xyz.mean(0)
        xyz = xyz / np.abs(xyz).max() * 5
        pts = [dict(id=pid, body=b, x=round(float(p[0]), 3), y=round(float(p[1]), 3), z=round(float(p[2]), 3))
               for pid, b, p in zip(meta.patch_id.to_numpy()[idx], meta.body.to_numpy()[idx], xyz)]
        out = ART / f"galaxy_{s}.json"
        out.write_text(json.dumps(pts, separators=(",", ":")))
        print(f"-> {out}: {len(pts):,} puntos {pd.Series([p['body'] for p in pts]).value_counts().to_dict()}, "
              f"{out.stat().st_size / 1e6:.1f} MB", flush=True)


if __name__ == "__main__":
    main()
