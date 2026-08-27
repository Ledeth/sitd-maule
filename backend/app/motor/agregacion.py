"""
SITD — Motor de agregación elástica (Fase III, Capa 2).

Núcleo analítico del sistema. Recibe un polígono ad-hoc (dibujado por el
usuario, en coordenadas EPSG:32719) y devuelve un informe territorial:

  1. Selecciona las unidades censales cuyo CENTROIDE cae dentro del polígono
     (regla de indivisibilidad — ADR-001 — garantiza exactitud del OE2).
  2. Suma los conteos base (población, hogares, viviendas + conteos del JSONB).
  3. Calcula los indicadores derivados del catálogo sobre esos totales.
  4. Agrega el uso de suelo (hectáreas por subuso) desde unidad_conaf.
  5. Mide el tiempo de respuesta (evidencia empírica del OE2).

La selección por centroide se apoya en el índice GIST idx_unidad_centroide,
de modo que la consulta responde en milisegundos aun sobre toda la región.
"""
from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.etl.catalogo import INDICADORES, COLUMNAS_JSONB_POR_DIMENSION

# Las geometrías se simplifican antes de enviarlas al navegador. La tolerancia
# es ADAPTATIVA: mientras más unidades tenga la selección, más agresiva es la
# simplificación, porque a mayor extensión el usuario está viendo el mapa más
# alejado y el detalle fino es imperceptible. Así se mantiene el peso de la
# respuesta acotado sin dejar de resaltar las unidades.
def tolerancia_para(n_unidades: int) -> float:
    if n_unidades <= 500:
        return 5.0      # detalle urbano fino
    if n_unidades <= 2000:
        return 15.0
    if n_unidades <= 6000:
        return 40.0
    return 80.0         # vista regional

# Tope duro: por encima de esto ni siquiera la simplificación agresiva evita
# una respuesta inmanejable para el navegador. Se devuelven los atributos, sin
# geometrías, y se informa con la bandera 'geometrias_omitidas'.
LIMITE_GEOMETRIAS = 15000


def _sumar_conteos_jsonb(filas_extra: list[dict]) -> dict[str, int]:
    """Suma los conteos del JSONB de todas las unidades seleccionadas.
    Preserva la semántica de nulos: si TODAS las unidades tienen null en un
    campo (secreto estadístico), el total queda en None; si algunas tienen
    valor, suma solo las que lo tienen."""
    totales: dict[str, Any] = {}
    vistos_con_valor: set[str] = set()

    for extra in filas_extra:
        for dimension, conteos in extra.items():
            if not isinstance(conteos, dict):
                continue
            for campo, valor in conteos.items():
                if valor is None:
                    totales.setdefault(campo, 0)
                else:
                    totales[campo] = totales.get(campo, 0) + valor
                    vistos_con_valor.add(campo)

    # Campos que nunca tuvieron un valor real -> None (dato protegido/ausente)
    for campo in list(totales.keys()):
        if campo not in vistos_con_valor:
            totales[campo] = None
    return totales


def agregar_por_poligono(engine: Engine, poligono_wkt: str) -> dict[str, Any]:
    """Ejecuta la agregación elástica sobre un polígono ad-hoc (WKT, EPSG:32719).

    Devuelve un dict con: totales base, indicadores derivados, composición de
    uso de suelo, número de unidades y duración en ms.
    """
    t0 = time.perf_counter()

    with engine.connect() as conn:
        # --- 1 y 2. Seleccionar unidades por centroide y traer sus datos ---
        filas = conn.execute(text("""
            SELECT id_unidad, nombre_comuna, area_tipo,
                   poblacion_total, total_hogares,
                   total_viviendas, atributos_extra,
                   ROUND((ST_Area(geom) / 10000)::numeric, 2) AS hectareas
            FROM unidad_censal
            WHERE ST_Within(
                centroide,
                ST_GeomFromText(:wkt, 32719)
            )
            ORDER BY poblacion_total DESC
        """), {"wkt": poligono_wkt}).mappings().all()

        n_unidades = len(filas)

        if n_unidades == 0:
            return {
                "n_unidades": 0,
                "mensaje": "El polígono no contiene el centroide de ninguna unidad.",
                "duracion_ms": round((time.perf_counter() - t0) * 1000, 1),
            }

        # Totales base (siempre sumables)
        totales = {
            "n_per": sum(f["poblacion_total"] for f in filas),
            "n_hog": sum(f["total_hogares"] for f in filas),
            "n_vp": sum(f["total_viviendas"] for f in filas),
        }

        # Totales de los conteos del JSONB (por dimensión)
        extras = [
            f["atributos_extra"] if isinstance(f["atributos_extra"], dict)
            else json.loads(f["atributos_extra"])
            for f in filas
        ]
        totales.update(_sumar_conteos_jsonb(extras))

        # --- 4. Uso de suelo: sumar hectáreas por subuso ---
        ids = [f["id_unidad"] for f in filas]
        suelo_rows = conn.execute(text("""
            SELECT subuso,
                   SUM(area_m2) / 10000.0 AS hectareas,
                   bool_or(es_bosque_nativo) AS es_bosque_nativo
            FROM unidad_conaf
            WHERE id_unidad = ANY(:ids)
            GROUP BY subuso
            ORDER BY hectareas DESC
        """), {"ids": ids}).mappings().all()

    # --- 3. Calcular indicadores derivados sobre los totales agregados ---
    indicadores = {}
    for clave, ind in INDICADORES.items():
        try:
            valor = ind["formula"](totales)
        except (KeyError, TypeError, ZeroDivisionError):
            valor = None
        indicadores[clave] = {
            "etiqueta": ind["etiqueta"],
            "dimension": ind["dimension"],
            "valor": valor,
        }

    # Composición de uso de suelo
    total_ha = sum(r["hectareas"] for r in suelo_rows) or 1.0
    uso_suelo = [
        {
            "subuso": r["subuso"],
            "hectareas": round(r["hectareas"], 2),
            "porcentaje": round(100 * r["hectareas"] / total_ha, 1),
            "es_bosque_nativo": r["es_bosque_nativo"],
        }
        for r in suelo_rows
    ]

    # --- 5. Unidades seleccionadas: atributos para la tabla y geometrías
    #        para resaltarlas en el mapa (ADR-001: el usuario debe VER qué
    #        unidades se agregaron, no solo el polígono que dibujó). ---
    omitir_geometrias = n_unidades > LIMITE_GEOMETRIAS

    unidades = [
        {
            "id_unidad": f["id_unidad"],
            "comuna": f["nombre_comuna"],
            "tipo": f["area_tipo"],
            "poblacion": f["poblacion_total"],
            "hogares": f["total_hogares"],
            "viviendas": f["total_viviendas"],
            "hectareas": float(f["hectareas"]) if f["hectareas"] is not None else None,
        }
        for f in filas
    ]

    geojson = None
    if not omitir_geometrias:
        # Segunda consulta, solo geometrías, con la tolerancia adecuada al
        # tamaño de la selección. Separarla mantiene liviana la consulta de
        # atributos y permite elegir la tolerancia ya conociendo n_unidades.
        tol = tolerancia_para(n_unidades)
        with engine.connect() as conn:
            geoms = conn.execute(text("""
                SELECT id_unidad,
                       ST_AsGeoJSON(
                           ST_Transform(
                               ST_SimplifyPreserveTopology(geom, :tol), 4326
                           ), 5
                       ) AS gj
                FROM unidad_censal
                WHERE ST_Within(centroide, ST_GeomFromText(:wkt, 32719))
            """), {"wkt": poligono_wkt, "tol": tol}).mappings().all()

        atributos = {f["id_unidad"]: f for f in filas}
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(g["gj"]),
                    "properties": {
                        "id_unidad": g["id_unidad"],
                        "comuna": atributos[g["id_unidad"]]["nombre_comuna"],
                        "tipo": atributos[g["id_unidad"]]["area_tipo"],
                        "poblacion": atributos[g["id_unidad"]]["poblacion_total"],
                        "hogares": atributos[g["id_unidad"]]["total_hogares"],
                        "viviendas": atributos[g["id_unidad"]]["total_viviendas"],
                    },
                }
                for g in geoms
                if g["gj"] and g["id_unidad"] in atributos
            ],
        }

    return {
        "n_unidades": n_unidades,
        "poblacion_total": totales["n_per"],
        "hogares_total": totales["n_hog"],
        "viviendas_total": totales["n_vp"],
        "indicadores": indicadores,
        "uso_suelo": uso_suelo,
        "superficie_total_ha": round(total_ha, 2),
        "unidades": unidades,
        "geojson": geojson,
        "geometrias_omitidas": omitir_geometrias,
        "duracion_ms": round((time.perf_counter() - t0) * 1000, 1),
    }
