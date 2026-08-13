"""SITD — API (Fase IV: motor expuesto vía REST con RBAC)."""
import os

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

# CORS. En local se permiten los puertos de Vite. En producción, el dominio del
# frontend se añade vía la variable CORS_ORIGINS (lista separada por comas), para
# no hardcodear la URL de Vercel en el código.
origenes = ["http://localhost:3000", "http://localhost:5173"]
extra = os.getenv("CORS_ORIGINS", "")
if extra:
    origenes += [o.strip() for o in extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes,
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
