import json
import logging
from fastapi import APIRouter
from app.core.config import CONTRACTS_DIR
from app.core.schemas import SimilarRequest
from app.services.search_service import get_searcher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Similarity Search"])

@router.post("/similar")
def find_similar(req: SimilarRequest):
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
                method="rrf",
                scale_m=req.scale_m,
            )
        except Exception as e:
            logger.error(f"Error en Searcher.search: {e}. Usando mock.")

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
                if req.target_bodies:
                    data["query"]["target_bodies"] = req.target_bodies
            return data

    return {
        "query": {
            "body": req.body,
            "lat": req.lat,
            "lon": req.lon,
            "profile": req.profile,
            "scale_m": req.scale_m,
            "target_bodies": req.target_bodies or ["earth", "mars"]
        },
        "results": [],
        "warnings": ["Artefactos de ML no encontrados y sin mock disponible."]
    }
