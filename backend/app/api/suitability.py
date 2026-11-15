"""GET /api/suitability/{moon_south,mars}: metadatos y PNG de las capas de aptitud
(docs/contratos.md §4b y §5). Se sirven tal cual los exporta ML."""
import json
from typing import Literal
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.core.config import get_artifacts_dir

router = APIRouter(prefix="/api/suitability", tags=["Suitability"])

SuitabilityCriterion = Literal["landing", "rover", "ice", "temperature", "total"]
VALID_CRITERIA = {"landing", "rover", "ice", "temperature", "total"}
MARS_CRITERIA = {"landing", "rover", "elevation", "hydrogen", "total"}

# Primero el JSON completo para la API (con zonas recomendadas); si no existe, el de ML.
METADATA_FILES = {
    "moon_south": ("api_moon_south.json", "suitability_moon.json"),
    "mars": ("api_mars.json",),
}
PENDING = {
    "moon_south": "Los artefactos de aptitud lunar se están generando.",
    "mars": "Los artefactos de aptitud de Marte se están generando.",
}


def _get_suitability_dir():
    return get_artifacts_dir() / "suitability"


def _metadata(layer: str):
    for name in METADATA_FILES[layer]:
        path = _get_suitability_dir() / name
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    return {"status": "pending", "message": PENDING[layer], "candidates": []}


def _image(prefix: str, criterion: str, valid: set):
    if criterion not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Criterio '{criterion}' no válido. Opciones: {sorted(valid)}",
        )
    png_path = _get_suitability_dir() / f"{prefix}_{criterion}.png"
    if not png_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Capa '{criterion}' no encontrada en data/artifacts/suitability/.",
        )
    return FileResponse(png_path, media_type="image/png")


@router.get("/moon_south")
def get_suitability_metadata():
    """Pesos, reglas, zonas recomendadas y candidatos de la NASA con sus puntajes."""
    return _metadata("moon_south")


@router.get("/moon_south/{criterion}")
def get_suitability_image(criterion: str):
    """PNG de aptitud lunar: landing, rover, ice, temperature, total."""
    return _image("moon_south", criterion, VALID_CRITERIA)


@router.get("/mars")
def get_mars_suitability_metadata():
    """Pesos, reglas, zonas recomendadas y sitios de Marte con sus puntajes."""
    return _metadata("mars")


@router.get("/mars/{criterion}")
def get_mars_suitability_image(criterion: str):
    """PNG de aptitud de Marte: landing, rover, elevation, hydrogen, total."""
    return _image("mars", criterion, MARS_CRITERIA)
