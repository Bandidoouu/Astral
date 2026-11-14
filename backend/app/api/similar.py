"""POST /api/similar (docs/contratos.md §3)."""
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.search import search_similar

router = APIRouter()

Body = Literal["earth", "moon", "mars"]


class SimilarRequest(BaseModel):
    body: Body
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    target_bodies: list[Body] | None = None
    scale_m: Literal[1000, 60] = 1000
    profile: Literal["general", "rover", "isru", "habitat", "eva", "astrobiology"] = "general"
    k: int = Field(default=10, ge=1, le=100)
    method: Literal["rrf", "hybrid", "net", "baseline"] = "rrf"


@router.post("/api/similar")
def similar(req: SimilarRequest) -> dict:
    try:
        return search_similar(req.body, req.lat, req.lon, req.target_bodies, req.k,
                              req.profile, req.scale_m, req.method)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc