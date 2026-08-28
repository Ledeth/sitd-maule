# SITD — Metodología y Ejecución del Proyecto

Documento que describe el enfoque metodológico híbrido empleado y documenta la
ejecución real del desarrollo, incluyendo la desviación respecto a la
planificación inicial.

---

> El seguimiento se lleva en un **tablero Kanban en GitHub Projects**
> (*Tablero Kanban SITD Maule*), que es la fuente de verdad del avance. El
> documento `PRODUCT_BACKLOG.md` formaliza ese tablero con épicas, estimación y
> trazabilidad.

## 1. Enfoque metodológico híbrido

Conforme a la justificación de la Tabla 2 del documento de tesis, el proyecto
adoptó un **enfoque híbrido** que combina dos metodologías, cada una aplicada al
componente donde aporta mayor valor:

| Componente | Metodología | Razón |
|---|---|---|
| Documentación normativa | **Cascada** | El cumplimiento normativo público (Leyes 21.719 y 21.180) exige requisitos definidos por adelantado y documentación exhaustiva, sin iteración. |
| Desarrollo de software | **Kanban** | El geoprocesamiento se beneficia de un flujo continuo de tareas con validación temprana e iteración sobre el código. |

La frase que sintetiza el híbrido (Tabla 2): *"Utiliza la cascada para documentar
normas (Ley N° 21.719) y Scrum/Kanban para programar."*

### 1.1 Por qué Kanban y no Scrum

Entre los marcos ágiles, se seleccionó **Kanban** (no Scrum) por corresponder a
la realidad de un **desarrollador único**:

- Scrum está diseñado para equipos y requiere roles (Product Owner, Scrum
  Master), sprints de duración fija y ceremonias (planning, daily, review,
  retrospective) que no son aplicables a un desarrollador individual.
- Kanban se basa en un **flujo continuo de tareas** visualizado en un tablero
  (Por hacer / En progreso / Hecho), limitando el trabajo en progreso, sin exigir
  equipo ni ceremonias.

El Product Backlog (`PRODUCT_BACKLOG.md`) funciona como tablero Kanban: cada
historia de usuario transita por los estados ⏳ Por hacer → 🟡 En progreso →
✅ Hecho.

### 1.2 La rama en cascada (componente normativo)

El cumplimiento normativo siguió fases secuenciales estrictas, sin iteración:

1. **Requisitos** (definidos al inicio): solo datos agregados por unidad censal;
   respeto al secreto estadístico; esquema documentado con metadatos.
2. **Diseño conforme:** tablas sin campos individualizables; `COMMENT ON` en cada
   tabla y columna relevante (Ley 21.180).
3. **Implementación:** el ETL preserva los nulos del INE (no los rellena) y marca
   las celdas de baja frecuencia (Ley 21.719).
4. **Verificación:** se comprobó que ningún atributo cargado permite
   reidentificación.

Esta secuencia rígida es apropiada porque las obligaciones legales se cumplen o
no se cumplen; no se "repriorizan por iteración" como el código.

### 1.3 La rama Kanban (componente de software)

El desarrollo del software siguió un flujo continuo de historias de usuario,
con estas prácticas:

- **Product Backlog** priorizado (MoSCoW) y estimado en *story points*.
- **Flujo continuo:** cada historia se llevaba hasta "Hecho" (con su prueba)
  antes de tomar la siguiente, limitando el trabajo en progreso.
- **Integración continua:** control de versiones Git con ramas por funcionalidad
  y consolidación en `main` tras validar cada incremento.
- **Validación temprana:** pruebas automatizadas de OE1, OE2 y OE3.

---

## 2. Planificación inicial vs. ejecución real

### 2.1 Planificación

La Carta Gantt (Figura 3 de la tesis) previó un desarrollo distribuido en
**11 semanas**, con etapas secuenciales para gestión, backend de datos, motor
analítico, frontend, control de calidad y cierre.

### 2.2 Desviación y su causa

Por **contratiempos personales** (mudanza e incorporación laboral) durante el
período académico, el inicio efectivo del desarrollo se postergó respecto a la
planificación. En consecuencia, la ejecución se concentró en un **período
intensivo** en lugar de distribuirse en las 11 semanas previstas.

**La desviación fue temporal, no de alcance.** Se mantuvo el orden de fases, la
arquitectura definida y —lo esencial— **todos los criterios de aceptación de los
objetivos específicos se cumplieron y verificaron** (OE1 al 100%; OE2 exacto y
muy por debajo del límite de tiempo; OE3 funcional). El desfase entre
planificación y ejecución es habitual en proyectos de software reales; su
documentación transparente constituye una práctica de gestión profesional.

> Nota: la rama en cascada (documentación normativa) no sufrió esta desviación,
> pues sus requisitos se definieron y respetaron desde el diseño inicial del
> esquema. El burndown de la sección 4 aplica únicamente a la rama Kanban
> (desarrollo de software).

---

## 3. Cronología de ejecución real

| Fecha | Hito | Épicas / Historias |
|---|---|---|
| 31-07-2026 | Infraestructura: Docker, WSL2, PostgreSQL/PostGIS, esquema espacial, Git/GitHub | Épica 1 (HU-01 a HU-06) |
| 01-08 a 03-08 | ETL: carga Censo 2024, validación topológica, carga CONAF, cruce materializado | Épica 2 (HU-07 a HU-13) |
| 03-08 a 05-08 | Motor de agregación elástica + verificación OE1/OE2 | Épica 3 (HU-14 a HU-18) |
| 05-08 | API REST con JWT y RBAC territorial; dashboard React | Épica 4 (HU-19 a HU-25) |
| 13-08 | Migración de la base a Supabase; documentación técnica | Épica 5 (HU-06, HU-29) |
| 16-08 | Formalización metodológica (backlog, burndown) | Documentación |
| 26-08 | Resaltado de unidades seleccionadas, tabla de atributos, interfaz en español | Épica 4 (HU-27) |
| 27-08 | Informe PDF territorial con mapa propio y anexo de identificadores | Épica 4 (HU-26, HU-28) |

---

## 4. Burndown chart (rama Kanban)

Story points pendientes a lo largo de la ejecución efectiva del desarrollo de
software. La línea ideal desciende uniformemente (plan); la real refleja el
arranque concentrado tras la postergación.

**Total de trabajo:** 151 story points (31 historias de usuario), según el tablero Kanban.

```
SP
pendientes
151 |●─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   ← inicio (31-07)
    |  ╲
139 |  ●╲            ── Línea ideal (planificada, 11 semanas)
    |    ╲╲          ●● Línea real (ejecución concentrada)
 96 |     ●╲╲
    |       ╲ ╲
 55 |        ╲ ╲
    |         ╲ ╲
 37 |          ●╲ ╲
    |            ╲  ╲
 29 |             ●___●________
 10 |                          ●   ← 27-08 (93%)
    |
  0 |──────────────────────────────────────────
    31-07   03-08   05-08      13-08      27-08
```

### Datos del burndown

| Fecha | SP completados | SP pendientes | % avance |
|---|---|---|---|
| 31-07 | 0 | 151 | 0% |
| 01-08 | 12 | 139 | 8% |
| 03-08 | 55 | 96 | 36% |
| 05-08 | 114 | 37 | 75% |
| 13-08 | 122 | 29 | 81% |
| 27-08 | 141 | 10 | 93% |

---

## 5. Velocidad y análisis

- **Trabajo completado:** 141 SP de 151 (93%); 29 de 31 historias en estado *Listo*.
- **Concentración:** el 73% se completó en los primeros 6 días (Épicas 1-4 más
  el grueso de la 5: el núcleo funcional del MVP).
- **Segunda fase (13-08 al 27-08):** despliegue de la base en la nube,
  refinamiento de la interfaz (resaltado de unidades, tabla de atributos,
  traducción) e informe PDF. Trabajo de menor volumen pero alto valor de uso.
- **Núcleo del MVP (OE1 + OE2):** 100% completo y verificado.
- **Pendiente (10 SP):** empaquetado del sistema (HU-30) y consolidación del
  código con documentación técnica (HU-31), ambos de cierre de proyecto. Las
  cuatro épicas funcionales están completas. La medición SUS del OE3 requiere
  usuarios reales y no es automatizable.

**Interpretación honesta:** la alta velocidad se explica por (a) el uso de
herramientas de asistencia declaradas en la Declaración de Uso de IA de la tesis,
(b) desarrollo concentrado sin interrupciones una vez iniciado, y (c) decisiones
de arquitectura que redujeron el retrabajo (p. ej., el cruce materializado del
ADR-002).

---

## 6. Lecciones y gestión de la desviación

1. **La planificación cumplió su función** aunque no sus plazos: el orden de
   fases y los criterios de aceptación guiaron la ejecución intensiva sin
   improvisación.
2. **Los contratiempos se gestionaron reduciendo la distribución temporal, no el
   alcance ni la calidad.** Todos los OE se cumplieron.
3. **La arquitectura definida tempranamente** (tres capas, cruce materializado)
   hizo viable la ejecución concentrada al evitar retrabajos.
4. **El enfoque híbrido demostró su valor:** la rama en cascada aseguró el
   cumplimiento normativo riguroso desde el diseño, mientras la rama Kanban
   permitió avanzar el software con flexibilidad bajo presión de tiempo.
5. **Área de mejora reconocida:** un inicio más temprano habría permitido incluir
   la medición SUS con usuarios reales y el refinamiento completo de la interfaz.
