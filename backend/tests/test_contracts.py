import json

from app.core.config import get_contracts_dir
from app.services.scoring import PatchRecord, score_pair


def _load(name):
    return json.loads((get_contracts_dir() / name).read_text(encoding="utf-8"))


def test_similar_request_example():
    request = _load("similar_request.json")
    assert set(request) == {"body", "lat", "lon", "scale_m", "profile", "k"}


def test_similar_response_example_shape():
    response = _load("similar_response.json")
    assert set(response) == {"query", "results", "_note"}
    assert set(response["query"]) == {"body", "lat", "lon", "scale_m", "profile", "patch_id"}
    for result in response["results"]:
        assert set(result) == {
            "patch_id",
            "body",
            "lat",
            "lon",
            "region",
            "score",
            "scores",
            "not_comparable",
        }
        assert set(result["scores"]) == {"terrain", "materials", "thermal", "operations"}
        assert 0.0 <= result["score"] <= 1.0
        for dimension, value in result["scores"].items():
            if value is not None:
                assert 0.0 <= value <= 1.0, dimension


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
    query = PatchRecord("moon-60-002461", "moon", -89.5, 130.0, "Shackleton")
    result = PatchRecord(
        example["patch_id"],
        example["body"],
        example["lat"],
        example["lon"],
        example["region"],
    )
    produced = score_pair(query, result, terrain=example["scores"]["terrain"], profile="rover", scale_m=60)
    assert set(produced) == set(example)
    assert set(produced["scores"]) == set(example["scores"])
    assert produced["not_comparable"] == example["not_comparable"]
