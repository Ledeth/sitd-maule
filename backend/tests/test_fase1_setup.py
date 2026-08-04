"""Fase I — tests de humo.

Los tests de OE1/OE2/OE3 se implementan en sus fases respectivas:
  tests/test_oe1_integracion.py  (Fase II)
  tests/test_oe2_agregacion.py   (Fase III)
  tests/test_oe3_api.py          (Fase IV)

Estos solo verifican que el esqueleto es coherente. Requieren la BD
levantada (docker compose up db) para el test de esquema.
"""
import os

import pytest
from sqlalchemy import create_engine, inspect, text

from app.core.config import CRS_TRABAJO, ROLES_VALIDOS

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://sitd:sitd_dev_only@localhost:5432/sitd",
)

TABLAS_ESPERADAS = {
    "comuna",
    "manzana_censal",
    "conaf_uso_suelo",
    "manzana_conaf",
    "etl_log",
    "usuario",
    "consulta_agregacion",
}


def test_constantes_de_dominio():
    assert CRS_TRABAJO == "EPSG:32719"
    assert set(ROLES_VALIDOS) == {"regional", "tecnico"}


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(DATABASE_URL)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("BD no disponible: levantar con `docker compose up -d db`")
    return eng


def test_esquema_completo(engine):
    tablas = set(inspect(engine).get_table_names())
    faltantes = TABLAS_ESPERADAS - tablas
    assert not faltantes, f"Faltan tablas del esquema: {faltantes}"


def test_postgis_activo_y_srid(engine):
    with engine.connect() as conn:
        version = conn.execute(text("SELECT PostGIS_Version()")).scalar()
        assert version is not None
        srid = conn.execute(
            text(
                "SELECT Find_SRID('public', 'manzana_censal', 'geom')"
            )
        ).scalar()
        assert srid == 32719, "Las geometrías de manzanas deben estar en EPSG:32719"
