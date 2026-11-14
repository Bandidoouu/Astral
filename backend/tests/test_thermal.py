import math

import pandas as pd

from app.services.thermal import load_thermal, thermal_for_patch


def test_missing_artifact_returns_empty(artifacts_dir):
    assert load_thermal(60, artifacts_dir) == {}


def test_loads_thermal_columns(artifacts_dir):
    pd.DataFrame(
        {
            "patch_id": ["earth-60-000001", "moon-60-000002"],
            "tmax_k": [310.0, 220.0],
            "tmin_k": [280.0, 120.0],
            "trange_k": [30.0, 100.0],
        }
    ).to_parquet(artifacts_dir / "features_60.parquet", index=False)

    table = load_thermal(60, artifacts_dir)
    stats = table["earth-60-000001"]
    assert stats.tmax_k == 310.0
    assert stats.tmin_k == 280.0
    assert stats.trange_k == 30.0
    assert thermal_for_patch("moon-60-000002", table).tmin_k == 120.0
    assert thermal_for_patch("mars-60-999999", table) is None


def test_missing_columns_returns_empty(artifacts_dir):
    pd.DataFrame({"patch_id": ["earth-60-000001"]}).to_parquet(
        artifacts_dir / "features_60.parquet", index=False
    )
    assert load_thermal(60, artifacts_dir) == {}


def test_nan_temperature_is_not_data(artifacts_dir):
    pd.DataFrame(
        {
            "patch_id": ["earth-60-000001", "earth-60-000002"],
            "tmax_k": [float("nan"), 300.0],
            "tmin_k": [280.0, 250.0],
        }
    ).to_parquet(artifacts_dir / "features_60.parquet", index=False)
    table = load_thermal(60, artifacts_dir)
    assert "earth-60-000001" not in table
    assert "earth-60-000002" in table
    assert table["earth-60-000002"].trange_k is None
    assert math.isfinite(table["earth-60-000002"].tmax_k)
