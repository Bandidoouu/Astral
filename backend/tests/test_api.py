import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import CONTRACTS_DIR

client = TestClient(app)

def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"

def test_similar_matches_contract():
    req_file = CONTRACTS_DIR / "similar_request.json"
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
            "k": 10
        }
    
    res = client.post("/api/similar", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "query" in data
    assert "results" in data
