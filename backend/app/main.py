"""SITD — API (Fase I: solo esqueleto + healthcheck).

Los routers reales se agregan en:
  Fase II  -> app/etl/       (se ejecuta como scripts, no expone endpoints)
  Fase III -> app/motor/     (agregación elástica)
  Fase IV  -> app/api/       (endpoints REST + RBAC)
"""
from fastapi import FastAPI
from sqlalchemy import create_engine, text

from app.core.config import settings, CRS_TRABAJO

app = FastAPI(
    title="SITD — Sistema de Inteligencia Territorial Dinámica",
    description="MVP Región del Maule. Acceso Restringido - Perfil Funcionario.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    """Verifica API viva + conexión a PostGIS + versión de la extensión."""
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        postgis = conn.execute(text("SELECT PostGIS_Version()")).scalar()
    return {"status": "ok", "postgis": postgis, "crs_trabajo": CRS_TRABAJO}
