"""
SITD — Carga inicial de la tabla `comuna` (Fase II, prerequisito).

La tabla comuna debe poblarse ANTES de etl_censo.py, porque unidad_censal
tiene una foreign key hacia comuna (cada manzana pertenece a una comuna).

Extrae las 30 comunas del Maule (código CUT + nombre) desde el mismo gpkg
del censo, de modo que no dependemos de otra fuente. La geometría comunal se
deja nula por ahora (no es necesaria para el MVP; el RBAC usa solo el código).

Uso:
    python carga_comunas.py --archivo /data/maule_base_censal_unificada_32719.gpkg
"""
from __future__ import annotations

import argparse
import os
import sys

import geopandas as gpd


def main():
    parser = argparse.ArgumentParser(description="Carga tabla comuna (SITD)")
    parser.add_argument("--archivo", required=True, help="Ruta al .gpkg del INE")
    args = parser.parse_args()

    if not os.path.exists(args.archivo):
        print(f"ERROR: no existe {args.archivo}")
        sys.exit(1)

    print(f"Leyendo comunas desde {args.archivo} ...")
    gdf = gpd.read_file(args.archivo, engine="pyogrio")
    comunas = (
        gdf[["CUT", "COMUNA"]]
        .drop_duplicates()
        .sort_values("CUT")
    )
    print(f"  {len(comunas)} comunas encontradas.")

    from sqlalchemy import create_engine, text
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://sitd:sitd_dev_only@localhost:5432/sitd",
    )
    engine = create_engine(url)

    with engine.begin() as conn:
        for _, r in comunas.iterrows():
            conn.execute(text("""
                INSERT INTO comuna (codigo_comuna, nombre, codigo_region)
                VALUES (:cc, :nombre, '07')
                ON CONFLICT (codigo_comuna) DO UPDATE SET nombre = EXCLUDED.nombre
            """), {"cc": str(int(r["CUT"])), "nombre": r["COMUNA"]})

    print(f"  Tabla comuna poblada: {len(comunas)} filas.")


if __name__ == "__main__":
    main()
