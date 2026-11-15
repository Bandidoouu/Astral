import json
import logging
from typing import Any, Dict
from fastapi import APIRouter
from app.core.config import CONTRACTS_DIR
from app.core.schemas import SimilarRequest
from app.services.search_service import get_searcher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Similarity Search"])


@router.post("/similar")
def find_similar(req: SimilarRequest) -> Dict[str, Any]:
    """
    POST /api/similar
    Busca los gemelos del punto planetario solicitado.
    Usa ml.search.Searcher si los artefactos están disponibles, o el mock oficial
    de contracts/similar_response.json para que el frontend nunca se bloquee.
    """
    searcher = get_searcher()
    if searcher is not None:
        try:
            return searcher.search(
                body=req.body,
                lat=req.lat,
                lon=req.lon,
                target_bodies=req.target_bodies,
                k=req.k,
                profile=req.profile,
                method=req.method or "rrf",
                scale_m=req.scale_m,
            )
        except Exception as e:
            logger.error(f"Error en Searcher.search: {e}. Usando mock.")

    targets = req.target_bodies or [
        b for b in ("earth", "moon", "mars") if b != req.body
    ]

    # Fallback al contrato mock oficial
    mock_file = CONTRACTS_DIR / "similar_response.json"
    if mock_file.exists():
        with open(mock_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "query" in data:
                data["query"]["body"] = req.body
                data["query"]["lat"] = req.lat
                data["query"]["lon"] = req.lon
                data["query"]["profile"] = req.profile
                data["query"]["scale_m"] = req.scale_m
                data["query"]["method"] = req.method or "rrf"
                data["query"]["target_bodies"] = targets
                if "patches" in data["query"]:
                    data["query"]["patches"] = {
                        t: data["query"]["patches"].get(
                            t,
                            {
                                "patch_id": f"{req.body}-{req.scale_m}-000001",
                                "scale_m": req.scale_m,
                                "distance_km": 0.0,
                            },
                        )
                        for t in targets
                    }
            if "results" in data and req.target_bodies:
                data["results"] = [
                    r for r in data["results"] if r.get("body") in targets
                ]
            return data

    return {
        "query": {
            "body": req.body,
            "lat": req.lat,
            "lon": req.lon,
            "profile": req.profile,
            "scale_m": req.scale_m,
            "target_bodies": targets,
            "method": req.method or "rrf",
            "patches": {
                t: {
                    "patch_id": f"{req.body}-{req.scale_m}-000001",
                    "scale_m": req.scale_m,
                    "distance_km": 0.0,
                }
                for t in targets
            },
            "attributes": {
                "tmax_k": None,
                "tmin_k": None,
                "trange_k": None,
                "albedo": None,
                "ice_distance_km": None,
                "ice_frac": None,
                "soil_raw": None,
                "soil_pct": None,
                "precip_mm": None,
            },
        },
        "results": [],
        "warnings": ["Artefactos de ML no encontrados y sin mock disponible."],
        "_note": "Mock fallback",
    }
