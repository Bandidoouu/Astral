"""Datos térmicos auxiliares por parche (Diviner para la Luna, MODIS para la Tierra).

El backend no reprocesa los productos crudos: consume las columnas que ML calcula
en ``features_{scale}.parquet`` (``tmax_k``, ``tmin_k``, ``trange_k``). Si el
artefacto no existe, no tiene las columnas o le falta el parche, el resultado es
``None`` ("sin dato"): nunca se inventan temperaturas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.core.config import get_artifacts_dir

REQUIRED_COLUMNS = ("tmax_k", "tmin_k")
OPTIONAL_COLUMNS = ("trange_k",)


@dataclass(frozen=True)
class ThermalStats:
    tmax_k: float | None
    tmin_k: float | None
    trange_k: float | None


def _finite(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


@lru_cache(maxsize=8)
def _load_thermal_file(path_str: str) -> dict[str, ThermalStats]:
    path = Path(path_str)
    if not path.is_file():
        return {}
    try:
        frame = pd.read_parquet(path)
    except Exception:
        return {}
    if "patch_id" not in frame.columns or any(c not in frame.columns for c in REQUIRED_COLUMNS):
        return {}

    columns = ["patch_id", *REQUIRED_COLUMNS]
    if "trange_k" in frame.columns:
        columns.append("trange_k")

    table: dict[str, ThermalStats] = {}
    for row in frame[columns].to_dict("records"):
        patch_id = row.get("patch_id")
        if not isinstance(patch_id, str):
            continue
        tmax = _finite(row.get("tmax_k"))
        tmin = _finite(row.get("tmin_k"))
        if tmax is None or tmin is None:
            continue
        trange = _finite(row.get("trange_k"))
        table[patch_id] = ThermalStats(tmax_k=tmax, tmin_k=tmin, trange_k=trange)
    return table


def load_thermal(scale: int, artifacts_dir: Path | None = None) -> dict[str, ThermalStats]:
    """Carga la tabla térmica de una escala; vacía si el artefacto no está disponible."""
    root = Path(artifacts_dir) if artifacts_dir is not None else get_artifacts_dir()
    path = root / f"features_{scale}.parquet"
    if not path.is_file():
        return {}
    return dict(_load_thermal_file(str(path)))


def thermal_for_patch(
    patch_id: str, table: dict[str, ThermalStats] | None
) -> ThermalStats | None:
    return (table or {}).get(patch_id)
