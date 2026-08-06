"""
SITD — Seguridad (Fase IV): JWT + hashing + RBAC.

RBAC del brief:
  - rol 'regional' (GORE/Gobernador/Alcalde): ve toda la región.
  - rol 'tecnico'  (SECPLAN): restringido a su comuna (codigo_comuna).

JWT simple según la instrucción del brief (no OAuth institucional para el MVP).

Nota técnica: se usa `bcrypt` directamente en lugar de `passlib`. passlib no es
compatible con bcrypt 4.x (falla al leer la versión del backend) y su
mantenimiento está detenido. bcrypt directo es más simple y no añade capas.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

# HTTPBearer: el diálogo "Authorize" de /docs pide solo el token,
# que es lo que realmente usa esta API (el login recibe JSON, no un
# formulario OAuth2). Evita la inconsistencia del esquema anterior.
bearer_scheme = HTTPBearer()

# bcrypt no admite secretos de más de 72 bytes; se trunca explícitamente.
_MAX_BYTES = 72


class DatosToken(BaseModel):
    correo: str
    rol: str
    codigo_comuna: Optional[str] = None


def _a_bytes(plano: str) -> bytes:
    return plano.encode("utf-8")[:_MAX_BYTES]


def hashear_password(plano: str) -> str:
    """Genera el hash bcrypt de una contraseña (nunca se guarda en texto plano)."""
    return bcrypt.hashpw(_a_bytes(plano), bcrypt.gensalt()).decode("utf-8")


def verificar_password(plano: str, hasheado: str) -> bool:
    """Compara una contraseña contra su hash almacenado."""
    try:
        return bcrypt.checkpw(_a_bytes(plano), hasheado.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def crear_token(datos: DatosToken) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": datos.correo,
        "rol": datos.rol,
        "codigo_comuna": datos.codigo_comuna,
        "exp": expira,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def usuario_actual(
    credencial: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> DatosToken:
    """Dependencia FastAPI: decodifica el JWT y devuelve el usuario, o 401."""
    cred_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            credencial.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        correo = payload.get("sub")
        rol = payload.get("rol")
        if correo is None or rol is None:
            raise cred_error
    except JWTError:
        raise cred_error
    return DatosToken(
        correo=correo, rol=rol, codigo_comuna=payload.get("codigo_comuna")
    )
