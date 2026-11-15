from fastapi import APIRouter
from app.core.config import get_artifacts_dir
from app.core.schemas import HealthResponse
from app.services.search_service import get_searcher

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    """
    Verifica estado de salud del backend y disponibilidad de artefactos de ML.
    """
    artifacts_dir = get_artifacts_dir()
    scale_60 = (artifacts_dir / "meta_60.parquet").exists()
    scale_1000 = (artifacts_dir / "meta_1000.parquet").exists()
    searcher_ok = get_searcher() is not None

    return HealthResponse(
        status="ok",
        encoder_version=1,
        service="ASTRAL Backend API",
        searcher_available=searcher_ok,
        scale_60_available=scale_60,
        scale_1000_available=scale_1000,
    )
