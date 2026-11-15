import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_contracts_dir, get_artifacts_dir
from app.services.scoring import ATTRIBUTE_KEYS, DIMENSIONS

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["encoder_version"] == 1
    assert "searcher_available" in data
    assert "scale_60_available" in data
    assert "scale_1000_available" in data


def test_similar_matches_contract():
    req_file = get_contracts_dir() / "similar_request.json"
    if req_file.exists():
        with open(req_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        payload = {
            "body": "moon",
            "lat": -89.5,
            "lon": 130.0,
            "target_bodies": ["earth", "mars"],
            "scale_m": 1000,
            "profile": "general",
            "method": "rrf",
            "k": 10,
        }

    res = client.post("/api/similar", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert "query" in data
    assert "results" in data
    assert "warnings" in data

    query = data["query"]
    assert query["body"] == payload["body"]
    assert query["lat"] == payload["lat"]
    assert query["lon"] == payload["lon"]
    assert query["scale_m"] == payload["scale_m"]
    assert "method" in query
    assert "attributes" in query
    assert "patches" in query

    for res_item in data["results"]:
        assert "patch_id" in res_item
        assert "body" in res_item
        assert "scores" in res_item
        assert "score" in res_item
        assert set(res_item["scores"].keys()) == set(DIMENSIONS)


def test_similar_validation_errors():
    # Invalid celestial body
    res = client.post(
        "/api/similar",
        json={"body": "jupiter", "lat": 0.0, "lon": 0.0, "scale_m": 1000},
    )
    assert res.status_code == 422

    # Invalid scale
    res = client.post(
        "/api/similar",
        json={"body": "earth", "lat": 0.0, "lon": 0.0, "scale_m": 500},
    )
    assert res.status_code == 422

    # Out of range latitude
    res = client.post(
        "/api/similar",
        json={"body": "earth", "lat": 95.0, "lon": 0.0, "scale_m": 1000},
    )
    assert res.status_code == 422

    # Invalid profile
    res = client.post(
        "/api/similar",
        json={"body": "earth", "lat": 0.0, "lon": 0.0, "profile": "unknown"},
    )
    assert res.status_code == 422


def test_suitability_metadata():
    res = client.get("/api/suitability/moon_south")
    assert res.status_code == 200
    data = res.json()
    assert "candidates" in data or "status" in data


def test_suitability_invalid_criterion():
    res = client.get("/api/suitability/moon_south/invalid_criterio")
    assert res.status_code == 400


def test_suitability_image_file(artifacts_dir):
    suit_dir = artifacts_dir / "suitability"
    suit_dir.mkdir(parents=True, exist_ok=True)
    fake_png = suit_dir / "moon_south_landing.png"
    fake_png.write_bytes(b"\x89PNG\r\n\x1a\nfakecontent")

    res = client.get("/api/suitability/moon_south/landing")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
