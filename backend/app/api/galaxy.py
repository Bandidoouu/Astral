"""GET /api/galaxy: coordenadas UMAP 3D de la galaxia (contracts/galaxy.example.json)."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.config import get_artifacts_dir, get_contracts_dir

router = APIRouter(prefix="/api", tags=["galaxy"])
ALLOWED_SCALES = {60, 500, 1000}
BODIES = {"earth", "moon", "mars"}
REQUIRED_KEYS = {"id", "body", "x", "y", "z"}


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _validate_galaxy(payload) -> list[dict]:
    if not isinstance(payload, list):
        raise ValueError("galaxy must be a JSON array")
    for item in payload:
        if not isinstance(item, dict) or not REQUIRED_KEYS.issubset(item):
            raise ValueError("galaxy items need id, body, x, y and z")
        if item["body"] not in BODIES:
            raise ValueError("galaxy body must be earth, moon or mars")
    return payload


def _candidate_paths(scale: int) -> list[Path]:
    artifacts = get_artifacts_dir()
    return [
        artifacts / f"galaxy_{scale}.json",
        artifacts / "galaxy.json",
        get_contracts_dir() / "galaxy.example.json",
    ]


@router.get("/galaxy")
def get_galaxy(scale: int = Query(60, description="Pixel scale: 60, 500 or 1000 m")):
    if scale not in ALLOWED_SCALES:
        raise HTTPException(
            status_code=422,
            detail=f"scale must be one of {sorted(ALLOWED_SCALES)}",
        )
    for path in _candidate_paths(scale):
        if not path.is_file():
            continue
        payload = _read_json(path)
        if payload is None:
            raise HTTPException(status_code=500, detail=f"invalid galaxy artifact: {path.name}")
        try:
            data = _validate_galaxy(payload)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=f"invalid galaxy artifact: {exc}") from exc
        return JSONResponse(content=data)
    raise HTTPException(status_code=404, detail="galaxy artifact not found")
