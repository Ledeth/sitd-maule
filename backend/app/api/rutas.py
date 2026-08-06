"""
SITD — API REST (Fase IV). Expone el motor de agregación con RBAC.

Endpoints:
  POST /auth/login              -> obtiene JWT (correo + password)
  GET  /me                      -> datos del usuario autenticado
  POST /agregacion              -> agregación elástica sobre polígono ad-hoc
  GET  /comunas                 -> lista de comunas (para el frontend)

Decisión RBAC (defendible): la restricción del rol 'tecnico' se aplica en el
SERVIDOR. Su polígono se intersecta con la geometría de su comuna ANTES de
agregar, de modo que no puede obtener datos de otras comunas ni manipulando
la petición. El frontend solo refleja lo que el backend ya garantiza.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.api.seguridad import (
    DatosToken, crear_token, usuario_actual, verificar_password,
)
from app.motor.agregacion import agregar_por_poligono

router = APIRouter()
engine = create_engine(settings.database_url)


# --------------------------- Modelos de entrada/salida ---------------------------
class LoginIn(BaseModel):
    correo: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str


class AgregacionIn(BaseModel):
    poligono_wkt: str = Field(
        ...,
        description="Polígono ad-hoc en WKT, EPSG:32719. Ej: 'POLYGON((x y, ...))'",
    )


# --------------------------- Auth ---------------------------
@router.post("/auth/login", response_model=TokenOut)
def login(datos: LoginIn):
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT correo, hash_password, rol, codigo_comuna, activo
            FROM usuario WHERE correo = :correo
        """), {"correo": datos.correo}).mappings().first()

    if not row or not row["activo"] or not verificar_password(
        datos.password, row["hash_password"]
    ):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    token = crear_token(DatosToken(
        correo=row["correo"], rol=row["rol"], codigo_comuna=row["codigo_comuna"]
    ))
    return TokenOut(access_token=token, rol=row["rol"])


@router.get("/me", response_model=DatosToken)
def me(usuario: DatosToken = Depends(usuario_actual)):
    return usuario


# --------------------------- Datos de apoyo ---------------------------
@router.get("/comunas")
def listar_comunas(usuario: DatosToken = Depends(usuario_actual)):
    """Lista de comunas. El técnico solo ve la suya."""
    sql = "SELECT codigo_comuna, nombre FROM comuna"
    params = {}
    if usuario.rol == "tecnico":
        sql += " WHERE codigo_comuna = :cc"
        params["cc"] = usuario.codigo_comuna
    sql += " ORDER BY nombre"
    with engine.connect() as conn:
        filas = conn.execute(text(sql), params).mappings().all()
    return [dict(f) for f in filas]


# --------------------------- Núcleo: agregación con RBAC ---------------------------
@router.post("/agregacion")
def agregacion(datos: AgregacionIn, usuario: DatosToken = Depends(usuario_actual)):
    """Agregación elástica. Para el rol 'tecnico', el polígono se recorta a su
    comuna en el servidor antes de agregar (RBAC territorial real)."""
    poligono = datos.poligono_wkt

    if usuario.rol == "tecnico":
        if not usuario.codigo_comuna:
            raise HTTPException(status_code=403, detail="Técnico sin comuna asignada")
        # Recortar el polígono a la comuna del técnico (intersección en servidor)
        with engine.connect() as conn:
            recortado = conn.execute(text("""
                SELECT ST_AsText(
                    ST_Intersection(
                        ST_GeomFromText(:wkt, 32719),
                        (SELECT ST_Union(geom) FROM unidad_censal
                         WHERE codigo_comuna = :cc)
                    )
                )
            """), {"wkt": poligono, "cc": usuario.codigo_comuna}).scalar()
        if not recortado or recortado.upper().startswith("GEOMETRYCOLLECTION EMPTY"):
            raise HTTPException(
                status_code=400,
                detail="El polígono no intersecta la comuna asignada.",
            )
        poligono = recortado

    try:
        resultado = agregar_por_poligono(engine, poligono)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en la agregación: {e}")

    resultado["rol_solicitante"] = usuario.rol
    return resultado
