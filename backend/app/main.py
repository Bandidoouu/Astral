"""Aplicación FastAPI de ASTRAL: CORS y routers de la API."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import galaxy, patches
from app.api.patches import HEIGHT_HEADERS

app = FastAPI(title="ASTRAL API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=list(HEIGHT_HEADERS),
)

app.include_router(galaxy.router)
app.include_router(patches.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "encoder_version": 1}
