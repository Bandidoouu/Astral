"""Búsqueda de gemelos: envoltura delgada sobre ml.search.Searcher."""
import json
import logging

from app.core.config import get_contracts_dir
from app.services.artifacts import get_searcher

log = logging.getLogger(__name__)


def mock_response(
    body="moon",
    lat=-89.5,
    lon=130.0,
    target_bodies=None,
    k=10,
    profile="general",
    scale_m=1000,
    method="rrf",
) -> dict:
    path = get_contracts_dir() / "similar_response.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    targets = target_bodies or [b for b in ("earth", "moon", "mars") if b != body]
    if "query" in data:
        data["query"]["body"] = body
        data["query"]["lat"] = lat
        data["query"]["lon"] = lon
        data["query"]["profile"] = profile
        data["query"]["scale_m"] = scale_m
        data["query"]["method"] = method or "rrf"
        data["query"]["target_bodies"] = targets
        if "patches" in data["query"]:
            data["query"]["patches"] = {
                t: data["query"]["patches"].get(
                    t,
                    {
                        "patch_id": f"{body}-{scale_m}-000001",
                        "scale_m": scale_m,
                        "distance_km": 0.0,
                    },
                )
                for t in targets
            }
    if "results" in data and target_bodies:
        data["results"] = [r for r in data["results"] if r.get("body") in targets]
    data.setdefault("warnings", []).append("mock: sin artefactos de ML, respuesta de ejemplo")
    return data


def search_similar(
    body,
    lat,
    lon,
    target_bodies=None,
    k=10,
    profile="general",
    scale_m=1000,
    method="rrf",
) -> dict:
    searcher = get_searcher()
    if searcher is None:
        return mock_response(body, lat, lon, target_bodies, k, profile, scale_m, method)
    try:
        return searcher.search(
            body,
            lat,
            lon,
            target_bodies,
            k,
            profile,
            method=method,
            scale_m=scale_m,
        )
    except Exception as exc:
        log.warning("Fallo en Searcher.search (%s), recurriendo al mock", exc)
        return mock_response(body, lat, lon, target_bodies, k, profile, scale_m, method)
