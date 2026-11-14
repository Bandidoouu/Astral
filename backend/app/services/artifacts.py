from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.core.config import ARTIFACTS_DIR, EMB_DIM, SCALES

try:
    import faiss
except ImportError:
    faiss = None


def artifact_paths(scale: int) -> dict[str, Path]:
    return {
        "emb": ARTIFACTS_DIR / f"emb_{scale}.npy",
        "index": ARTIFACTS_DIR / f"index_{scale}.faiss",
        "meta": ARTIFACTS_DIR / f"meta_{scale}.parquet",
    }