"""
OE3 (backend) — Test de la API y el RBAC.

Verifica:
  - Login correcto devuelve token; login incorrecto da 401.
  - Endpoints protegidos rechazan peticiones sin token.
  - RBAC: el técnico de Curepto NO obtiene datos de Talca (recorte en servidor).

Requiere BD cargada + usuarios de prueba creados (crear_usuarios.py).
Se salta si no hay BD.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app

client = TestClient(app)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://sitd:sitd_dev_only@localhost:5432/sitd",
)


@pytest.fixture(scope="module", autouse=True)
def _requiere_bd():
    try:
        eng = create_engine(DATABASE_URL)
        with eng.connect() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM usuario")).scalar()
        if not n:
            pytest.skip("Sin usuarios: correr crear_usuarios.py")
    except Exception:
        pytest.skip("BD no disponible")


def _login(correo, pwd="demo1234"):
    r = client.post("/auth/login", json={"correo": correo, "password": pwd})
    return r


def test_login_correcto():
    r = _login("regional@maule.cl")
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert r.json()["rol"] == "regional"


def test_login_incorrecto():
    r = _login("regional@maule.cl", "clave_mala")
    assert r.status_code == 401


def test_endpoint_protegido_sin_token():
    r = client.post("/agregacion", json={"poligono_wkt": "POLYGON((0 0,1 0,1 1,0 1,0 0))"})
    assert r.status_code == 401


def _bbox_comuna(nombre):
    eng = create_engine(DATABASE_URL)
    with eng.connect() as conn:
        return conn.execute(text("""
            SELECT ST_AsText(ST_Envelope(ST_Collect(geom)))
            FROM unidad_censal WHERE nombre_comuna = :n
        """), {"n": nombre}).scalar()


def test_rbac_tecnico_no_ve_otra_comuna():
    """El técnico de Curepto pide un polígono sobre TALCA; el servidor lo
    recorta a Curepto -> no debe recibir población de Talca."""
    token = _login("secplan@curepto.cl").json()["access_token"]
    bbox_talca = _bbox_comuna("TALCA")
    r = client.post(
        "/agregacion",
        json={"poligono_wkt": bbox_talca},
        headers={"Authorization": f"Bearer {token}"},
    )
    # O bien 400 (no intersecta su comuna) o bien datos SOLO de su comuna.
    if r.status_code == 200:
        # La población no puede ser la de Talca (230k); a lo sumo la de Curepto.
        assert r.json().get("poblacion_total", 0) < 20000
    else:
        assert r.status_code == 400


def test_regional_ve_la_region():
    token = _login("regional@maule.cl").json()["access_token"]
    bbox_talca = _bbox_comuna("TALCA")
    r = client.post(
        "/agregacion",
        json={"poligono_wkt": bbox_talca},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["n_unidades"] > 0
