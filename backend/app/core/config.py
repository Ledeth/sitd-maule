"""Configuración central del SITD (Fase I).

Todas las constantes del dominio viven aquí para que ETL, motor y API
compartan una sola fuente de verdad.
"""
from pydantic_settings import BaseSettings


# CRS proyectado único de trabajo (UTM 19S, Chile continental).
# Riesgo identificado en el plan: CRS distintos entre INE y CONAF.
# TODO Fase II: el ETL reproyecta TODO a este CRS antes de cualquier
# operación espacial y lo trata como bloqueante si la reproyección falla.
CRS_TRABAJO = "EPSG:32719"

CODIGO_REGION_MAULE = "07"

ROLES_VALIDOS = ("regional", "tecnico")


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://sitd:sitd_dev_only@localhost:5432/sitd"
    jwt_secret: str = "cambiar_en_staging"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    class Config:
        env_file = ".env"


settings = Settings()
