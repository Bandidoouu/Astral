#!/usr/bin/env python
"""Control de sanidad (NO es la evaluación principal): ¿los gemelos terrestres de
una consulta lunar tienen relieve y pendiente parecidos? Favorece a la fórmula base
por construcción (usa esas mismas variables); sirve para detectar modelos rotos.

  python -m ml.sanity_relief --tags "" _abl _v2test
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=60)
    ap.add_argument("--tags", nargs="*", default=[""])
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--k", type=int, default=5)
    a = ap.parse_args()
    art = ROOT / "data/artifacts"
    meta = pd.read_parquet(art / f"meta_{a.scale}.parquet")
    B = np.load(art / f"baseline_feat_{a.scale}.npy")
    names = json.loads((art / f"baseline_feat_{a.scale}.json").read_text())["names"]
    rel = np.log1p((meta.elev_max_m - meta.elev_min_m).to_numpy())
    slope = B[:, names.index("slope_mean")]
    E, M = np.flatnonzero(meta.body == "earth"), np.flatnonzero(meta.body == "moon")
    rng = np.random.default_rng(0)
    Q = rng.choice(M, a.n, replace=False)

    def nn(f, cos):
        out = []
        for q in Q:
            s = f[E] @ f[q] if cos else -((f[E] - f[q]) ** 2).sum(1)
            out.append(E[np.argpartition(-s, a.k)[:a.k]])
        return np.array(out)

    methods = {"fórmula base": nn(B, False)}
    for t in a.tags:
        p = art / f"emb_{a.scale}{t}.npy"
        if p.exists():
            methods[f"red{t or '_v1'}"] = nn(np.load(p), True)
    methods["al azar"] = rng.choice(E, (len(Q), a.k))
    print(f"{'método':<16}{'relieve difiere (x)':>22}{'|Δ pendiente| (z)':>20}")
    for name, N in methods.items():
        dr = np.abs(rel[N] - rel[Q][:, None]).mean()
        ds = np.abs(slope[N] - slope[Q][:, None]).mean()
        print(f"{name:<16}{np.exp(dr):>22.2f}{ds:>20.3f}")


if __name__ == "__main__":
    main()
