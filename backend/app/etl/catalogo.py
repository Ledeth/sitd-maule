"""
Catálogo de indicadores y mapeo de columnas del SITD (Fase II).

Este módulo es la ÚNICA fuente de verdad sobre:
  1. Qué columnas del .gpkg del INE se cargan y a qué campo van.
  2. Qué indicadores derivados calcula el sistema y con qué fórmula.

Regla de oro (ver docs/decisiones.md):
  - Las columnas base (conteos n_*) SÍ se suman entre manzanas.
  - Los indicadores derivados (%, índices) NO se suman: se calculan SOBRE
    los totales ya agregados del área ad-hoc. Por eso aquí se definen como
    fórmulas, no como columnas almacenadas.
"""

# ---------------------------------------------------------------------------
# 1. MAPEO DE COLUMNAS: origen (.gpkg INE) -> destino (PostGIS)
# ---------------------------------------------------------------------------

# Identificadores y totales -> columnas de PRIMERA CLASE en unidad_censal.
COLUMNAS_PRIMERA_CLASE = {
    "MANZENT": "id_unidad",        # se castea a texto (viene como float en el origen)
    "CUT": "codigo_comuna",
    "COMUNA": "nombre_comuna",
    "AREA_C": "area_tipo",          # URBANO / RURAL
    "n_per": "poblacion_total",
    "n_hog": "total_hogares",
    "n_vp": "total_viviendas",
}

# Columnas base que alimentan indicadores -> van al JSONB atributos_extra,
# agrupadas por dimensión. Solo conteos (n_*), que sí son sumables.
COLUMNAS_JSONB_POR_DIMENSION = {
    "demografia": [
        "n_hombres", "n_mujeres",
        "n_edad_0_5", "n_edad_6_13", "n_edad_14_17",
        "n_edad_18_24", "n_edad_25_44", "n_edad_45_59", "n_edad_60_mas",
    ],
    "vulnerabilidad": [
        "n_discapacidad", "n_analfabet",
        "n_ocupado", "n_desocupado", "n_fuera_fuerza_trabajo",
        "n_jefatura_mujer",
    ],
    "habitacional": [
        "n_viv_hacinadas", "n_deficit_cuantitativo", "n_viv_irrecuperables",
    ],
    "servicios": [
        "n_internet",
        "n_fuente_agua_publica", "n_fuente_agua_pozo", "n_fuente_agua_rio",
        "n_serv_hig_alc_dentro",
        "n_fuente_elect_publica", "n_fuente_elect_no_tiene",
    ],
    "ambiental": [
        "n_comb_calefaccion_lena", "n_comb_cocina_lena",
    ],
}

# Columnas con SECRETO ESTADÍSTICO del INE (nulos = dato suprimido por baja
# frecuencia, Ley 21.719). No se rellenan con 0; se cargan como null honesto.
COLUMNAS_SECRETO_ESTADISTICO = ["n_inmigrantes", "n_pueblos_orig"]


def todas_las_columnas_a_cargar():
    """Lista plana de columnas del .gpkg que el ETL debe conservar."""
    cols = list(COLUMNAS_PRIMERA_CLASE.keys())
    for grupo in COLUMNAS_JSONB_POR_DIMENSION.values():
        cols.extend(grupo)
    cols.extend(COLUMNAS_SECRETO_ESTADISTICO)
    return cols


# ---------------------------------------------------------------------------
# 2. CATÁLOGO DE INDICADORES DERIVADOS
#    Cada indicador se calcula sobre TOTALES AGREGADOS de un área.
#    'formula' recibe un dict de sumas y devuelve el valor (o None si no aplica).
# ---------------------------------------------------------------------------

def _pct(num, den):
    """Porcentaje seguro: None si el denominador es 0 (evita div/0)."""
    return round(100 * num / den, 2) if den and den > 0 else None


INDICADORES = {
    # --- Demografía ---
    "indice_dependencia": {
        "dimension": "demografia",
        "etiqueta": "Índice de dependencia demográfica (%)",
        "descripcion": "(<18 + 60 y más) / población en edad activa (18-59), en %.",
        "formula": lambda t: _pct(
            t["n_edad_0_5"] + t["n_edad_6_13"] + t["n_edad_14_17"] + t["n_edad_60_mas"],
            t["n_edad_18_24"] + t["n_edad_25_44"] + t["n_edad_45_59"],
        ),
    },
    "pct_adulto_mayor": {
        "dimension": "demografia",
        "etiqueta": "Población adulto mayor (60+) (%)",
        "descripcion": "Personas de 60 o más sobre población total.",
        "formula": lambda t: _pct(t["n_edad_60_mas"], t["n_per"]),
    },
    # --- Vulnerabilidad ---
    "tasa_analfabetismo": {
        "dimension": "vulnerabilidad",
        "etiqueta": "Tasa de analfabetismo (%)",
        "descripcion": "Personas analfabetas sobre población total.",
        "formula": lambda t: _pct(t["n_analfabet"], t["n_per"]),
    },
    "tasa_desocupacion": {
        "dimension": "vulnerabilidad",
        "etiqueta": "Tasa de desocupación (%)",
        "descripcion": "Desocupados sobre fuerza de trabajo (ocupados + desocupados).",
        "formula": lambda t: _pct(t["n_desocupado"], t["n_ocupado"] + t["n_desocupado"]),
    },
    "pct_jefatura_femenina": {
        "dimension": "vulnerabilidad",
        "etiqueta": "Hogares con jefatura femenina (%)",
        "descripcion": "Hogares con jefa mujer sobre total de hogares.",
        "formula": lambda t: _pct(t["n_jefatura_mujer"], t["n_hog"]),
    },
    # --- Habitacional ---
    "tasa_hacinamiento": {
        "dimension": "habitacional",
        "etiqueta": "Viviendas hacinadas (%)",
        "descripcion": "Viviendas hacinadas sobre total de viviendas.",
        "formula": lambda t: _pct(t["n_viv_hacinadas"], t["n_vp"]),
    },
    "deficit_cuantitativo_abs": {
        "dimension": "habitacional",
        "etiqueta": "Déficit habitacional cuantitativo (viviendas)",
        "descripcion": "Suma absoluta del déficit cuantitativo en el área.",
        "formula": lambda t: int(t["n_deficit_cuantitativo"]),
    },
    # --- Servicios ---
    "pct_sin_alcantarillado": {
        "dimension": "servicios",
        "etiqueta": "Hogares sin alcantarillado (%)",
        "descripcion": "Hogares sin conexión de alcantarillado dentro de la vivienda.",
        "formula": lambda t: _pct(t["n_hog"] - t["n_serv_hig_alc_dentro"], t["n_hog"]),
    },
    "pct_sin_internet": {
        "dimension": "servicios",
        "etiqueta": "Hogares sin internet (%)",
        "descripcion": "Hogares sin acceso a internet sobre total de hogares.",
        "formula": lambda t: _pct(t["n_hog"] - t["n_internet"], t["n_hog"]),
    },
    # --- Ambiental ---
    "pct_calefaccion_lena": {
        "dimension": "ambiental",
        "etiqueta": "Hogares que calefaccionan con leña (%)",
        "descripcion": "Relevante para calidad del aire y presión sobre bosque nativo.",
        "formula": lambda t: _pct(t["n_comb_calefaccion_lena"], t["n_hog"]),
    },
    "pct_agua_no_formal": {
        "dimension": "ambiental",
        "etiqueta": "Hogares con fuente de agua no formal (%)",
        "descripcion": "Abastecimiento por pozo o río sobre total de hogares.",
        "formula": lambda t: _pct(
            t["n_fuente_agua_pozo"] + t["n_fuente_agua_rio"], t["n_hog"]
        ),
    },
}
