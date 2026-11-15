"""POST /api/similar (docs/contratos.md §3)."""
from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from app.core.schemas import SimilarRequest
from app.services.search import search_similar

router = APIRouter(prefix="/api", tags=["Similarity Search"])


@router.post("/similar")
def similar(req: SimilarRequest) -> Dict[str, Any]:
    """
    POST /api/similar
    Busca los gemelos del punto planetario solicitado.
    """
    try:
        return search_similar(
            body=req.body,
            lat=req.lat,
            lon=req.lon,
            target_bodies=req.target_bodies,
            k=req.k,
            profile=req.profile,
            scale_m=req.scale_m,
            method=req.method or "rrf",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
