"""
SITD — ETL Censo 2024 (Fase II, Capa 1 de ingesta).

Flujo:
  1. Lee el GeoPackage del INE (ya unificado y en EPSG:32719).
  2. Verifica CRS (bloqueante si no es 32719) y valida topología.
  3. Recorta columnas según el catálogo, normaliza identificadores.
  4. Arma el JSONB de atributos por dimensión (respetando secreto estadístico).
  5. Carga a PostgreSQL/PostGIS y deja traza en etl_log.

Uso:
    python etl_censo.py --archivo /data/maule_base_censal_unificada_32719.gpkg
    python etl_censo.py --archivo ... --dry-run   # valida sin cargar

Requiere las variables del entorno del proyecto (DATABASE_URL) o el default local.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import geopandas as gpd
import pandas as pd
from shapely.validation import explain_validity, make_valid

from catalogo import (
    COLUMNAS_JSONB_POR_DIMENSION,
    COLUMNAS_PRIMERA_CLASE,
    COLUMNAS_SECRETO_ESTADISTICO,
    todas_las_columnas_a_cargar,
)

CRS_OBJETIVO = 32719
UMBRAL_POBLACION_REIDENTIFICACION = 5  # Ley 21.719: 1-4 personas = riesgo


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def log(msg: str) -> None:
    print(msg, flush=True)


def normalizar_id_unidad(valor) -> str | None:
    """MANZENT viene como float (7103011001002.0). Lo pasamos a texto entero
    sin decimales ni notación científica. Un identificador jamás es float."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return None
    try:
        return str(int(round(float(valor))))
    except (ValueError, TypeError):
        return str(valor).strip()


def a_int_o_none(valor):
    """Conteos: entero, o None si es nulo (secreto estadístico / sin dato).
    NO convierte nulos a 0 (eso falsearía datos protegidos)."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return None
    return int(round(float(valor)))


# ---------------------------------------------------------------------------
# Pasos del ETL
# ---------------------------------------------------------------------------
def leer_y_verificar(ruta: str) -> gpd.GeoDataFrame:
    log(f"Leyendo {ruta} ...")
    gdf = gpd.read_file(ruta, engine="pyogrio")
    log(f"  {len(gdf)} filas, {len(gdf.columns)} columnas.")

    # CRS — bloqueante (riesgo del plan de gestión)
    epsg = gdf.crs.to_epsg() if gdf.crs else None
    if epsg != CRS_OBJETIVO:
        log(f"  CRS actual EPSG:{epsg}, reproyectando a EPSG:{CRS_OBJETIVO} ...")
        gdf = gdf.to_crs(epsg=CRS_OBJETIVO)
    else:
        log(f"  CRS OK: EPSG:{CRS_OBJETIVO}.")

    # Verificar que existan las columnas esperadas
    faltantes = [c for c in todas_las_columnas_a_cargar() if c not in gdf.columns]
    if faltantes:
        log(f"  ADVERTENCIA: columnas ausentes en el origen: {faltantes}")
    return gdf


def validar_topologia(gdf: gpd.GeoDataFrame):
    """Devuelve (gdf_valido, registros_log). Repara geometrías inválidas con
    make_valid; si tras reparar sigue vacía/nula, se rechaza."""
    validos, rechazos = [], []
    reparadas = 0
    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            rechazos.append({"idx": idx, "causa": "geometría nula o vacía"})
            continue
        if not geom.is_valid:
            causa = explain_validity(geom)
            geom = make_valid(geom)
            if geom.is_empty or geom.geom_type not in ("Polygon", "MultiPolygon"):
                rechazos.append({"idx": idx, "causa": f"irreparable: {causa}"})
                continue
            gdf.at[idx, "geometry"] = geom
            reparadas += 1
        validos.append(idx)
    log(f"  Topología: {len(validos)} válidas, {reparadas} reparadas, "
        f"{len(rechazos)} rechazadas.")
    return gdf.loc[validos].copy(), rechazos


def transformar(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Aplica recorte de columnas, normaliza IDs, arma JSONB por dimensión y
    marca celdas de baja frecuencia (Ley 21.719)."""
    filas = []
    n_baja_frecuencia = 0

    for _, row in gdf.iterrows():
        pob = a_int_o_none(row.get("n_per"))

        # Chequeo de reidentificación: 1-4 personas
        baja_frecuencia = pob is not None and 0 < pob < UMBRAL_POBLACION_REIDENTIFICACION
        if baja_frecuencia:
            n_baja_frecuencia += 1

        # JSONB por dimensión (solo conteos, nulos preservados)
        extra = {}
        for dim, cols in COLUMNAS_JSONB_POR_DIMENSION.items():
            extra[dim] = {c: a_int_o_none(row.get(c)) for c in cols if c in row}
        # Secreto estadístico: en su propio grupo, marcado
        extra["protegido_secreto_estadistico"] = {
            c: a_int_o_none(row.get(c)) for c in COLUMNAS_SECRETO_ESTADISTICO if c in row
        }
        if baja_frecuencia:
            extra["_flag_baja_frecuencia"] = True

        filas.append({
            "id_unidad": normalizar_id_unidad(row.get("MANZENT")),
            "codigo_comuna": str(a_int_o_none(row.get("CUT"))),
            "nombre_comuna": row.get("COMUNA"),
            "area_tipo": row.get("AREA_C"),
            "poblacion_total": pob if pob is not None else 0,
            "total_hogares": a_int_o_none(row.get("n_hog")) or 0,
            "total_viviendas": a_int_o_none(row.get("n_vp")) or 0,
            "atributos_extra": json.dumps(extra, ensure_ascii=False),
            "geom_wkt": row.geometry.wkt,
        })

    log(f"  Transformadas {len(filas)} filas. "
        f"Celdas de baja frecuencia marcadas (Ley 21.719): {n_baja_frecuencia}.")
    return pd.DataFrame(filas)


def main():
    parser = argparse.ArgumentParser(description="ETL Censo 2024 -> PostGIS (SITD)")
    parser.add_argument("--archivo", required=True, help="Ruta al .gpkg del INE")
    parser.add_argument("--dry-run", action="store_true",
                        help="Valida y transforma sin cargar a la BD")
    parser.add_argument("--salida-csv", help="(dry-run) guarda el resultado a CSV")
    args = parser.parse_args()

    if not os.path.exists(args.archivo):
        log(f"ERROR: no existe el archivo {args.archivo}")
        sys.exit(1)

    gdf = leer_y_verificar(args.archivo)
    gdf, rechazos = validar_topologia(gdf)
    df = transformar(gdf)

    # Verificación de integridad: IDs únicos y no nulos
    n_dup = df["id_unidad"].duplicated().sum()
    n_nulos = df["id_unidad"].isna().sum()
    log(f"  Integridad IDs: {n_dup} duplicados, {n_nulos} nulos.")

    # Totales de control (deben cuadrar con cifras oficiales -> soporte OE2)
    log("\nTOTALES DE CONTROL (Región del Maule):")
    log(f"  Población: {df['poblacion_total'].sum():,}")
    log(f"  Hogares:   {df['total_hogares'].sum():,}")
    log(f"  Viviendas: {df['total_viviendas'].sum():,}")

    if args.dry_run:
        log("\n[dry-run] No se carga a la BD.")
        if args.salida_csv:
            df.drop(columns=["geom_wkt"]).to_csv(args.salida_csv, index=False)
            log(f"  Resultado guardado en {args.salida_csv}")
        return

    cargar_a_postgis(df, rechazos)


def cargar_a_postgis(df: pd.DataFrame, rechazos: list):
    """Carga a PostGIS usando SQLAlchemy. Import diferido para permitir
    dry-run sin dependencias de BD."""
    from sqlalchemy import create_engine, text

    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://sitd:sitd_dev_only@localhost:5432/sitd",
    )
    engine = create_engine(url)
    log(f"\nCargando a la BD ...")

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE unidad_censal CASCADE;"))
        for _, r in df.iterrows():
            conn.execute(text("""
                INSERT INTO unidad_censal
                    (id_unidad, codigo_comuna, nombre_comuna, area_tipo,
                     poblacion_total, total_hogares, total_viviendas,
                     atributos_extra, geom)
                VALUES
                    (:id, :cc, :nom, :area, :pob, :hog, :viv,
                     CAST(:extra AS jsonb),
                     ST_Multi(ST_GeomFromText(:wkt, 32719)))
                ON CONFLICT (id_unidad) DO NOTHING
            """), {
                "id": r["id_unidad"], "cc": r["codigo_comuna"],
                "nom": r["nombre_comuna"], "area": r["area_tipo"],
                "pob": r["poblacion_total"], "hog": r["total_hogares"],
                "viv": r["total_viviendas"],
                "extra": r["atributos_extra"], "wkt": r["geom_wkt"],
            })
        # Log de rechazos
        for rej in rechazos:
            conn.execute(text("""
                INSERT INTO etl_log (fuente, id_origen, resultado, causa)
                VALUES ('INE', :id, 'rechazado', :causa)
            """), {"id": str(rej["idx"]), "causa": rej["causa"]})

    log(f"  Carga completa: {len(df)} unidades, {len(rechazos)} rechazos logueados.")


if __name__ == "__main__":
    main()
