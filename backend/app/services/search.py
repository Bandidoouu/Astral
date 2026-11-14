"""Búsqueda de gemelos: envoltura delgada sobre ml.search.Searcher."""
import json

from app.core.config import get_contracts_dir
from app.services.artifacts import get_searcher


def mock_response() -> dict:
    path = get_contracts_dir() / "similar_response.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("warnings", []).append("mock: sin artefactos de ML, respuesta de ejemplo")
    return data


def search_similar(body, lat, lon, target_bodies=None, k=10,
                   profile="general", scale_m=1000, method="rrf") -> dict:
    searcher = get_searcher()
    if searcher is None:
        return mock_response()
    return searcher.search(body, lat, lon, target_bodies, k, profile,
                           method=method, scale_m=scale_m)