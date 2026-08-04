"""
SITD — ETL CONAF (Fase II, Capa 1 - componente ambiental).

Dos responsabilidades:
  1. Cargar el catastro CONAF a la tabla conaf_uso_suelo (una fila por polígono).
  2. Calcular el cruce espacial unidad × CONAF y materializarlo en
     unidad_conaf (una fila por unidad × subuso, con área y fracción).

Diseño (ver diagrama del chat y docs/decisiones.md):
  - La unidad es el molde: recorta las coberturas CONAF (no al revés).
  - Se agrupa por SUBUSO (26 categorías) sumando todos los trozos del mismo
    tipo dentro de una unidad → una fila por (unidad, subuso).
  - Se descartan slivers menores al umbral (artefactos de borde).
  - Flag de bosque nativo derivado de SUBUSO == 'Bosque Nativo'.

Uso:
    python etl_conaf.py --shapefile /data/conaf_maule.shp --dry-run
    python etl_conaf.py --shapefile /data/conaf_maule.shp
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import geopandas as gpd
import pandas as pd
from shapely.validation import make_valid

CRS_OBJETIVO = 32719
CAMPO_CLASIFICACION = "SUBUSO"    # 26 categorías (nivel intermedio elegido)
SUBUSO_BOSQUE_NATIVO = "Bosque Nativo"

# --- Umbral adaptativo de slivers ---------------------------------------------
# Un trozo se descarta SOLO si cumple AMBAS condiciones:
#   (a) es menor a UMBRAL_SLIVER_M2, y
#   (b) representa menos de UMBRAL_FRACCION_MINIMA de la unidad.
# Motivo: un trozo de 50 m2 dentro de una entidad rural de 100 ha es un
# artefacto de borde; ese mismo trozo dentro de una unidad urbana de 59 m2
# es su suelo real. El umbral fijo eliminaba 209 unidades urbanas diminutas
# por completo (todas con 0 habitantes), rompiendo el 100% del OE1.
UMBRAL_SLIVER_M2 = 100.0
UMBRAL_FRACCION_MINIMA = 0.05     # 5% de la unidad


def log(msg: str) -> None:
    print(msg, flush=True)


def limpiar_geometrias(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Quita nulas/vacías y repara inválidas con make_valid."""
    n0 = len(gdf)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    invalidas = (~gdf.geometry.is_valid).sum()
    if invalidas:
        gdf["geometry"] = gdf.geometry.apply(
            lambda g: g if g.is_valid else make_valid(g)
        )
        # make_valid puede devolver colecciones; conservar solo (Multi)Polygon
        gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    log(f"  Geometrías: {n0} → {len(gdf)} ({invalidas} reparadas).")
    return gdf


def cargar_conaf(ruta: str) -> gpd.GeoDataFrame:
    log(f"Leyendo CONAF: {ruta}")
    gdf = gpd.read_file(ruta, engine="pyogrio")
    log(f"  {len(gdf)} polígonos, {len(gdf.columns)} columnas.")

    epsg = gdf.crs.to_epsg() if gdf.crs else None
    if epsg != CRS_OBJETIVO:
        log(f"  Reproyectando EPSG:{epsg} → EPSG:{CRS_OBJETIVO} ...")
        gdf = gdf.to_crs(epsg=CRS_OBJETIVO)
    else:
        log(f"  CRS OK: EPSG:{CRS_OBJETIVO}.")

    gdf = limpiar_geometrias(gdf)
    # Flag de bosque nativo, consistente y verificable
    gdf["es_bosque_nativo"] = gdf[CAMPO_CLASIFICACION] == SUBUSO_BOSQUE_NATIVO
    return gdf[[CAMPO_CLASIFICACION, "USO", "es_bosque_nativo", "geometry"]].copy()


def cargar_unidades_desde_bd():
    """Trae las unidades ya cargadas (por etl_censo.py) para el cruce."""
    from sqlalchemy import create_engine
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://sitd:sitd_dev_only@localhost:5432/sitd",
    )
    engine = create_engine(url)
    gdf = gpd.read_postgis(
        "SELECT id_unidad, geom FROM unidad_censal", engine, geom_col="geom"
    )
    log(f"  {len(gdf)} unidades leídas de la BD.")
    return gdf


def cargar_unidades_desde_gpkg(ruta_gpkg: str):
    """Alternativa para dry-run sin BD: lee unidades del gpkg original."""
    gdf = gpd.read_file(ruta_gpkg, engine="pyogrio")
    gdf["id_unidad"] = gdf["MANZENT"].apply(lambda v: str(int(round(float(v)))))
    return gdf[["id_unidad", "geometry"]].rename(columns={"geometry": "geom"}).set_geometry("geom")


def calcular_cruce(unidades: gpd.GeoDataFrame, conaf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Overlay espacial → agrupa por (unidad, subuso) → aplica umbral →
    calcula fracción de unidad. Devuelve el DataFrame listo para unidad_conaf."""
    log("Ejecutando overlay espacial (puede tardar varios minutos)...")
    t0 = time.time()

    unidades = unidades.rename_geometry("geometry")
    cruce = gpd.overlay(
        unidades[["id_unidad", "geometry"]],
        conaf[[CAMPO_CLASIFICACION, "es_bosque_nativo", "geometry"]],
        how="intersection",
        keep_geom_type=True,
    )
    cruce["area_m2"] = cruce.geometry.area
    log(f"  Overlay completo en {time.time()-t0:.1f}s: {len(cruce)} trozos brutos.")

    # Agrupar todos los trozos del mismo subuso dentro de cada unidad
    agrupado = (
        cruce.groupby(["id_unidad", CAMPO_CLASIFICACION], as_index=False)
        .agg(area_m2=("area_m2", "sum"),
             es_bosque_nativo=("es_bosque_nativo", "first"))
    )
    n_antes = len(agrupado)

    # Fracción provisional (antes del filtro) para evaluar el criterio adaptativo
    area_total_prev = agrupado.groupby("id_unidad")["area_m2"].transform("sum")
    frac_prev = agrupado["area_m2"] / area_total_prev

    # Umbral ADAPTATIVO: descarta solo si es pequeño EN ABSOLUTO y EN RELATIVO
    es_sliver = (agrupado["area_m2"] < UMBRAL_SLIVER_M2) & (frac_prev < UMBRAL_FRACCION_MINIMA)
    agrupado = agrupado[~es_sliver].copy()
    log(f"  Agrupado por subuso: {n_antes} filas → {len(agrupado)} "
        f"tras umbral adaptativo (<{UMBRAL_SLIVER_M2:.0f} m² Y "
        f"<{UMBRAL_FRACCION_MINIMA:.0%} de la unidad).")

    # Fracción definitiva respecto al área total cruzada de la unidad
    area_total = agrupado.groupby("id_unidad")["area_m2"].transform("sum")
    agrupado["fraccion_unidad"] = (agrupado["area_m2"] / area_total).round(4)

    return agrupado.rename(columns={CAMPO_CLASIFICACION: "subuso"})


def main():
    parser = argparse.ArgumentParser(description="ETL CONAF + cruce espacial (SITD)")
    parser.add_argument("--shapefile", required=True, help="Ruta al .shp de CONAF")
    parser.add_argument("--unidades-gpkg", help="(dry-run) gpkg de unidades si no hay BD")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--salida-csv")
    args = parser.parse_args()

    if not os.path.exists(args.shapefile):
        log(f"ERROR: no existe {args.shapefile}")
        sys.exit(1)

    conaf = cargar_conaf(args.shapefile)

    if args.unidades_gpkg:
        unidades = cargar_unidades_desde_gpkg(args.unidades_gpkg)
        log(f"  {len(unidades)} unidades leídas del gpkg (modo dry-run).")
    else:
        unidades = cargar_unidades_desde_bd()

    cruce = calcular_cruce(unidades, conaf)

    # Verificación de integridad (soporte OE1)
    n_mz_entrada = unidades["id_unidad"].nunique()
    n_mz_con_suelo = cruce["id_unidad"].nunique()
    log("\nVERIFICACIÓN OE1 (integración espacial):")
    log(f"  Unidades de entrada:          {n_mz_entrada}")
    log(f"  Unidades con cobertura:     {n_mz_con_suelo}")
    log(f"  Unidades sin cobertura:     {n_mz_entrada - n_mz_con_suelo}")
    log(f"  Total filas unidad_conaf:  {len(cruce)}")
    log(f"  Superficie total cruzada:   {cruce['area_m2'].sum()/1e6:,.1f} km²")
    log(f"  Filas de bosque nativo:     {cruce['es_bosque_nativo'].sum()}")

    if args.dry_run:
        log("\n[dry-run] No se carga a la BD.")
        if args.salida_csv:
            cruce.to_csv(args.salida_csv, index=False)
            log(f"  Guardado en {args.salida_csv}")
        return

    cargar_cruce_a_bd(cruce)


def cargar_cruce_a_bd(cruce):
    """Carga el cruce agregado en unidad_conaf (una fila por unidad × subuso)."""
    from sqlalchemy import create_engine, text
    url = os.getenv("DATABASE_URL",
                    "postgresql+psycopg://sitd:sitd_dev_only@localhost:5432/sitd")
    engine = create_engine(url)
    log("\nCargando a la BD...")

    registros = cruce.to_dict("records")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE unidad_conaf;"))
        # Inserción por lotes: mucho más rápido que fila por fila
        conn.execute(text("""
            INSERT INTO unidad_conaf
                (id_unidad, subuso, es_bosque_nativo, area_m2, fraccion_unidad)
            VALUES (:id_unidad, :subuso, :es_bosque_nativo, :area_m2, :fraccion_unidad)
            ON CONFLICT (id_unidad, subuso) DO UPDATE
                SET area_m2 = EXCLUDED.area_m2,
                    fraccion_unidad = EXCLUDED.fraccion_unidad
        """), [
            {
                "id_unidad": r["id_unidad"],
                "subuso": r["subuso"],
                "es_bosque_nativo": bool(r["es_bosque_nativo"]),
                "area_m2": float(r["area_m2"]),
                "fraccion_unidad": float(r["fraccion_unidad"]),
            }
            for r in registros
        ])
    log(f"  Cargadas {len(cruce)} filas en unidad_conaf.")


if __name__ == "__main__":
    main()
