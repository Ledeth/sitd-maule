"""
SITD — Crear usuarios de prueba (Fase IV).

Crea dos usuarios para probar el RBAC:
  - regional@maule.cl  / demo1234  (rol regional, ve toda la región)
  - secplan@curepto.cl / demo1234  (rol tecnico, solo comuna 7103 Curepto)

Uso:
    python app/api/crear_usuarios.py
"""
import os

from sqlalchemy import create_engine, text

from app.api.seguridad import hashear_password

url = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://sitd:sitd_dev_only@localhost:5432/sitd",
)
engine = create_engine(url)

USUARIOS = [
    ("regional@maule.cl", "demo1234", "regional", None),
    ("secplan@curepto.cl", "demo1234", "tecnico", "7103"),
]

with engine.begin() as conn:
    for correo, pwd, rol, comuna in USUARIOS:
        conn.execute(text("""
            INSERT INTO usuario (correo, hash_password, rol, codigo_comuna)
            VALUES (:correo, :hash, :rol, :cc)
            ON CONFLICT (correo) DO UPDATE
                SET hash_password = EXCLUDED.hash_password,
                    rol = EXCLUDED.rol,
                    codigo_comuna = EXCLUDED.codigo_comuna
        """), {"correo": correo, "hash": hashear_password(pwd),
               "rol": rol, "cc": comuna})
        print(f"  Usuario {correo} ({rol}) creado/actualizado.")

print("Listo. Contraseña de ambos: demo1234")
