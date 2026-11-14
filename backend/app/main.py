"""Aplicación FastAPI de ASTRAL: CORS y routers de la API."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import galaxy, patches, similar
from app.api.patches import HEIGHT_HEADERS
from app.services.artifacts import get_searcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_searcher()  # carga única al arrancar
    yield


app = FastAPI(title="ASTRAL API", version="0.1.0", lifespan=lifespan)

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
app.include_router(similar.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "encoder_version": 1}