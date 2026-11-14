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

REQUIRED_COLUMNS = ("patch_id", "body", "lat", "lon", "region")


@dataclass(frozen=True)
class ScaleArtifacts:
    scale: int
    emb: np.ndarray
    meta: pd.DataFrame
    index: object | None


def validate(scale: int, emb: np.ndarray, meta: pd.DataFrame, index) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in meta.columns]
    if missing:
        raise ValueError(f"meta_{scale}.parquet: faltan columnas {missing}")
    if emb.ndim != 2 or emb.shape[1] != EMB_DIM:
        raise ValueError(f"emb_{scale}.npy debe ser (N, {EMB_DIM}); llegó {emb.shape}")
    if len(meta) != emb.shape[0]:
        raise ValueError(f"Escala {scale}: meta tiene {len(meta)} filas y emb {emb.shape[0]}")
    if index is not None and index.ntotal != emb.shape[0]:
        raise ValueError(f"Escala {scale}: el índice tiene {index.ntotal} vectores y emb {emb.shape[0]}")
    norms = np.linalg.norm(emb, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-3):
        raise ValueError(f"emb_{scale}.npy no tiene norma 1")


def load_scale(scale: int) -> ScaleArtifacts:
    paths = artifact_paths(scale)
    emb = np.load(paths["emb"]).astype(np.float32)
    meta = pd.read_parquet(paths["meta"]).reset_index(drop=True)
    index = None
    if faiss is not None and paths["index"].exists():
        index = faiss.read_index(str(paths["index"]))
    validate(scale, emb, meta, index)
    return ScaleArtifacts(scale=scale, emb=emb, meta=meta, index=index)


@lru_cache(maxsize=1)
def get_artifacts() -> dict[int, ScaleArtifacts]:
    loaded = {s: load_scale(s) for s in SCALES if artifact_paths(s)["emb"].exists()}
    if not loaded:
        raise RuntimeError(f"No hay artefactos en {ARTIFACTS_DIR}")
    return loaded