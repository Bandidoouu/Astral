"""Datos auxiliares por parche (Diviner en la Luna, MODIS en la Tierra).

El backend no reprocesa los productos crudos: consume las columnas que ML calcula
en ``features_{scale}.parquet``. Si falta el artefacto, una columna o el parche,
el valor correspondiente es ``None`` ("sin dato"): nunca se inventan valores.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.core.config import get_artifacts_dir

FEATURE_COLUMNS = (
    "tmax_k",
    "tmin_k",
    "trange_k",
    "tavg_k",
    "albedo",
    "ice_distance_km",
    "ice_frac",
    "soil_raw",
    "soil_pct",
    "precip_mm",
)
@dataclass(frozen=True)
class ThermalStats:
    tmax_k: float | None
    tmin_k: float | None
    trange_k: float | None


@dataclass(frozen=True)
class PatchAttributes:
    tmax_k: float | None = None
    tmin_k: float | None = None
    trange_k: float | None = None
    tavg_k: float | None = None
    albedo: float | None = None
    ice_distance_km: float | None = None
    ice_frac: float | None = None
    soil_raw: float | None = None
    soil_pct: float | None = None
    precip_mm: float | None = None

    def thermal(self) -> ThermalStats | None:
        if self.tmax_k is None or self.tmin_k is None:
            return None
        return ThermalStats(
            tmax_k=self.tmax_k,
            tmin_k=self.tmin_k,
            trange_k=self.trange_k,
        )


def _finite(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


@lru_cache(maxsize=8)
def _load_features_file(path_str: str) -> dict[str, PatchAttributes]:
    path = Path(path_str)
    if not path.is_file():
        return {}
    try:
        frame = pd.read_parquet(path)
    except Exception:
        return {}
    if "patch_id" not in frame.columns:
        return {}

    columns = [column for column in FEATURE_COLUMNS if column in frame.columns]
    if not columns:
        columns = []
    table: dict[str, PatchAttributes] = {}
    for row in frame[["patch_id", *columns]].to_dict("records"):
        patch_id = row.get("patch_id")
        if not isinstance(patch_id, str):
            continue
        table[patch_id] = PatchAttributes(
            **{column: _finite(row.get(column)) for column in FEATURE_COLUMNS}
        )
    return table


def load_attributes(
    scale: int, artifacts_dir: Path | None = None
) -> dict[str, PatchAttributes]:
    """Carga todas las características auxiliares de una escala."""
    root = Path(artifacts_dir) if artifacts_dir is not None else get_artifacts_dir()
    path = root / f"features_{scale}.parquet"
    if not path.is_file():
        return {}
    return dict(_load_features_file(str(path)))


def load_thermal(
    scale: int, artifacts_dir: Path | None = None
) -> dict[str, ThermalStats]:
    """Subconjunto térmico: solo parches con temperatura máxima y mínima."""
    table: dict[str, ThermalStats] = {}
    for patch_id, attributes in load_attributes(scale, artifacts_dir).items():
        thermal = attributes.thermal()
        if thermal is not None:
            table[patch_id] = thermal
    return table


def thermal_for_patch(
    patch_id: str, table: dict[str, ThermalStats] | None
) -> ThermalStats | None:
    return (table or {}).get(patch_id)
