import json

from app.core.config import get_contracts_dir
from app.services.scoring import (
    ATTRIBUTE_KEYS,
    DIMENSIONS,
    OpsStats,
    PatchRecord,
    score_pair,
)


def _load(name):
    return json.loads((get_contracts_dir() / name).read_text(encoding="utf-8"))


def test_similar_request_example():
    request = _load("similar_request.json")
    assert set(request) == {
        "body",
        "lat",
        "lon",
        "target_bodies",
        "scale_m",
        "profile",
        "k",
        "scale_mode",
    }
    assert request["scale_m"] in {60, 1000}
    assert request["profile"] in {
        "general",
        "rover",
        "isru",
        "habitat",
        "eva",
        "astrobiology",
    }


def test_similar_response_example_shape():
    response = _load("similar_response.json")
    assert set(response) == {"query", "results", "warnings", "_note"}
    assert set(response["query"]) == {
        "body",
        "lat",
        "lon",
        "profile",
        "target_bodies",
        "method",
        "patches",
        "scale_m",
        "attributes",
        "scale_mode",
        "land_cover",
    }
    assert set(response["query"]["attributes"]) == set(ATTRIBUTE_KEYS)
    for result in response["results"]:
        assert set(result) == {
            "patch_id",
            "body",
            "lat",
            "lon",
            "region",
            "scale_m",
            "score",
            "scores",
            "not_comparable",
            "no_data",
            "attributes",
            "land_cover",
            "window_km",
        }
        assert set(result["scores"]) == set(DIMENSIONS)
        assert 0.0 <= result["score"] <= 1.0
        for dimension, value in result["scores"].items():
            if value is not None:
                assert 0.0 <= value <= 1.0, dimension
        assert set(result["attributes"]) == set(ATTRIBUTE_KEYS)


def test_galaxy_example_shape():
    galaxy = _load("galaxy.example.json")
    assert isinstance(galaxy, list) and galaxy
    for item in galaxy:
        assert set(item) == {"id", "body", "x", "y", "z"}
        assert item["body"] in {"earth", "moon", "mars"}


def test_heights_example_shape():
    heights = _load("heights.example.json")
    assert set(heights) == {
        "patch_id",
        "width",
        "height",
        "dtype",
        "endianness",
        "min",
        "max",
        "m_per_px",
    }
    assert heights["dtype"] == "float32"
    assert heights["endianness"] == "little"
    assert heights["width"] == 128 and heights["height"] == 128


def test_score_pair_matches_contract_result_keys():
    example = _load("similar_response.json")["results"][0]
    query = PatchRecord("moon-1000-002461", "moon", -89.5, 130.0, "Shackleton")
    result = PatchRecord(
        example["patch_id"],
        example["body"],
        example["lat"],
        example["lon"],
        example["region"],
    )
    ops = OpsStats(
        slope_mean=5.0,
        frac_under_8=0.6,
        frac_under_15=0.75,
        roughness_m=10.0,
    )
    produced = score_pair(
        query,
        result,
        terrain=example["scores"]["terrain"],
        profile="general",
        scale_m=example["scale_m"],
        query_ops=ops,
        result_ops=ops,
    )
    # score_pair produces the core result keys; window_km and land_cover are
    # added later by the search layer when enriching results.
    enrichment_keys = {"window_km", "land_cover"}
    assert set(example) - enrichment_keys <= set(produced)
    assert set(produced) - set(example) == {"weights_used"}
    assert set(produced["scores"]) == set(example["scores"])
    assert produced["not_comparable"] == example["not_comparable"]
    assert produced["no_data"] == example["no_data"]
    assert produced["attributes"] == example["attributes"]
    assert produced["scale_m"] == example["scale_m"]
