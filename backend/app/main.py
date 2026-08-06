"""SITD — API (Fase IV: motor expuesto vía REST con RBAC)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text

from app.core.config import settings, CRS_TRABAJO
from app.api.rutas import router

app = FastAPI(
    title="SITD — Sistema de Inteligencia Territorial Dinámica",
    description="MVP Región del Maule. Acceso Restringido - Perfil Funcionario.",
    version="0.4.0",
)

# CORS: permite que el frontend (React en localhost) consuma la API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health() -> dict:
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        postgis = conn.execute(text("SELECT PostGIS_Version()")).scalar()
    return {"status": "ok", "postgis": postgis, "crs_trabajo": CRS_TRABAJO}
