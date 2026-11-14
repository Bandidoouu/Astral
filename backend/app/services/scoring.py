"""Puntajes por dimensión y por perfil de misión (docs/contratos.md §3-4).

`terrain` llega ya calculado por FAISS (coseno de embeddings): aquí no se
recalcula. `operations` compara estadísticas crudas de relieve entre los dos
parches, `thermal` compara temperaturas (Diviner vs MODIS) y `materials` queda
explícitamente en ``None`` hasta que ML decida la fuente (ml/CLAUDE.md §6.3).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

from app.core.config import get_artifacts_dir
from app.services.thermal import ThermalStats

PROFILES: dict[str, dict[str, float]] = {
    "rover": {"terrain": 0.45, "materials": 0.10, "thermal": 0.05, "operations": 0.40},
    "isru": {"terrain": 0.20, "materials": 0.50, "thermal": 0.20, "operations": 0.10},
    "habitat": {"terrain": 0.25, "materials": 0.20, "thermal": 0.25, "operations": 0.30},
    "eva": {"terrain": 0.40, "materials": 0.40, "thermal": 0.05, "operations": 0.15},
    "astrobiology": {"terrain": 0.25, "materials": 0.50, "thermal": 0.25, "operations": 0.00},
}

DIMENSIONS = ("terrain", "materials", "thermal", "operations")

THERMAL_SCALE_K = 50.0
SLOPE_SCALE_DEG = 10.0
FRACTION_SCALE = 0.20
OPERATIONS_WEIGHTS = {
    "slope_mean": 0.20,
    "under_8": 0.25,
    "under_15": 0.30,
    "roughness": 0.25,
}

_OPS_SOURCE_COLUMNS = (
    "slope_mean",
    "slope_frac_0_2",
    "slope_frac_2_5",
    "slope_frac_5_8",
    "slope_frac_8_15",
)


@dataclass(frozen=True)
class PatchRecord:
    patch_id: str
    body: str
    lat: float
    lon: float
    region: str


@dataclass(frozen=True)
class OpsStats:
    slope_mean: float
    frac_under_8: float
    frac_under_15: float
    roughness_m: float


def _finite(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def not_comparable_for(*bodies: str) -> list[str]:
    """Límites físicos que la Tierra no puede replicar, según los cuerpos del par."""
    involved = set(bodies)
    result = ["gravity"]
    if "moon" in involved:
        result.append("vacuum")
    if "mars" in involved:
        result.append("atmosphere")
    result.append("radiation")
    return result


def effective_weights(
    scores: Mapping[str, float | None], profile: str
) -> dict[str, float]:
    """Pesos del perfil, quitando dimensiones nulas y renormalizando a 1.0."""
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile}")
    available = {
        dimension: weight
        for dimension, weight in PROFILES[profile].items()
        if weight > 0 and scores.get(dimension) is not None
    }
    total = sum(available.values())
    if total <= 0:
        return {}
    return {dimension: weight / total for dimension, weight in available.items()}


def operations_score(
    query: OpsStats | None, result: OpsStats | None, scale_m: float
) -> float | None:
    """Similitud 0-1 de las condiciones de operación entre los dos parches."""
    if query is None or result is None:
        return None
    scale = _finite(scale_m)
    if scale is None or scale <= 0:
        return None
    values = (
        query.slope_mean,
        query.frac_under_8,
        query.frac_under_15,
        query.roughness_m,
        result.slope_mean,
        result.frac_under_8,
        result.frac_under_15,
        result.roughness_m,
    )
    if any(_finite(value) is None for value in values):
        return None

    components = {
        "slope_mean": math.exp(-abs(query.slope_mean - result.slope_mean) / SLOPE_SCALE_DEG),
        "under_8": math.exp(
            -abs(query.frac_under_8 - result.frac_under_8) / FRACTION_SCALE
        ),
        "under_15": math.exp(
            -abs(query.frac_under_15 - result.frac_under_15) / FRACTION_SCALE
        ),
        "roughness": math.exp(
            -abs(query.roughness_m - result.roughness_m) / scale
        ),
    }
    return _clip01(
        sum(OPERATIONS_WEIGHTS[name] * value for name, value in components.items())
    )


def _trange(stats: ThermalStats) -> float | None:
    if stats.trange_k is not None:
        return _finite(stats.trange_k)
    if stats.tmax_k is None or stats.tmin_k is None:
        return None
    tmax, tmin = _finite(stats.tmax_k), _finite(stats.tmin_k)
    if tmax is None or tmin is None:
        return None
    return tmax - tmin


def thermal_score(
    query: ThermalStats | None, result: ThermalStats | None
) -> float | None:
    """Similitud térmica: media de exp(-|ΔT| / 50 K) en máxima, mínima y rango."""
    if query is None or result is None:
        return None
    q_tmax, q_tmin = _finite(query.tmax_k), _finite(query.tmin_k)
    r_tmax, r_tmin = _finite(result.tmax_k), _finite(result.tmin_k)
    q_trange, r_trange = _trange(query), _trange(result)
    if None in (q_tmax, q_tmin, r_tmax, r_tmin, q_trange, r_trange):
        return None
    deltas = (abs(q_tmax - r_tmax), abs(q_tmin - r_tmin), abs(q_trange - r_trange))
    return _clip01(
        sum(math.exp(-delta / THERMAL_SCALE_K) for delta in deltas) / len(deltas)
    )


def score_pair(
    query: PatchRecord,
    result: PatchRecord,
    *,
    terrain: float,
    profile: str,
    scale_m: float,
    query_ops: OpsStats | None = None,
    result_ops: OpsStats | None = None,
    query_thermal: ThermalStats | None = None,
    result_thermal: ThermalStats | None = None,
) -> dict:
    """Devuelve el objeto ``results[]`` del contrato para un par query/result."""
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile}")
    terrain_value = _finite(terrain)
    if terrain_value is None:
        raise ValueError("terrain similarity must be a finite number")

    scores: dict[str, float | None] = {
        "terrain": round(_clip01(terrain_value), 4),
        "materials": None,
        "thermal": None,
        "operations": None,
    }
    thermal_value = thermal_score(query_thermal, result_thermal)
    operations_value = operations_score(query_ops, result_ops, scale_m)
    if thermal_value is not None:
        scores["thermal"] = round(_clip01(thermal_value), 4)
    if operations_value is not None:
        scores["operations"] = round(_clip01(operations_value), 4)

    weights = effective_weights(scores, profile)
    total = (
        sum(scores[dimension] * weight for dimension, weight in weights.items())
        if weights
        else 0.0
    )
    return {
        "patch_id": result.patch_id,
        "body": result.body,
        "lat": round(float(result.lat), 4),
        "lon": round(float(result.lon), 4),
        "region": result.region,
        "score": round(_clip01(total), 4),
        "scores": scores,
        "not_comparable": not_comparable_for(query.body, result.body),
    }


def _ops_from_raw(slope_mean: float, under_8: float, under_15: float, roughness_m: float) -> OpsStats | None:
    values = (slope_mean, under_8, under_15, roughness_m)
    if any(_finite(value) is None for value in values):
        return None
    return OpsStats(
        slope_mean=float(slope_mean),
        frac_under_8=_clip01(under_8),
        frac_under_15=_clip01(under_15),
        roughness_m=max(0.0, float(roughness_m)),
    )


@lru_cache(maxsize=8)
def _load_operations_cached(artifacts_dir: str, scale: int) -> dict[str, OpsStats]:
    root = Path(artifacts_dir)
    meta_path = root / f"meta_{scale}.parquet"
    feat_path = root / f"baseline_feat_{scale}.npy"
    names_path = root / f"baseline_feat_{scale}.json"
    if not (meta_path.is_file() and feat_path.is_file() and names_path.is_file()):
        return {}
    try:
        meta = pd.read_parquet(meta_path, columns=["patch_id"])
        features = np.load(feat_path)
        spec = json.loads(names_path.read_text(encoding="utf-8"))
        names = list(spec["names"])
        mean = np.asarray(spec["mean"], dtype=np.float64)
        std = np.asarray(spec["std"], dtype=np.float64)
    except Exception:
        return {}
    if len(meta) != len(features) or features.ndim != 2:
        return {}
    if features.shape[1] != len(names) or mean.shape != (len(names),) or std.shape != (len(names),):
        return {}

    try:
        index = {name: position for position, name in enumerate(names)}
        slope_mean_idx = index["slope_mean"]
        under8_idx = [index[name] for name in ("slope_frac_0_2", "slope_frac_2_5", "slope_frac_5_8")]
        under15_idx = [index["slope_frac_8_15"]]
    except KeyError:
        return {}
    if "log_rough_mean" in index:
        rough_idx = index["log_rough_mean"]
        rough_is_log = True
    elif "rough_mean" in index:
        rough_idx = index["rough_mean"]
        rough_is_log = False
    else:
        return {}

    raw = features.astype(np.float64) * std + mean
    table: dict[str, OpsStats] = {}
    for row, patch_id in enumerate(meta.patch_id.to_numpy()):
        if not isinstance(patch_id, str):
            continue
        under_8 = float(sum(raw[row, position] for position in under8_idx))
        under_15 = under_8 + float(raw[row, under15_idx[0]])
        roughness = raw[row, rough_idx]
        roughness_m = float(np.expm1(roughness)) if rough_is_log else float(roughness)
        stats = _ops_from_raw(
            slope_mean=float(raw[row, slope_mean_idx]),
            under_8=under_8,
            under_15=under_15,
            roughness_m=roughness_m,
        )
        if stats is not None:
            table[patch_id] = stats
    return table


def load_operations(
    scale: int, artifacts_dir: Path | None = None
) -> dict[str, OpsStats]:
    """Carga las estadísticas de operación crudas desde los artefactos de ML."""
    root = Path(artifacts_dir) if artifacts_dir is not None else get_artifacts_dir()
    return dict(_load_operations_cached(str(root), int(scale)))
