"""Alturas de detalle y Grad-CAM (contracts/heights.example.json, docs/contratos.md §5)."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response

from app.core.config import get_artifacts_dir

router = APIRouter(prefix="/api", tags=["patches"])
PATCH_ID_RE = re.compile(r"^(earth|moon|mars)-(60|500|1000)-\d{6}$")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
HEIGHT_HEADERS = (
    "X-Min",
    "X-Max",
    "X-M-Per-Px",
    "X-Width",
    "X-Height",
    "X-Dtype",
    "X-Endianness",
)


def _validated_patch_id(patch_id: str) -> str:
    if not PATCH_ID_RE.fullmatch(patch_id):
        raise HTTPException(status_code=404, detail=f"unknown patch_id: {patch_id}")
    return patch_id


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _number(value, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=500, detail=f"invalid heights metadata: {name}")
    if not math.isfinite(number):
        raise HTTPException(status_code=500, detail=f"invalid heights metadata: {name}")
    return number


def _positive_int(value, name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=500, detail=f"invalid heights metadata: {name}")
    if number <= 0:
        raise HTTPException(status_code=500, detail=f"invalid heights metadata: {name}")
    return number


@router.get("/patch/{patch_id}/heights")
def get_heights(patch_id: str):
    patch_id = _validated_patch_id(patch_id)
    base = get_artifacts_dir() / "heights"
    binary_path = base / f"{patch_id}.bin"
    metadata_path = base / f"{patch_id}.json"
    if not binary_path.is_file() or not metadata_path.is_file():
        raise HTTPException(status_code=404, detail=f"heights not found for {patch_id}")

    metadata = _read_json(metadata_path)
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=500, detail=f"invalid heights metadata for {patch_id}")
    if metadata.get("patch_id") != patch_id:
        raise HTTPException(status_code=500, detail=f"heights metadata mismatch for {patch_id}")
    if metadata.get("dtype") != "float32" or metadata.get("endianness") != "little":
        raise HTTPException(status_code=500, detail=f"unsupported heights dtype for {patch_id}")

    width = _positive_int(metadata.get("width"), "width")
    height = _positive_int(metadata.get("height"), "height")
    min_value = _number(metadata.get("min"), "min")
    max_value = _number(metadata.get("max"), "max")
    m_per_px = _number(metadata.get("m_per_px"), "m_per_px")

    payload = binary_path.read_bytes()
    expected = width * height * 4
    if len(payload) != expected:
        raise HTTPException(
            status_code=500,
            detail=f"heights size mismatch for {patch_id}: {len(payload)} != {expected}",
        )

    headers = {
        "X-Min": str(min_value),
        "X-Max": str(max_value),
        "X-M-Per-Px": str(m_per_px),
        "X-Width": str(width),
        "X-Height": str(height),
        "X-Dtype": "float32",
        "X-Endianness": "little",
        "Cache-Control": "public, max-age=3600",
    }
    return Response(content=payload, media_type="application/octet-stream", headers=headers)


@router.get("/gradcam/{query_id}/{patch_id}")
def get_gradcam(query_id: str, patch_id: str):
    query_id = _validated_patch_id(query_id)
    patch_id = _validated_patch_id(patch_id)
    path = get_artifacts_dir() / "gradcam" / f"{query_id}__{patch_id}.png"
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"gradcam not found for {query_id} / {patch_id}",
        )
    payload = path.read_bytes()
    if not payload.startswith(PNG_SIGNATURE):
        raise HTTPException(status_code=500, detail=f"invalid gradcam artifact: {path.name}")
    return Response(
        content=payload,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )
