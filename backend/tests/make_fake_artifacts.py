"""Genera artefactos FALSOS con el formato de docs/contratos.md (secciones 1 y 2)."""
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import faiss
except ImportError:
    faiss = None

OUT = Path("../data/artifacts_fake")
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(0)

for scale, other in ((60, "moon"), (500, "mars")):
    n_earth, n_other = 300, 200
    n = n_earth + n_other
    meta = pd.DataFrame({
        "patch_id": [f"earth-{scale}-{i:06d}" for i in range(n_earth)]
                  + [f"{other}-{scale}-{i:06d}" for i in range(n_other)],
        "body": ["earth"] * n_earth + [other] * n_other,
        "scale_m": scale,
        "lat": np.r_[rng.uniform(14.5, 32.7, n_earth), rng.uniform(-90, -80, n_other)],
        "lon": np.r_[rng.uniform(-117, -86.7, n_earth), rng.uniform(-180, 180, n_other)],
        "crs": "fake", "x": 0.0, "y": 0.0,
        "region": ["Mexico (fake)"] * n_earth + [f"{other} (fake)"] * n_other,
        "holdout": False,
        "elev_mean_m": 0.0, "elev_min_m": 0.0, "elev_max_m": 0.0,
    })
    emb = rng.normal(size=(n, 128)).astype("float32")
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)

    np.save(OUT / f"emb_{scale}.npy", emb)
    meta.to_parquet(OUT / f"meta_{scale}.parquet")
    if faiss is not None:
        index = faiss.IndexFlatIP(128)
        index.add(emb)
        faiss.write_index(index, str(OUT / f"index_{scale}.faiss"))
    print(f"escala {scale}: {n} parches en {OUT}")