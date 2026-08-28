# SITD — Product Backlog

Backlog del producto del Sistema de Inteligencia Territorial Dinámica.

**Fuente de verdad:** tablero Kanban en GitHub Projects
(*Tablero Kanban SITD Maule*, repositorio `Ledeth/sitd-maule`). Los
identificadores, títulos, épicas, story points y estados de este documento se
corresponden literalmente con los ítems de ese tablero. El documento añade lo
que la vista de columnas no muestra: agrupación explicada, prioridad MoSCoW y
las matrices de trazabilidad con los objetivos específicos y los ADR.

**Roles:** Administrador técnico (desarrollador) · Usuario regional (GORE /
Gobernador / Alcalde, acceso regional) · Usuario técnico (SECPLAN, restringido
a su comuna).

**Estados Kanban:** ✅ Listo · 🟡 En progreso · ⏳ Backlog.
**Prioridad:** MoSCoW (Must / Should / Could).

---

## Épica 1 — Infraestructura
*14 SP · 6/6 completadas*

| ID | Historia | Prior. | SP | Estado |
|---|---|---|---|---|
| HU-01 | Levantar Docker Compose sobre WSL2 como entorno reproducible | Must | 3 | ✅ |
| HU-02 | Configurar PostgreSQL 16 + PostGIS 3.4 | Must | 3 | ✅ |
| HU-03 | Definir esquema de 7 tablas con `COMMENT ON` (Ley 21.180) | Must | 3 | ✅ |
| HU-04 | Fijar EPSG:32719 como CRS único a nivel de columna | Must | 2 | ✅ |
| HU-05 | Configurar repositorio Git/GitHub con ramas por funcionalidad | Must | 1 | ✅ |
| HU-06 | Conectar la base a Supabase | Could | 2 | ✅ |

## Épica 2 — ETL
*41 SP · 7/7 completadas*

| ID | Historia | Prior. | SP | Estado |
|---|---|---|---|---|
| HU-07 | Cargar las 30 comunas del Maule con su CUT | Must | 2 | ✅ |
| HU-08 | Cargar 18.653 unidades censales del INE sin pérdida de geometrías | Must | 8 | ✅ |
| HU-09 | Normalizar microdatos conforme a norma (MANZENT, secreto estadístico, flag de baja frecuencia) | Must | 7 | ✅ |
| HU-10 | Cargar 119.017 polígonos CONAF de uso de suelo | Must | 8 | ✅ |
| HU-11 | Materializar el cruce unidad × subuso (ADR-002) | Must | 8 | ✅ |
| HU-12 | Aplicar umbral adaptativo de slivers (ADR-005) | Must | 5 | ✅ |
| HU-13 | Registrar rechazos topológicos en `etl_log` | Should | 3 | ✅ |

## Épica 3 — Motor Analítico
*29 SP · 5/5 completadas*

| ID | Historia | Prior. | SP | Estado |
|---|---|---|---|---|
| HU-14 | Incluir la unidad censal entera si su centroide cae en el polígono (ADR-001) | Must | 5 | ✅ |
| HU-15 | Calcular población del área con 100% de coincidencia INE en menos de 10 min | Must | 8 | ✅ |
| HU-16 | Calcular los once indicadores socioterritoriales sobre totales agregados | Must | 8 | ✅ |
| HU-17 | Calcular composición de uso de suelo por SUBUSO (ADR-004) | Must | 5 | ✅ |
| HU-18 | Aplicar asimetría demografía indivisible / suelo divisible (ADR-003) | Must | 3 | ✅ |

## Épica 4 — Frontend e Interfaz
*54 SP · 10/10 completadas*

Incluye la capa de exposición (API) además del cliente web, por ser la
infraestructura que habilita la interfaz.

| ID | Historia | Prior. | SP | Estado |
|---|---|---|---|---|
| HU-19 | Exponer endpoints FastAPI documentados en `/docs` | Must | 5 | ✅ |
| HU-20 | Autenticación JWT con bcrypt y usuarios demo (ADR-007) | Must | 9 | ✅ |
| HU-21 | Aplicar RBAC en servidor con `ST_Intersection` (ADR-006) | Must | 5 | ✅ |
| HU-22 | Registrar cada consulta en `consulta_agregacion` | Should | 3 | ✅ |
| HU-23 | Mapa Leaflet con la región cargada | Must | 5 | ✅ |
| HU-24 | Dibujar polígono ad-hoc con Leaflet.draw | Must | 5 | ✅ |
| HU-25 | Panel de indicadores del área calculada | Must | 3 | ✅ |
| HU-26 | Generar reporte descargable | Should | 3 | ✅ |
| HU-27 | Refinar la interfaz cartográfica: corregir renderizado del contenedor, acotar la vista a los límites de la Región del Maule y mejorar la visibilidad de capas y unidades seleccionadas | Should | 13 | ✅ |
| HU-28 | Gráfico de composición de uso de suelo | Could | 3 | ✅ |

## Épica 5 — Despliegue
*13 SP · 1/3 completadas*

| ID | Historia | Prior. | SP | Estado |
|---|---|---|---|---|
| HU-29 | Desplegar base de datos en Supabase | Could | 3 | ✅ |
| HU-30 | Empaquetar el sistema con Docker Compose | Must | 5 | 🟡 |
| HU-31 | Consolidar código en `main` con documentación técnica | Must | 5 | ⏳ |

---

## Resumen de avance

| Épica | Ítems | Completados | SP | SP completados |
|---|---|---|---|---|
| 1 — Infraestructura | 6 | 6 | 14 | 14 |
| 2 — ETL | 7 | 7 | 41 | 41 |
| 3 — Motor Analítico | 5 | 5 | 29 | 29 |
| 4 — Frontend e Interfaz | 10 | 10 | 54 | 54 |
| 5 — Despliegue | 3 | 1 | 13 | 3 |
| **Total** | **31** | **29** | **151** | **141** |

**Avance global: 93% de los story points** (141 de 151) · 29 de 31 ítems en
estado *Listo*.

Las cuatro épicas funcionales están **100% completas y verificadas**. Lo
pendiente corresponde íntegramente al cierre del proyecto: empaquetado
(HU-30) y consolidación documental (HU-31).

---

## Trazabilidad con los objetivos específicos

| Objetivo | Historias que lo cubren | Estado |
|---|---|---|
| **OE1** — 100% de unidades integradas con su cobertura CONAF | HU-08, HU-10, HU-11, HU-12 | ✅ 18.653/18.653 verificado |
| **OE2** — Coincidencia exacta con INE en menos de 10 minutos | HU-14, HU-15, HU-16, HU-17, HU-18 | ✅ Exacto; 6-27 ms medidos |
| **OE3** — Herramientas visuales operativas, SUS ≥ 80 | HU-23 a HU-28 | 🟡 Funcional; SUS pendiente |

> La medición SUS requiere testeo con usuarios reales y no es automatizable,
> por lo que se documenta como pendiente fuera del alcance del desarrollo.

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

## Correspondencia entre commits e historias

El desarrollo se ejecutó de forma concentrada (ver
`METODOLOGIA_Y_EJECUCION.md`), por lo que cada commit agrupa varias historias en
lugar de una por commit. La correspondencia es la siguiente:

| Fecha | Commit | Historias contenidas |
|---|---|---|
| 03-08 | Fases I-II: infraestructura Docker/PostGIS y ETL Censo+CONAF | HU-01 a HU-05, HU-07 a HU-13 |
| 05-08 | Fase III: motor de agregación elástica + tests OE2 | HU-14 a HU-18 |
| 05-08 | Fase IV: API REST con JWT y RBAC territorial | HU-19 a HU-22 |
| 05-08 | Fase IV: dashboard React con mapa interactivo | HU-23 a HU-25 |
| 13-08 | ETL: inserción por lotes e imports de paquete (Supabase) | HU-06, HU-29 |
| 13-08 | Despliegue API: render.yaml, Dockerfile, CORS | (parcial HU-30) |
| 27-08 | Informe PDF, resaltado de unidades, tabla de atributos, interfaz en español | HU-26, HU-27, HU-28 |

> Reconocimiento explícito: la tesis declara "commits atómicos por tarea". La
> ejecución concentrada derivó en **commits por incremento funcional** en lugar
> de por historia individual. Se documenta la desviación en lugar de omitirla;
> a partir del cierre documental se adopta una granularidad más fina,
> referenciando el issue correspondiente en cada mensaje de commit.

---

## Nota metodológica

El tablero opera bajo **Kanban** (flujo continuo, sin sprints de duración fija),
consistente con el enfoque híbrido descrito en `METODOLOGIA_Y_EJECUCION.md`:
cascada para la documentación normativa, Kanban para el desarrollo de software.
Cada ítem transita ⏳ Backlog → 🟡 En progreso → ✅ Listo.

El backlog se formalizó mediante **ingeniería inversa** sobre un sistema ya
construido, con el fin de documentar de forma trazable el trabajo realizado y
verificar el cumplimiento de la metodología declarada. La estimación en story
points es retrospectiva y refleja la complejidad relativa observada durante el
desarrollo.
