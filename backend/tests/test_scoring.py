import json
import math

import numpy as np
import pandas as pd
import pytest

from app.services.scoring import (
    PROFILES,
    OpsStats,
    PatchRecord,
    effective_weights,
    load_operations,
    not_comparable_for,
    operations_score,
    score_pair,
    thermal_score,
)
from app.services.thermal import ThermalStats

QUERY = PatchRecord("moon-60-002461", "moon", -89.5, 130.0, "Shackleton")
RESULT = PatchRecord("earth-60-000123", "earth", 31.77, -113.5, "Sonora, Mexico")
OPS = OpsStats(slope_mean=5.0, frac_under_8=0.6, frac_under_15=0.75, roughness_m=10.0)
THERMAL = ThermalStats(tmax_k=300.0, tmin_k=200.0, trange_k=100.0)


def _scores(**overrides):
    values = {"terrain": 0.9, "materials": None, "thermal": 0.5, "operations": 0.8}
    values.update(overrides)
    return values


def test_terrain_is_used_directly():
    result = score_pair(
        QUERY,
        RESULT,
        terrain=0.91234,
        profile="rover",
        scale_m=60,
        query_ops=OPS,
        result_ops=OPS,
        query_thermal=THERMAL,
        result_thermal=THERMAL,
    )
    assert result["scores"]["terrain"] == 0.9123


def test_materials_is_always_null():
    result = score_pair(
        QUERY,
        RESULT,
        terrain=0.5,
        profile="isru",
        scale_m=60,
        query_ops=OPS,
        result_ops=OPS,
    )
    assert result["scores"]["materials"] is None


def test_operations_identical_is_one():
    assert operations_score(OPS, OPS, scale_m=60) == pytest.approx(1.0)


def test_operations_known_deltas():
    other = OpsStats(slope_mean=15.0, frac_under_8=0.4, frac_under_15=0.55, roughness_m=70.0)
    expected = 0.20 * math.exp(-10 / 10) + 0.25 * math.exp(-0.2 / 0.2)
    expected += 0.30 * math.exp(-0.2 / 0.2) + 0.25 * math.exp(-60 / 60)
    assert operations_score(OPS, other, scale_m=60) == pytest.approx(expected)


def test_operations_none_when_data_missing():
    partial = OpsStats(slope_mean=float("nan"), frac_under_8=0.5, frac_under_15=0.7, roughness_m=5.0)
    assert operations_score(partial, OPS, scale_m=60) is None
    assert operations_score(None, OPS, scale_m=60) is None
    assert operations_score(OPS, OPS, scale_m=0) is None


def test_thermal_known_deltas():
    other = ThermalStats(tmax_k=350.0, tmin_k=250.0, trange_k=100.0)
    expected = (math.exp(-1) + math.exp(-1) + 1.0) / 3.0
    assert thermal_score(THERMAL, other) == pytest.approx(expected)


def test_thermal_derives_range_and_handles_missing():
    no_range = ThermalStats(tmax_k=300.0, tmin_k=200.0, trange_k=None)
    other = ThermalStats(tmax_k=350.0, tmin_k=250.0, trange_k=None)
    assert thermal_score(no_range, other) == pytest.approx((math.exp(-1) * 2 + 1) / 3)
    assert thermal_score(None, other) is None
    missing = ThermalStats(tmax_k=None, tmin_k=200.0, trange_k=100.0)
    assert thermal_score(missing, other) is None


@pytest.mark.parametrize("profile", list(PROFILES))
def test_weights_redistribute_when_materials_is_null(profile):
    weights = effective_weights(_scores(materials=None), profile)
    assert "materials" not in weights
    assert sum(weights.values()) == pytest.approx(1.0)
    assert all(weight > 0 for weight in weights.values())


@pytest.mark.parametrize("profile", list(PROFILES))
def test_weights_redistribute_when_materials_and_thermal_are_null(profile):
    weights = effective_weights(_scores(materials=None, thermal=None), profile)
    assert "materials" not in weights
    assert "thermal" not in weights
    assert sum(weights.values()) == pytest.approx(1.0)


def test_astrobiology_excludes_zero_weight_operations():
    weights = effective_weights(_scores(materials=None), "astrobiology")
    assert "operations" not in weights
    assert sum(weights.values()) == pytest.approx(1.0)


def test_score_pair_rover_with_redistribution():
    result = score_pair(
        QUERY,
        RESULT,
        terrain=0.91,
        profile="rover",
        scale_m=60,
        query_ops=OPS,
        result_ops=OPS,
        query_thermal=THERMAL,
        result_thermal=THERMAL,
    )
    assert result["scores"] == {
        "terrain": 0.91,
        "materials": None,
        "thermal": 1.0,
        "operations": 1.0,
    }
    assert result["score"] == pytest.approx(0.955, abs=1e-4)
    assert result["not_comparable"] == ["gravity", "vacuum", "radiation"]


def test_score_pair_without_thermal_redistributes():
    result = score_pair(
        QUERY,
        RESULT,
        terrain=0.91,
        profile="rover",
        scale_m=60,
        query_ops=OPS,
        result_ops=OPS,
    )
    assert result["scores"]["thermal"] is None
    expected = (0.91 * 0.45 + 1.0 * 0.40) / 0.85
    assert result["score"] == pytest.approx(expected, abs=1e-4)


def test_unknown_profile_and_invalid_terrain():
    with pytest.raises(ValueError):
        score_pair(QUERY, RESULT, terrain=0.5, profile="unknown", scale_m=60)
    with pytest.raises(ValueError):
        score_pair(QUERY, RESULT, terrain=float("nan"), profile="rover", scale_m=60)


def test_not_comparable_by_body():
    assert not_comparable_for("moon", "earth") == ["gravity", "vacuum", "radiation"]
    assert not_comparable_for("mars", "earth") == ["gravity", "atmosphere", "radiation"]
    assert not_comparable_for("mars", "moon") == [
        "gravity",
        "vacuum",
        "atmosphere",
        "radiation",
    ]
    assert not_comparable_for("earth", "mars") == ["gravity", "atmosphere", "radiation"]


def _write_operations_artifacts(root, scale=60):
    names = [
        "log_relief",
        "log_elev_std",
        "hypsometric_integral",
        "elev_skew",
        "elev_kurt",
        "slope_mean",
        "slope_std",
        "slope_p90",
        "slope_frac_0_2",
        "slope_frac_2_5",
        "slope_frac_5_8",
        "slope_frac_8_15",
        "slope_frac_15_25",
        "slope_frac_25_35",
        "slope_frac_35_90",
        "log_rough_mean",
        "log_rough_p90",
        "curv_absmean",
        "curv_std",
        "curv_convex_frac",
    ]
    features = np.zeros((2, len(names)), dtype=np.float32)
    features[0, names.index("slope_mean")] = 5.0
    features[0, names.index("slope_frac_0_2")] = 0.1
    features[0, names.index("slope_frac_2_5")] = 0.2
    features[0, names.index("slope_frac_5_8")] = 0.3
    features[0, names.index("slope_frac_8_15")] = 0.15
    features[0, names.index("log_rough_mean")] = math.log1p(10.0)
    np.save(root / f"baseline_feat_{scale}.npy", features)
    (root / f"baseline_feat_{scale}.json").write_text(
        json.dumps(
            {
                "names": names,
                "mean": [0.0] * len(names),
                "std": [1.0] * len(names),
                "slope_bins": [0, 2, 5, 8, 15, 25, 35, 90],
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "patch_id": ["earth-60-000001", "earth-60-000002"],
            "body": ["earth", "earth"],
        }
    ).to_parquet(root / f"meta_{scale}.parquet", index=False)


def test_load_operations_restores_raw_values(artifacts_dir):
    _write_operations_artifacts(artifacts_dir)
    table = load_operations(60, artifacts_dir)
    stats = table["earth-60-000001"]
    assert stats.slope_mean == pytest.approx(5.0)
    assert stats.frac_under_8 == pytest.approx(0.6)
    assert stats.frac_under_15 == pytest.approx(0.75)
    assert stats.roughness_m == pytest.approx(10.0)


def test_load_operations_returns_empty_without_artifacts(artifacts_dir):
    assert load_operations(60, artifacts_dir) == {}
