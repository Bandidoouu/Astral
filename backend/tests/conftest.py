import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import scoring, thermal  # noqa: E402


@pytest.fixture
def artifacts_dir(tmp_path, monkeypatch):
    root = tmp_path / "artifacts"
    root.mkdir()
    monkeypatch.setenv("ASTRAL_ARTIFACTS", str(root))
    thermal._load_features_file.cache_clear()
    scoring._load_operations_cached.cache_clear()
    yield root
    thermal._load_features_file.cache_clear()
    scoring._load_operations_cached.cache_clear()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
