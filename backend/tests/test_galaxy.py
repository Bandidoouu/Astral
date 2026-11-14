import json

from app.core.config import get_contracts_dir

SAMPLE = [
    {"id": "earth-60-000123", "body": "earth", "x": 1.25, "y": -0.40, "z": 3.10},
    {"id": "moon-60-002461", "body": "moon", "x": 1.31, "y": -0.35, "z": 2.95},
]


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_scale_specific_file_wins(client, artifacts_dir):
    _write(artifacts_dir / "galaxy_60.json", SAMPLE)
    _write(artifacts_dir / "galaxy.json", SAMPLE[:1])
    response = client.get("/api/galaxy?scale=60")
    assert response.status_code == 200
    assert response.json() == SAMPLE


def test_falls_back_to_galaxy_json(client, artifacts_dir):
    _write(artifacts_dir / "galaxy.json", SAMPLE)
    response = client.get("/api/galaxy?scale=60")
    assert response.status_code == 200
    assert response.json() == SAMPLE


def test_falls_back_to_contract_mock(client, artifacts_dir):
    expected = json.loads(
        (get_contracts_dir() / "galaxy.example.json").read_text(encoding="utf-8")
    )
    response = client.get("/api/galaxy?scale=60")
    assert response.status_code == 200
    assert response.json() == expected


def test_invalid_scale_is_422(client):
    assert client.get("/api/galaxy?scale=42").status_code == 422


def test_corrupt_artifact_is_500(client, artifacts_dir):
    (artifacts_dir / "galaxy_60.json").write_text("{not json", encoding="utf-8")
    assert client.get("/api/galaxy?scale=60").status_code == 500
