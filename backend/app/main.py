"""Aplicación FastAPI de ASTRAL: CORS y routers de la API."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import galaxy, health, patches, similar, suitability
from app.api.patches import HEIGHT_HEADERS
from app.services.artifacts import get_searcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_searcher()  # carga única al arrancar
    yield


app = FastAPI(
    title="ASTRAL API",
    description="Planetary Shazam for Moon and Mars analogs · NASA Space Apps Challenge 2026",
    version="1.0.0",
    lifespan=lifespan,
)

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
app.include_router(suitability.router)
app.include_router(health.router)


@app.get("/")
def root():
    return {
        "service": "ASTRAL Backend API",
        "status": "online",
        "docs": "/docs",
        "health": "/api/health",
    }
