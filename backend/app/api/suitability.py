import json
from typing import Literal
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.core.config import get_artifacts_dir

router = APIRouter(prefix="/api/suitability", tags=["Suitability"])

SuitabilityCriterion = Literal["landing", "rover", "ice", "temperature", "total"]
VALID_CRITERIA = {"landing", "rover", "ice", "temperature", "total"}


def _get_suitability_dir():
    return get_artifacts_dir() / "suitability"


@router.get("/moon_south")
def get_suitability_metadata():
    """
    Retorna los pesos, reglas y candidatos de la NASA con sus puntajes.
    """
    json_path = _get_suitability_dir() / "suitability_moon.json"
    if not json_path.exists():
        return {
            "status": "pending",
            "message": "Los artefactos de aptitud lunar se están generando.",
            "candidates": [],
        }
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/moon_south/{criterion}")
def get_suitability_image(criterion: str):
    """
    Retorna la imagen PNG de aptitud lunar:
    landing, rover, ice, temperature, total
    """
    if criterion not in VALID_CRITERIA:
        raise HTTPException(
            status_code=400,
            detail=f"Criterio '{criterion}' no válido. Opciones: {sorted(VALID_CRITERIA)}",
        )

    png_path = _get_suitability_dir() / f"moon_south_{criterion}.png"
    if not png_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Capa '{criterion}' no encontrada en data/artifacts/suitability/.",
        )
    return FileResponse(png_path, media_type="image/png")
