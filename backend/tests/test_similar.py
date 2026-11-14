import json

import pytest

from app.core.config import get_contracts_dir
from app.services import artifacts


@pytest.fixture
def mock_client(artifacts_dir):
    artifacts.get_searcher.cache_clear()
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
    artifacts.get_searcher.cache_clear()


def _example(name):
    return json.loads((get_contracts_dir() / name).read_text(encoding="utf-8"))


def test_similar_mock_matches_contract(mock_client):
    r = mock_client.post("/api/similar", json=_example("similar_request.json"))
    assert r.status_code == 200
    data, example = r.json(), _example("similar_response.json")
    assert {"query", "results", "warnings"} <= set(data)
    assert data["results"][0].keys() == example["results"][0].keys()


def test_similar_rejects_bad_latitude(mock_client):
    r = mock_client.post("/api/similar", json={"body": "moon", "lat": 123, "lon": 0})
    assert r.status_code == 422