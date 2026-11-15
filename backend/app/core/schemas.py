from typing import List, Literal, Optional
from pydantic import BaseModel, Field

CelestialBody = Literal["earth", "moon", "mars"]
ScaleM = Literal[60, 1000]
MissionProfile = Literal[
    "general", "rover", "isru", "habitat", "eva", "astrobiology"
]
SearchMethod = Literal["rrf", "hybrid", "net", "baseline", "random"]
ScaleMode = Literal["same_size", "gravity_scaled"]


class SimilarRequest(BaseModel):
    body: CelestialBody = Field(
        ..., description="Cuerpo celeste de origen: 'moon', 'mars' o 'earth'"
    )
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitud planetocéntrica (-90 a 90)")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitud planetocéntrica (-180 a 180)")
    target_bodies: Optional[List[CelestialBody]] = Field(
        default=None,
        description="Cuerpos objetivo. Si es None, busca en los otros dos cuerpos",
    )
    scale_m: ScaleM = Field(
        default=1000,
        description="Escala de píxel: 1000 (global) o 60 (detalle Luna-Tierra)",
    )
    profile: MissionProfile = Field(
        default="general",
        description="Perfil de misión: 'general', 'rover', 'isru', 'habitat', 'eva', 'astrobiology'",
    )
    scale_mode: ScaleMode = Field(
        default="same_size",
        description="'same_size' (ventanas iguales en km) o 'gravity_scaled' (Luna 6x, Marte 2.6x; solo scale_m=1000)",
    )
    method: Optional[SearchMethod] = Field(
        default="rrf",
        description="Método de búsqueda de terreno: 'rrf', 'hybrid', 'net', 'baseline', 'random'",
    )
    k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Número de gemelos a devolver por cuerpo destino",
    )


class HealthResponse(BaseModel):
    status: str = "ok"
    encoder_version: int = 1
    service: str = "ASTRAL Backend API"
    searcher_available: bool = False
    scale_60_available: bool = False
    scale_1000_available: bool = False
