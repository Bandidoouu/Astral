import pandas as pd
import pytest

from app.services.thermal import (
    PatchAttributes,
    ThermalStats,
    load_attributes,
    load_thermal,
    thermal_for_patch,
)


def _write_features(root, scale=1000, frame=None):
    if frame is None:
        frame = pd.DataFrame(
            {
                "patch_id": ["moon-1000-000001", "moon-1000-000002", "mars-1000-000003"],
                "tmax_k": [300.0, float("nan"), 280.0],
                "tmin_k": [200.0, 210.0, 180.0],
                "trange_k": [100.0, float("nan"), 100.0],
                "tavg_k": [250.0, 240.0, 230.0],
                "albedo": [0.2, 0.25, 0.18],
                "ice_distance_km": [3.2, None, 7.5],
                "ice_frac": [0.1, 0.0, 0.05],
                "soil_raw": [0.5, 0.4, 0.6],
                "soil_pct": [0.7, 0.4, 0.9],
                "precip_mm": [100.0, 0.0, 0.0],
            }
        )
    frame.to_parquet(root / f"features_{scale}.parquet", index=False)


def test_load_attributes_reads_all_columns(artifacts_dir):
    _write_features(artifacts_dir)
    table = load_attributes(1000, artifacts_dir)
    assert set(table) == {"moon-1000-000001", "moon-1000-000002", "mars-1000-000003"}
    attrs = table["moon-1000-000001"]
    assert attrs == PatchAttributes(
        tmax_k=300.0,
        tmin_k=200.0,
        trange_k=100.0,
        tavg_k=250.0,
        albedo=0.2,
        ice_distance_km=3.2,
        ice_frac=0.1,
        soil_raw=0.5,
        soil_pct=0.7,
        precip_mm=100.0,
    )


def test_nan_becomes_none_and_thermal_skips_incomplete_rows(artifacts_dir):
    _write_features(artifacts_dir)
    attributes = load_attributes(1000, artifacts_dir)
    assert attributes["moon-1000-000002"].tmax_k is None
    assert attributes["moon-1000-000002"].trange_k is None
    assert attributes["moon-1000-000002"].tmin_k == 210.0

    table = load_thermal(1000, artifacts_dir)
    assert set(table) == {"moon-1000-000001", "mars-1000-000003"}
    assert table["moon-1000-000001"] == ThermalStats(300.0, 200.0, 100.0)


def test_thermal_table_derives_range_when_missing(artifacts_dir):
    _write_features(
        artifacts_dir,
        frame=pd.DataFrame(
            {
                "patch_id": ["earth-1000-000001"],
                "tmax_k": [310.0],
                "tmin_k": [290.0],
            }
        ),
    )
    table = load_thermal(1000, artifacts_dir)
    assert table["earth-1000-000001"].trange_k is None
    attributes = load_attributes(1000, artifacts_dir)["earth-1000-000001"]
    assert attributes.albedo is None
    assert attributes.thermal() == ThermalStats(310.0, 290.0, None)


def test_missing_file_returns_empty(artifacts_dir):
    assert load_attributes(1000, artifacts_dir) == {}
    assert load_thermal(1000, artifacts_dir) == {}


def test_missing_patch_id_column_returns_empty(artifacts_dir):
    _write_features(
        artifacts_dir,
        frame=pd.DataFrame({"tmax_k": [300.0], "tmin_k": [200.0]}),
    )
    assert load_attributes(1000, artifacts_dir) == {}


def test_partial_columns_keep_nulls(artifacts_dir):
    _write_features(
        artifacts_dir,
        frame=pd.DataFrame(
            {"patch_id": ["earth-1000-000009"], "albedo": [0.33]}
        ),
    )
    attributes = load_attributes(1000, artifacts_dir)["earth-1000-000009"]
    assert attributes.albedo == pytest.approx(0.33)
    assert attributes.tmax_k is None
    assert attributes.thermal() is None
    assert load_thermal(1000, artifacts_dir) == {}


def test_thermal_for_patch():
    table = {"moon-1": ThermalStats(300.0, 200.0, 100.0)}
    assert thermal_for_patch("moon-1", table) == ThermalStats(300.0, 200.0, 100.0)
    assert thermal_for_patch("moon-2", table) is None
    assert thermal_for_patch("moon-1", None) is None


def test_thermal_requires_both_extremes():
    assert PatchAttributes(tmax_k=300.0).thermal() is None
    assert PatchAttributes(tmin_k=200.0).thermal() is None
    assert PatchAttributes(tmax_k=300.0, tmin_k=200.0).thermal() == ThermalStats(
        300.0, 200.0, None
    )
