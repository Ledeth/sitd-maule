# SITD — Product Backlog

Backlog del producto del Sistema de Inteligencia Territorial Dinámica.

**Fuente de verdad:** tablero Kanban en GitHub Projects
(`github.com/Ledeth/sitd-maule` · *Tablero Kanban SITD Maule*). Este documento
formaliza ese tablero añadiendo lo que la vista de columnas no muestra: épicas,
estimación en story points, prioridad MoSCoW y trazabilidad con los objetivos
específicos. Los identificadores y títulos coinciden literalmente con los issues
del repositorio.

**Roles:** Administrador técnico (desarrollador) · Usuario regional (GORE /
Gobernador / Alcalde, acceso regional) · Usuario técnico (SECPLAN, restringido
a su comuna).

**Estimación:** story points (SP), escala Fibonacci, retrospectiva.
**Prioridad:** MoSCoW. **Estados Kanban:** ✅ Listo · 🟡 En progreso · ⏳ Backlog.

---

## Épica 1 — Infraestructura y modelo de datos
*Fase I · Issues #1 a #6*

| ID | Historia | Prior. | SP | Estado |
|---|---|---|---|---|
| HU-01 | Levantar Docker Compose sobre WSL2 como entorno reproducible | Must | 5 | ✅ |
| HU-02 | Configurar PostgreSQL 16 + PostGIS 3.4 | Must | 3 | ✅ |
| HU-03 | Definir esquema de 7 tablas con `COMMENT ON` (Ley 21.180) | Must | 5 | ✅ |
| HU-04 | Fijar EPSG:32719 como CRS único a nivel de columna | Must | 3 | ✅ |
| HU-05 | Configurar repositorio Git/GitHub con ramas por funcionalidad | Must | 2 | ✅ |
| HU-06 | Conectar la base a Supabase | Could | 3 | ✅ |

**Subtotal:** 21 SP · 6/6 completadas

## Épica 2 — Ingesta e integración de datos (ETL)
*Fase II · Issues #7 a #13*

| ID | Historia | Prior. | SP | Estado |
|---|---|---|---|---|
| HU-07 | Cargar las 30 comunas del Maule con su CUT | Must | 2 | ✅ |
| HU-08 | Cargar 18.653 unidades censales del INE sin pérdida de geometrías | Must | 8 | ✅ |
| HU-09 | Normalizar microdatos conforme a norma (MANZENT, secreto estadístico, flag de baja frecuencia) | Must | 5 | ✅ |
| HU-10 | Cargar 119.017 polígonos CONAF de uso de suelo | Must | 5 | ✅ |
| HU-11 | Materializar el cruce unidad × subuso (ADR-002) | Must | 13 | ✅ |
| HU-12 | Aplicar umbral adaptativo de slivers (ADR-005) | Must | 5 | ✅ |
| HU-13 | Registrar rechazos topológicos en `etl_log` | Should | 3 | ✅ |

**Subtotal:** 41 SP · 7/7 completadas

## Épica 3 — Motor de agregación elástica
*Fase III · Issues #14 a #18*

| ID | Historia | Prior. | SP | Estado |
|---|---|---|---|---|
| HU-14 | Incluir la unidad censal entera si su centroide cae en el polígono (ADR-001) | Must | 8 | ✅ |
| HU-15 | Calcular población del área con 100% de coincidencia INE en menos de 10 min | Must | 5 | ✅ |
| HU-16 | Calcular los once indicadores socioterritoriales sobre totales agregados | Must | 8 | ✅ |
| HU-17 | Calcular composición de uso de suelo por SUBUSO (ADR-004) | Must | 5 | ✅ |
| HU-18 | Aplicar asimetría demografía indivisible / suelo divisible (ADR-003) | Must | 3 | ✅ |

**Subtotal:** 29 SP · 5/5 completadas

## Épica 4 — API y control de acceso
*Fase IV (backend) · Issues #19 a #23*

| ID | Historia | Prior. | SP | Estado |
|---|---|---|---|---|
| HU-19 | Exponer endpoints FastAPI documentados en `/docs` | Must | 5 | ✅ |
| HU-20 | Autenticación JWT con bcrypt y usuarios demo (ADR-007) | Must | 5 | ✅ |
| HU-21 | Aplicar RBAC en servidor con `ST_Intersection` (ADR-006) | Must | 5 | ✅ |
| HU-22 | Registrar cada consulta en `consulta_agregacion` | Should | 3 | ✅ |

**Subtotal:** 18 SP · 4/4 completadas

## Épica 5 — Interfaz de usuario (Dashboard)
*Fase IV (frontend) · Issues #24 a #29*

| ID | Historia | Prior. | SP | Estado |
|---|---|---|---|---|
| HU-23 | Mapa Leaflet con la región cargada | Must | 5 | ✅ |
| HU-24 | Dibujar polígono ad-hoc con Leaflet.draw | Must | 5 | ✅ |
| HU-25 | Panel de indicadores del área calculada | Must | 5 | ✅ |
| HU-26 | Generar reporte descargable | Should | 8 | ✅ |
| HU-27 | Refinar la interfaz cartográfica: corregir renderizado del contenedor, acotar la vista a los límites de la Región del Maule y mejorar la visibilidad de capas y unidades seleccionadas | Should | 8 | 🟡 |
| HU-28 | Gráfico de composición de uso de suelo | Could | 3 | 🟡 |

**Subtotal:** 34 SP · 4/6 completadas (26 SP)

## Épica 6 — Despliegue y cierre
*Fase V*

| ID | Historia / Tarea | Prior. | SP | Estado |
|---|---|---|---|---|
| HU-29 | Desplegar base de datos en Supabase | Could | 5 | ✅ |
| HG-01 | Empaquetar el sistema con Docker Compose | Must | 3 | 🟡 |
| HG-02 | Consolidar código en `main` con documentación técnica | Must | 5 | ⏳ |

**Subtotal:** 13 SP · 1/3 completadas (5 SP)

> HG-01 y HG-02 son **hitos de gestión**, no historias de usuario: no entregan
> funcionalidad al usuario final sino que cierran el proyecto. Se numeran con
> el prefijo HG siguiendo la convención de la Carta Gantt de la tesis.

---

## Resumen de avance

| Épica | Ítems | Completados | SP | SP completados |
|---|---|---|---|---|
| 1 — Infraestructura y modelo de datos | 6 | 6 | 21 | 21 |
| 2 — Ingesta e integración (ETL) | 7 | 7 | 41 | 41 |
| 3 — Motor de agregación | 5 | 5 | 29 | 29 |
| 4 — API y control de acceso | 4 | 4 | 18 | 18 |
| 5 — Interfaz de usuario | 6 | 4 | 34 | 26 |
| 6 — Despliegue y cierre | 3 | 1 | 13 | 5 |
| **Total** | **31** | **27** | **156** | **140** |

**Avance global: 90% de los story points** (140 de 156) · 27 de 31 ítems en
estado *Listo*.

El núcleo funcional (Épicas 1 a 4, que cubren OE1 y OE2) está **100% completo y
verificado**. Lo pendiente se concentra en refinamiento de interfaz y cierre
documental.

---

## Trazabilidad con los objetivos específicos

| Objetivo | Historias que lo cubren | Estado |
|---|---|---|
| **OE1** — 100% de unidades integradas con cobertura CONAF | HU-08, HU-10, HU-11, HU-12 | ✅ 18.653/18.653 verificado |
| **OE2** — Coincidencia exacta con INE en < 10 min | HU-14, HU-15, HU-16, HU-17, HU-18 | ✅ Exacto; 6-27 ms medidos |
| **OE3** — Herramientas visuales operativas, SUS ≥ 80 | HU-23 a HU-28 | 🟡 Funcional; SUS pendiente |

## Trazabilidad con las decisiones de arquitectura

Varias historias implementan directamente un ADR documentado, lo que conecta el
backlog con las decisiones técnicas y su justificación:

| Historia | ADR | Decisión |
|---|---|---|
| HU-14 | ADR-001 | Unidad censal indivisible (regla de centroide) |
| HU-11 | ADR-002 | Cruce CONAF materializado en el ETL |
| HU-18 | ADR-003 | Asimetría demografía / uso de suelo |
| HU-17 | ADR-004 | Clasificación por SUBUSO (26 categorías) |
| HU-12 | ADR-005 | Umbral adaptativo de slivers |
| HU-21 | ADR-006 | RBAC aplicado en el servidor |
| HU-20 | ADR-007 | bcrypt directo en lugar de passlib |

---

## Nota metodológica

El backlog se formalizó mediante **ingeniería inversa** sobre un sistema ya
construido, con el fin de documentar de forma trazable el trabajo realizado y
verificar el cumplimiento de la metodología declarada. Las historias se
derivan de las funcionalidades efectivamente implementadas y verificadas; la
estimación en story points es retrospectiva y refleja la complejidad relativa
observada durante el desarrollo.

El tablero opera bajo **Kanban** (flujo continuo, sin sprints de duración
fija), consistente con el enfoque híbrido descrito en
`METODOLOGIA_Y_EJECUCION.md`: cascada para la documentación normativa, Kanban
para el desarrollo de software. Cada ítem transita
⏳ Backlog → 🟡 En progreso → ✅ Listo.
