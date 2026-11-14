"""Rutas de configuración del backend (sin rutas absolutas hardcodeadas)."""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
CONTRACTS_DIR = REPO_ROOT / "contracts"


def get_artifacts_dir() -> Path:
    """Directorio de artefactos de ML; se puede sobreescribir con ASTRAL_ARTIFACTS."""
    raw = os.environ.get("ASTRAL_ARTIFACTS")
    path = Path(raw).expanduser() if raw else REPO_ROOT / "data" / "artifacts"
    return path if path.is_absolute() else REPO_ROOT / path


def get_contracts_dir() -> Path:
    return CONTRACTS_DIR
