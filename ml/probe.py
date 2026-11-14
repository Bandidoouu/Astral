#!/usr/bin/env python
"""¿Los embeddings delatan el planeta? (prueba de invariancia para la ablación)

1. Clasificador lineal (regresión logística) sobre embeddings CONGELADOS, con
   clases balanceadas y validación cruzada de 5 particiones. Azar = 50%.
   Cerca de 50% -> los embeddings no distinguen Luna de Tierra.
2. Mezcla de vecinos: entre los 10 vecinos más cercanos de cada parche, fracción
   que es del OTRO cuerpo. Con clases balanceadas, mezcla perfecta = 50%.

  python -m ml.probe --tag ""      # modelo con discriminador
  python -m ml.probe --tag _abl    # ablación
"""
import argparse
import json
import os
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path(__file__).resolve().parents[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=60)
    ap.add_argument("--tag", default="")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    art = ROOT / "data/artifacts"
    emb = np.load(art / f"emb_{a.scale}{a.tag}.npy")
    meta = pd.read_parquet(art / f"meta_{a.scale}{a.tag}.parquet")
    rng = np.random.default_rng(a.seed)
    bodies = sorted(meta.body.unique())
    n = meta.body.value_counts().min()
    idx = np.concatenate([rng.choice(np.flatnonzero(meta.body == b), n, replace=False)
                          for b in bodies])
    X, y = emb[idx], meta.body.to_numpy()[idx]

    clf = LogisticRegression(max_iter=2000, C=1.0)
    cv = StratifiedKFold(5, shuffle=True, random_state=a.seed)
    acc = cross_val_score(clf, X, y, cv=cv, scoring="accuracy")

    index = faiss.IndexFlatIP(X.shape[1])
    index.add(X.astype(np.float32))
    _, nn = index.search(X.astype(np.float32), a.k + 1)
    other = (y[nn[:, 1:]] != y[:, None]).mean()

    res = dict(tag=a.tag or "main", n_per_body=int(n), bodies=bodies,
               linear_probe_acc=float(acc.mean()), linear_probe_std=float(acc.std()),
               chance=1 / len(bodies), knn_other_body_frac=float(other), k=a.k)
    (art / f"probe_{a.scale}{a.tag}.json").write_text(json.dumps(res, indent=2))
    print(f"[{res['tag']}] clasificador lineal: {100 * acc.mean():.1f}% ± {100 * acc.std():.1f} "
          f"(azar {100 / len(bodies):.0f}%) | vecinos del otro cuerpo (k={a.k}): "
          f"{100 * other:.1f}% (mezcla perfecta 50%) | {n} por cuerpo")


if __name__ == "__main__":
    main()
