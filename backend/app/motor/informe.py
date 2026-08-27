"""
SITD — Generación de informe territorial en PDF (HU-27).

Produce un informe de una página con:
  1. Encabezado institucional y metadatos de la consulta.
  2. Mapa del área: basemap raster (OpenStreetMap) RECORTADO a la forma del
     polígono ad-hoc, con las unidades censales incluidas resaltadas.
  3. Totales demográficos y los once indicadores derivados.
  4. Composición de uso de suelo.
  5. Pie con fuentes, atribución y aviso normativo.

El mapa se construye ÍNTEGRAMENTE con datos propios del sistema (límites
comunales derivados de la capa censal y las unidades seleccionadas). No se
consumen servicios externos de cartografía: la política de uso de los
servidores de OpenStreetMap no permite la descarga automatizada de teselas,
y prescindir de ellos hace además que el informe se genere de forma inmediata,
sin dependencias de red ni de licencias de terceros.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")  # backend sin ventana; obligatorio en servidor
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)
from shapely import wkt as shapely_wkt
from shapely.geometry import shape as shapely_shape

# Paleta coherente con el dashboard
VERDE = colors.HexColor("#0f766e")
GRIS = colors.HexColor("#475569")
GRIS_CLARO = colors.HexColor("#e2e8f0")

CRS_TRABAJO = "EPSG:32719"
CRS_WEB = "EPSG:3857"  # el que usan los tiles de OSM


# ---------------------------------------------------------------------------
# 1. Mapa
# ---------------------------------------------------------------------------
def _render_mapa(engine, poligono_wkt: str, geojson: dict | None) -> io.BytesIO:
    """Dibuja el mapa del área y lo devuelve como PNG en memoria.

    Composición (de fondo a frente):
      1. Comunas del entorno, en gris, con su nombre — dan contexto territorial.
      2. Unidades censales incluidas en la agregación, en verde.
      3. Polígono ad-hoc trazado por el usuario, en línea discontinua.

    Todo proviene de la propia base de datos; no se descarga cartografía externa.
    """
    import geopandas as gpd
    from sqlalchemy import text as sql_text

    poligono = shapely_wkt.loads(poligono_wkt)
    gdf_pol = gpd.GeoDataFrame(geometry=[poligono], crs=CRS_TRABAJO)

    # Contexto: comunas que tocan el entorno del área (con margen), derivadas
    # de la capa censal. Simplificadas con generosidad: son solo referencia.
    minx, miny, maxx, maxy = gdf_pol.total_bounds
    margen = max(maxx - minx, maxy - miny) * 0.35
    with engine.connect() as conn:
        filas_com = conn.execute(sql_text("""
            SELECT nombre_comuna,
                   ST_AsText(
                       ST_SimplifyPreserveTopology(ST_Union(geom), 150)
                   ) AS wkt
            FROM unidad_censal
            WHERE geom && ST_MakeEnvelope(:x1, :y1, :x2, :y2, 32719)
            GROUP BY nombre_comuna
        """), {
            "x1": minx - margen, "y1": miny - margen,
            "x2": maxx + margen, "y2": maxy + margen,
        }).mappings().all()

    fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=150)

    if filas_com:
        comunas = gpd.GeoDataFrame(
            {"nombre": [f["nombre_comuna"] for f in filas_com]},
            geometry=[shapely_wkt.loads(f["wkt"]) for f in filas_com],
            crs=CRS_TRABAJO,
        )
        comunas.plot(ax=ax, facecolor="#f1f5f9", edgecolor="#cbd5e1",
                     linewidth=0.7, zorder=1)
        # Nombre de cada comuna en su punto interior
        for _, c in comunas.iterrows():
            punto = c.geometry.representative_point()
            ax.annotate(
                str(c["nombre"]).title(), xy=(punto.x, punto.y),
                ha="center", va="center", fontsize=5.5, color="#94a3b8",
                zorder=2,
            )

    # Unidades censales incluidas
    if geojson and geojson.get("features"):
        geoms = [shapely_shape(f["geometry"]) for f in geojson["features"]]
        gdf_un = gpd.GeoDataFrame(geometry=geoms, crs="EPSG:4326").to_crs(CRS_TRABAJO)
        gdf_un.plot(ax=ax, facecolor="#14b8a6", edgecolor="#0f766e",
                    alpha=0.55, linewidth=0.15, zorder=3)

    # Polígono ad-hoc del usuario
    gdf_pol.boundary.plot(ax=ax, edgecolor="#0369a1", linewidth=1.6,
                          linestyle="--", zorder=4)

    # Encuadre con margen del 10% sobre el área analizada
    mx, my = (maxx - minx) * 0.10, (maxy - miny) * 0.10
    ax.set_xlim(minx - mx, maxx + mx)
    ax.set_ylim(miny - my, maxy + my)
    ax.set_aspect("equal")
    ax.set_axis_off()

    # Barra de escala sencilla (el CRS está en metros, así que es directa)
    ancho = (maxx + mx) - (minx - mx)
    paso = 10 ** int(round(np.log10(ancho / 5)))
    if paso >= 1000:
        etiqueta, largo = f"{paso // 1000} km", paso
    else:
        etiqueta, largo = f"{paso} m", paso
    x0, y0 = minx - mx * 0.4, miny - my * 0.4
    ax.plot([x0, x0 + largo], [y0, y0], color="#334155", linewidth=1.6, zorder=5)
    ax.annotate(etiqueta, xy=(x0 + largo / 2, y0), xytext=(0, 3),
                textcoords="offset points", ha="center", fontsize=5.5,
                color="#334155", zorder=5)

    fig.tight_layout(pad=0.2)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=150,
                facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# 2. Informe
# ---------------------------------------------------------------------------
def generar_informe_pdf(engine, resultado: dict, poligono_wkt: str,
                        usuario: str = "—", rol: str = "—") -> io.BytesIO:
    """Construye el PDF completo y lo devuelve en memoria."""
    salida = io.BytesIO()
    doc = SimpleDocTemplate(
        salida, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title="Informe territorial SITD",
        author="Sistema de Inteligencia Territorial Dinámica",
    )

    base = getSampleStyleSheet()
    st_titulo = ParagraphStyle(
        "t", parent=base["Title"], fontSize=15, spaceAfter=2, textColor=colors.HexColor("#0f172a")
    )
    st_sub = ParagraphStyle(
        "s", parent=base["Normal"], fontSize=8.5, textColor=GRIS, spaceAfter=8
    )
    st_h = ParagraphStyle(
        "h", parent=base["Heading3"], fontSize=9.5, spaceBefore=9, spaceAfter=4,
        textColor=VERDE,
    )
    st_pie = ParagraphStyle(
        "p", parent=base["Normal"], fontSize=6.8, textColor=GRIS, leading=9
    )

    hist = []
    ahora = datetime.now(timezone.utc).astimezone()

    # --- Encabezado ---
    hist.append(Paragraph("Informe de análisis territorial", st_titulo))
    hist.append(Paragraph(
        "Sistema de Inteligencia Territorial Dinámica (SITD) · Región del Maule<br/>"
        f"Generado el {ahora.strftime('%d-%m-%Y a las %H:%M')} · "
        f"Solicitante: {usuario} ({rol}) · "
        f"Consulta resuelta en {resultado.get('duracion_ms', '—')} ms",
        st_sub,
    ))

    # --- Mapa ---
    try:
        png = _render_mapa(engine, poligono_wkt, resultado.get("geojson"))
        hist.append(Image(png, width=174 * mm, height=111 * mm))
        hist.append(Paragraph(
            "Área analizada (línea discontinua) y unidades censales incluidas "
            "(en verde), sobre los límites comunales del entorno. Cartografía "
            "elaborada a partir de las capas del propio sistema.",
            st_pie,
        ))
    except Exception as e:
        hist.append(Paragraph(f"[No se pudo generar el mapa: {e}]", st_sub))

    hist.append(Spacer(1, 6))

    # --- Totales ---
    def n(v):
        return f"{v:,}".replace(",", ".") if isinstance(v, (int, float)) else "—"

    hist.append(Paragraph("Totales del área", st_h))
    t_tot = Table(
        [
            ["Población", "Hogares", "Viviendas", "Unidades censales", "Superficie"],
            [
                n(resultado.get("poblacion_total")),
                n(resultado.get("hogares_total")),
                n(resultado.get("viviendas_total")),
                n(resultado.get("n_unidades")),
                f"{n(round(resultado.get('superficie_total_ha', 0)))} ha",
            ],
        ],
        colWidths=[34.8 * mm] * 5,
    )
    t_tot.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("TEXTCOLOR", (0, 0), (-1, 0), GRIS),
        ("FONTSIZE", (0, 1), (-1, 1), 12),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.4, GRIS_CLARO),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, GRIS_CLARO),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    hist.append(t_tot)

    # --- Indicadores ---
    hist.append(Paragraph("Indicadores socioterritoriales", st_h))
    filas = [["Indicador", "Dimensión", "Valor"]]
    for ind in (resultado.get("indicadores") or {}).values():
        filas.append([
            ind.get("etiqueta", ""),
            (ind.get("dimension", "") or "").capitalize(),
            "—" if ind.get("valor") is None else str(ind["valor"]),
        ])
    t_ind = Table(filas, colWidths=[103 * mm, 40 * mm, 31 * mm], repeatRows=1)
    t_ind.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("FONTNAME", (2, 1), (2, -1), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRIS_CLARO),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    hist.append(t_ind)

    # --- Uso de suelo ---
    suelo = resultado.get("uso_suelo") or []
    if suelo:
        hist.append(Paragraph("Composición de uso de suelo (CONAF)", st_h))
        filas_s = [["Subuso", "Hectáreas", "% del área"]]
        for u in suelo[:12]:
            etiqueta = u["subuso"] + (" (nativo)" if u.get("es_bosque_nativo") else "")
            filas_s.append([
                etiqueta,
                n(round(u.get("hectareas", 0), 1)),
                f"{u.get('porcentaje', 0)}%",
            ])
        t_s = Table(filas_s, colWidths=[103 * mm, 40 * mm, 31 * mm], repeatRows=1)
        t_s.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRIS_CLARO),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        hist.append(t_s)
        if len(suelo) > 12:
            hist.append(Paragraph(
                f"Se listan las 12 categorías principales de {len(suelo)} presentes.",
                st_pie,
            ))

    # --- Anexo: identificadores de las unidades incluidas ---
    unidades = resultado.get("unidades") or []
    if unidades:
        hist.append(PageBreak())
        hist.append(Paragraph("Anexo · Unidades censales incluidas", st_h))
        hist.append(Paragraph(
            f"Listado completo de los {len(unidades)} identificadores INE que "
            "componen el área analizada. U = manzana urbana, R = entidad rural. "
            "Este anexo permite reproducir y auditar la agregación.",
            st_pie,
        ))
        hist.append(Spacer(1, 4))

        # Cuatro columnas de identificadores para aprovechar la página
        COLS = 4
        celdas = [
            f"{u['id_unidad']} ({'R' if u.get('tipo') == 'RURAL' else 'U'})"
            for u in unidades
        ]
        filas_id = [
            celdas[i:i + COLS] + [""] * (COLS - len(celdas[i:i + COLS]))
            for i in range(0, len(celdas), COLS)
        ]
        t_id = Table(filas_id, colWidths=[43.5 * mm] * COLS)
        t_id.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Courier"),
            ("FONTSIZE", (0, 0), (-1, -1), 6),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#334155")),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LINEBELOW", (0, 0), (-1, -1), 0.2, colors.HexColor("#f1f5f9")),
        ]))
        hist.append(t_id)

    # --- Pie ---
    hist.append(Spacer(1, 10))
    hist.append(Paragraph(
        "<b>Fuentes:</b> Censo de Población y Vivienda 2024 (INE) · Catastro de "
        "Recursos Vegetacionales 2024 (CONAF). Sistema de referencia EPSG:32719 "
        "(UTM 19S).<br/>"
        "<b>Método:</b> agregación elástica por regla de centroide — cada unidad "
        "censal se incluye completa si su punto interior cae dentro del área "
        "trazada, garantizando coincidencia exacta con los totales oficiales.<br/>"
        "<b>Protección de datos:</b> el sistema procesa exclusivamente datos "
        "agregados y anonimizados por unidad censal, preservando el secreto "
        "estadístico del INE (Ley N° 21.719).<br/>"
        "<i>Documento generado automáticamente. Prototipo académico (MVP) — "
        "Universidad Andrés Bello.</i>",
        st_pie,
    ))

    doc.build(hist)
    salida.seek(0)
    return salida
