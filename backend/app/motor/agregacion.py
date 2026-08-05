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
            SELECT id_unidad, poblacion_total, total_hogares,
                   total_viviendas, atributos_extra
            FROM unidad_censal
            WHERE ST_Within(
                centroide,
                ST_GeomFromText(:wkt, 32719)
            )
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

    return {
        "n_unidades": n_unidades,
        "poblacion_total": totales["n_per"],
        "hogares_total": totales["n_hog"],
        "viviendas_total": totales["n_vp"],
        "indicadores": indicadores,
        "uso_suelo": uso_suelo,
        "superficie_total_ha": round(total_ha, 2),
        "duracion_ms": round((time.perf_counter() - t0) * 1000, 1),
    }
