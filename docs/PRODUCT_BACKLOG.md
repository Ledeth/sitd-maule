# SITD — Product Backlog

Backlog del producto del Sistema de Inteligencia Territorial Dinámica,
formalizado por ingeniería inversa sobre el sistema construido. Las historias
se agrupan por épica y se expresan en formato estándar:

> *Como [rol], quiero [funcionalidad], para [beneficio].*

**Roles:** Administrador técnico (desarrollador) · Usuario regional (GORE /
Gobernador / Alcalde, acceso a toda la región) · Usuario técnico (SECPLAN,
restringido a su comuna).

**Estimación:** story points (SP), escala Fibonacci. **Prioridad:** MoSCoW.

---

## Épica 1 — Infraestructura y arquitectura base

| ID | Historia | Prioridad | SP | Estado |
|---|---|---|---|---|
| HU-01 | Como administrador técnico, quiero un entorno reproducible con Docker (PostgreSQL + PostGIS + API), para levantar el sistema con un comando. | Must | 5 | ✅ |
| HU-02 | Como administrador técnico, quiero un modelo de datos espacial con CRS único (EPSG:32719), para garantizar consistencia geométrica. | Must | 5 | ✅ |
| HU-03 | Como administrador técnico, quiero control de versiones con Git/GitHub y ramas por funcionalidad, para trazabilidad y respaldo. | Must | 2 | ✅ |
| HU-04 | Como administrador técnico, quiero pruebas automatizadas del esquema, para verificar que la base se crea correctamente. | Should | 2 | ✅ |

## Épica 2 — Ingesta e integración de datos (ETL)

| ID | Historia | Prioridad | SP | Estado |
|---|---|---|---|---|
| HU-05 | Como administrador técnico, quiero cargar las unidades censales del Censo 2024 desde un GeoPackage, para tener la base demográfica. | Must | 8 | ✅ |
| HU-06 | Como administrador técnico, quiero validación topológica con reparación y registro de rechazos, para que solo ingresen geometrías válidas. | Must | 5 | ✅ |
| HU-07 | Como administrador técnico, quiero cargar el catastro CONAF de uso de suelo, para incorporar la dimensión ambiental. | Must | 5 | ✅ |
| HU-08 | Como administrador técnico, quiero cruzar espacialmente unidades con coberturas CONAF y materializar el resultado, para que las consultas sean rápidas. | Must | 13 | ✅ |
| HU-09 | Como administrador técnico, quiero que el 100% de las unidades queden integradas con su cobertura (OE1), para no perder territorio. | Must | 5 | ✅ |
| HU-10 | Como responsable de datos, quiero que el sistema respete el secreto estadístico del INE, para cumplir la Ley 21.719. | Must | 3 | ✅ |
| HU-11 | Como responsable de datos, quiero que las celdas de baja frecuencia queden marcadas, para prevenir reidentificación. | Should | 2 | ✅ |
| HU-12 | Como administrador técnico, quiero carga por lotes contra bases remotas, para que la migración a la nube sea viable. | Should | 3 | ✅ |

## Épica 3 — Motor de agregación elástica

| ID | Historia | Prioridad | SP | Estado |
|---|---|---|---|---|
| HU-13 | Como usuario, quiero dibujar un polígono ad-hoc y obtener la población agregada, para analizar territorios que cruzan límites comunales. | Must | 8 | ✅ |
| HU-14 | Como usuario, quiero que la suma coincida exactamente con las cifras del INE (OE2), para confiar en los resultados. | Must | 5 | ✅ |
| HU-15 | Como usuario, quiero indicadores derivados calculados sobre el área, para tomar decisiones informadas. | Must | 8 | ✅ |
| HU-16 | Como usuario, quiero ver la composición de uso de suelo del área, para evaluar su carácter ambiental. | Must | 5 | ✅ |
| HU-17 | Como usuario, quiero que la consulta responda en menos de 10 minutos (OE2), para trabajar con agilidad. | Must | 3 | ✅ |

## Épica 4 — API y control de acceso

| ID | Historia | Prioridad | SP | Estado |
|---|---|---|---|---|
| HU-18 | Como usuario, quiero autenticarme con correo y contraseña, para acceder de forma segura. | Must | 5 | ✅ |
| HU-19 | Como responsable de seguridad, quiero contraseñas cifradas (bcrypt), para proteger las credenciales. | Must | 2 | ✅ |
| HU-20 | Como usuario regional, quiero acceder a los datos de toda la región, para visión estratégica completa. | Must | 3 | ✅ |
| HU-21 | Como usuario técnico, quiero ver solo los datos de mi comuna, para operar en mi ámbito (RBAC). | Must | 5 | ✅ |
| HU-22 | Como responsable de seguridad, quiero que la restricción territorial se aplique en el servidor, para que no se pueda evadir. | Must | 5 | ✅ |
| HU-23 | Como usuario, quiero una API documentada e interactiva, para probar y entender los endpoints. | Should | 2 | ✅ |

## Épica 5 — Interfaz de usuario (Dashboard)

| ID | Historia | Prioridad | SP | Estado |
|---|---|---|---|---|
| HU-24 | Como usuario, quiero una pantalla de inicio de sesión institucional, para acceder al sistema. | Must | 3 | ✅ |
| HU-25 | Como usuario, quiero un mapa interactivo de la región, para ubicarme territorialmente. | Must | 5 | ✅ |
| HU-26 | Como usuario, quiero dibujar y ajustar polígonos sobre el mapa, para delimitar el área a analizar. | Must | 5 | ✅ |
| HU-27 | Como usuario, quiero ver resaltadas las unidades censales efectivamente incluidas, para entender qué se está agregando (no solo mi trazo). | Must | 5 | ✅ |
| HU-28 | Como usuario, quiero una tabla con los atributos de las unidades incluidas y poder ubicarlas en el mapa, para identificarlas individualmente. | Should | 5 | ✅ |
| HU-29 | Como usuario, quiero ver los indicadores en un panel lateral claro, para interpretar resultados sin ser experto. | Must | 5 | ✅ |
| HU-30 | Como usuario, quiero la interfaz íntegramente en español, para operar sin barreras idiomáticas. | Should | 2 | ✅ |
| HU-31 | Como usuario, quiero generar un informe PDF del área con mapa, indicadores y anexo de identificadores, para respaldar mis decisiones. | Should | 8 | ✅ |
| HU-32 | Como usuario, quiero que la interfaz obtenga un puntaje SUS ≥ 80 (OE3), para asegurar usabilidad. | Should | 3 | ⏳ |

## Épica 6 — Despliegue

| ID | Historia | Prioridad | SP | Estado |
|---|---|---|---|---|
| HU-33 | Como administrador técnico, quiero la base de datos en la nube (Supabase), para que sea accesible fuera de mi máquina. | Could | 5 | ✅ |
| HU-34 | Como administrador técnico, quiero la API desplegada (Render), para exponer el motor por internet. | Could | 5 | 🟡 |
| HU-35 | Como administrador técnico, quiero el dashboard desplegado (Vercel), para acceso con un link. | Could | 3 | ⏳ |

---

## Resumen de avance

| Épica | Historias | Completadas | SP | SP completados |
|---|---|---|---|---|
| 1 — Infraestructura | 4 | 4 | 14 | 14 |
| 2 — ETL | 8 | 8 | 44 | 44 |
| 3 — Motor | 5 | 5 | 29 | 29 |
| 4 — API y RBAC | 6 | 6 | 22 | 22 |
| 5 — Dashboard | 9 | 8 | 38 | 35 |
| 6 — Despliegue | 3 | 1 | 13 | 5 |
| **Total** | **35** | **32** | **160** | **149** |

**Avance global: 93% de los story points** (149 de 160).

El núcleo funcional (Épicas 1-4, que cubren OE1 y OE2) está 100% completo y
verificado. Lo pendiente: medición SUS con usuarios reales (HU-32) y despliegue
en nube de API y frontend (Épica 6), esta última fuera del alcance original.

---

## Trazabilidad con los objetivos específicos

| Objetivo | Historias | Estado |
|---|---|---|
| **OE1** — Integración espacial 100% | HU-08, HU-09 | ✅ 18.653/18.653 verificado |
| **OE2** — Agregación exacta < 10 min | HU-13, HU-14, HU-15, HU-17 | ✅ Exacto; 6-27 ms |
| **OE3** — Interfaz funcional, SUS ≥ 80 | HU-24 a HU-32 | 🟡 Funcional; SUS pendiente |

---

## Nota metodológica

Backlog formalizado mediante **ingeniería inversa** sobre un sistema ya
construido, para documentar de forma trazable el trabajo realizado. Las
historias derivan de (a) las declaradas en la Carta Gantt de la tesis y (b) las
funcionalidades efectivamente implementadas y verificadas. La estimación en
story points es retrospectiva y refleja la complejidad relativa observada.

Funciona además como **tablero Kanban**: cada historia transita
⏳ Por hacer → 🟡 En progreso → ✅ Hecho.
