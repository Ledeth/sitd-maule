# SITD — Contexto Maestro del Proyecto

Documento de referencia con todo el contexto necesario para retomar el trabajo.
Última actualización: 27 de agosto de 2026.

---

## 1. Identificación

**Proyecto:** Sistema de Inteligencia Territorial Dinámica (SITD)
**Autor:** Leonardo Octavio Nicolás Cuadra Olave
**Profesor guía:** Edgardo Fuentes Cáceres
**Carrera:** Ingeniería en Computación e Informática — Universidad Andrés Bello
**Repositorio:** `https://github.com/Ledeth/sitd-maule` (privado)
**Usuario WSL:** `ledeth` · **Usuario Windows:** `leocu`
**Ruta del proyecto:** `~/sitd` (en WSL2 Ubuntu)

**Título completo:** Sistema de Inteligencia Territorial Dinámica (SITD) para la
automatización de la integración de microdatos del Censo 2024 y CONAF,
resolviendo la rigidez de los límites político-administrativos en la
planificación regional de la Región del Maule.

---

## 2. Qué hace el sistema (en una frase)

Un funcionario dibuja un área cualquiera sobre un mapa —que puede cruzar varios
límites comunales— y el sistema calcula al instante cuánta gente vive ahí, once
indicadores socioterritoriales y la composición de uso de suelo de esa área.

**El problema que resuelve:** la planificación pública opera sobre límites
comunales rígidos, pero los fenómenos reales (incendios, expansión periurbana,
cuencas) no los respetan. Hoy cruzar esos datos toma días de trabajo manual.

**Concepto central:** *agregación elástica* — recalcular indicadores sobre
polígonos ad-hoc que no existen en ningún dato oficial.

---

## 3. Objetivos específicos y su estado

| OE | Criterio | Estado |
|---|---|---|
| **OE1** | 100% de unidades censales integradas con su cobertura CONAF, sin pérdida de geometrías | ✅ **Verificado: 18.653/18.653** |
| **OE2** | 100% de coincidencia con cifras INE + generación < 10 minutos | ✅ **Verificado: exacto; 6-27 ms** |
| **OE3** | 100% de herramientas visuales operativas, cero bugs críticos; SUS ≥ 80 | 🟡 Funcional; **SUS pendiente** (requiere usuarios reales) |

---

## 4. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Base de datos | PostgreSQL 16 + PostGIS 3.4 (local) / 3.3 (Supabase) |
| ETL / motor | Python 3.11, GeoPandas, Shapely, pyogrio |
| API | FastAPI + JWT + bcrypt |
| Frontend | React 18 + Vite + Leaflet + Leaflet.draw + proj4 + Tailwind (CDN) |
| Contenedores | Docker Compose (db + api + frontend) |
| Control de versiones | Git / GitHub, ramas por funcionalidad |
| Nube | Supabase (BD), Render (API, en curso), Vercel (frontend, pendiente) |

**CRS único de trabajo:** EPSG:32719 (UTM 19S), impuesto a nivel de columna.

---

## 5. Datos

### Fuentes

| Fuente | Archivo | Contenido |
|---|---|---|
| INE (Censo 2024) | `maule_base_censal_unificada_32719.gpkg` (39 MB) | 18.653 unidades censales, 217 columnas |
| CONAF (2024) | `07__regi_n_del_maule_actualizaci_n_2024.shp` | 119.017 polígonos de uso de suelo, 56 columnas |

Ambas ya vienen en EPSG:32719. Se ubican en `~/sitd/data/` (no versionadas).

### Cifras de control

- **Población total:** 1.114.486 · **Hogares:** 403.599 · **Viviendas:** 483.027
- **30 comunas** de la Región del Maule
- **Urbano:** 13.769 unidades (manzanas), mediana ~4.144 m²
- **Rural:** 4.884 unidades (entidades), mediana ~1.131.669 m², máx. 1.783 km²
- **Superficie cruzada:** 30.269,5 km² (la región mide ~30.296 km²)

### Hallazgos relevantes en los datos

- `MANZENT` viene como **float** en el origen → se normaliza a texto.
- `n_inmigrantes` (3.977 nulos) y `n_pueblos_orig` (5.853) traen **secreto
  estadístico del INE** → se preservan como null, NO se rellenan con 0.
- Solo **1 unidad** con población 1-4 (riesgo de reidentificación) → marcada.
- 3.250 unidades con población 0 (normales: parques, zonas industriales).

---

## 6. Modelo de datos (7 tablas)

| Tabla | Contenido | Filas |
|---|---|---|
| `comuna` | 30 comunas (CUT + nombre) | 30 |
| `unidad_censal` | Geometría, totales, JSONB temático, centroide generado | 18.653 |
| `conaf_uso_suelo` | Polígonos CONAF (solo local, no se sube a la nube) | — |
| `unidad_conaf` | Cruce precalculado unidad × subuso (área + fracción) | 38.607 |
| `etl_log` | Trazabilidad de rechazos topológicos | — |
| `usuario` | Cuentas (bcrypt + rol + comuna) | 2 demo |
| `consulta_agregacion` | Historial auditable | — |

**Nomenclatura:** se usa `unidad_censal` (no `manzana_censal`) porque el Censo
usa manzanas en zonas urbanas y **entidades** en rurales. El campo `area_tipo`
(URBANO/RURAL) las distingue.

---

## 7. Decisiones de arquitectura (ADRs)

| ADR | Decisión | Por qué importa |
|---|---|---|
| **001** | Unidad censal indivisible: se incluye entera si su `ST_PointOnSurface` cae dentro del polígono | Garantiza OE2 por construcción. Prorratear inventaría población |
| **002** | Cruce CONAF materializado una vez en el ETL | Consultas en ms en vez de minutos. **Además redujo la BD en nube 90%** |
| **003** | Asimetría: demografía indivisible / suelo divisible | Personas se concentran; el suelo es continuo y medible |
| **004** | Clasificación por `SUBUSO` (26 categorías) | Distingue Plantación vs Bosque Nativo vs Mixto. `USO` (8) es muy grueso; `USO_TIERRA` (52) muy técnico |
| **005** | Umbral adaptativo de slivers: descarta si <100 m² **Y** <5% de la unidad | Recupera 209 unidades urbanas diminutas → OE1 al 100% |
| **006** | RBAC aplicado en el servidor (`ST_Intersection` con la comuna) | El técnico no evade la restricción manipulando la petición |
| **007** | bcrypt directo en lugar de passlib | passlib no soporta bcrypt 4.x y está sin mantenimiento |
| **008** | Imports absolutos (`from app.etl.catalogo import`) | Necesario para ejecutar con `python -m` |
| **009** | Simplificación adaptativa de geometrías al enviarlas al navegador (5 a 80 m según cantidad) | Permite resaltar miles de unidades sin saturar el cliente |
| **010** | El mapa del informe PDF se dibuja con datos propios, no con teselas de OSM | Su política prohíbe la descarga automatizada (bloqueo 403). Además hace el informe inmediato y sin dependencias externas |

**Limitación declarada:** la regla de centroide puede sobreestimar en entidades
rurales grandes. Se acepta porque prorratear sería peor (la población rural se
concentra en caseríos, no se distribuye uniforme).

---

## 8. Los once indicadores

Definidos en `backend/app/etl/catalogo.py`. **Regla de oro:** NO se almacenan por
unidad — se calculan sobre los totales YA agregados del área (un porcentaje no es
sumable entre unidades).

| Dimensión | Indicadores |
|---|---|
| Demografía | Índice de dependencia; % adulto mayor (60+) |
| Vulnerabilidad | Tasa analfabetismo; tasa desocupación; % jefatura femenina |
| Habitacional | % viviendas hacinadas; déficit cuantitativo (abs.) |
| Servicios | % sin alcantarillado; % sin internet |
| Ambiental | % calefacción con leña; % agua no formal (pozo/río) |

---

## 9. Cumplimiento normativo

**Ley 21.719 (Protección de Datos Personales):**
- Solo agregados por unidad censal; ninguna tabla admite datos individualizables.
- Secreto estadístico del INE preservado (nulos no rellenados).
- Celdas de baja frecuencia (1-4 hab.) marcadas con `_flag_baja_frecuencia`.

**Ley 21.180 (Transformación Digital del Estado):**
- Esquema autodocumentado con `COMMENT ON` en cada tabla y columna relevante.
- CRS estandarizado y formatos abiertos en toda la cadena.

---

## 10. Metodología

**Enfoque híbrido** (Tabla 2 de la tesis):
- **Cascada** → documentación normativa (secuencial: requisitos → diseño →
  implementación → verificación; las leyes no se "repriorizan por sprint").
- **Kanban** → desarrollo de software (flujo continuo de historias; elegido sobre
  Scrum porque es un desarrollador único, sin equipo ni ceremonias).

**Ejecución real:** el desarrollo comenzó el 31-07-2026 (postergado por mudanza e
incorporación laboral) y se concentró en un período intensivo, en lugar de las 11
semanas planificadas. La desviación fue **temporal, no de alcance**: todos los OE
se cumplieron. Documentado transparentemente en `METODOLOGIA_Y_EJECUCION.md`.

**Product Backlog:** 31 historias de usuario, 151 story points, **93% completado**
(141 SP); 29 de 31 en estado *Listo*. Épicas: Infraestructura (14 SP), ETL (41),
Motor Analítico (29), Frontend e Interfaz (54), Despliegue (13). Fuente de verdad:
**tablero Kanban en GitHub Projects**; `PRODUCT_BACKLOG.md` lo formaliza con
prioridad MoSCoW y trazabilidad con OE y ADR.
## 11. Estado actual del sistema

| Componente | Local (Docker) | Nube |
|---|---|---|
| Base de datos | ✅ Funcionando | ✅ Supabase (São Paulo), org `Tesis UNAB`, proyecto `sitd-maule` |
| API | ✅ Funcionando | 🟡 Render — deploy fallido, pendiente diagnosticar |
| Dashboard | ✅ Funcionando (mapa, resaltado, tabla, informe PDF) | ⏳ Vercel pendiente |

**Decisión:** el proyecto opera en entorno local. El despliegue en nube quedó
como extensión más allá del alcance declarado en la tesis.

**Credenciales demo:** `regional@maule.cl` y `secplan@curepto.cl`, ambas
`demo1234`. (Deben cambiarse antes de exponer públicamente.)

---

## 11.b Funcionalidades del dashboard

- **Login institucional** con aviso de acceso restringido.
- **Mapa interactivo** (Leaflet + OpenStreetMap) centrado en la Región del Maule.
- **Trazado y edición de polígonos ad-hoc**; al ajustar vértices se recalcula.
  Solo polígono libre (el rectángulo se retiró por redundante).
- **Resaltado de las unidades censales efectivamente incluidas** en verde, con
  tooltip de detalle al pasar el cursor. Hace visible la regla de centroide.
- **Tabla de atributos** desplegable con los identificadores, comuna, tipo
  (U/R), población y hogares; al hacer clic el mapa se centra en esa unidad.
- **Panel de indicadores** con los once indicadores y la composición de suelo.
- **Informe PDF descargable** con mapa, totales, indicadores, uso de suelo y
  anexo con todos los identificadores.
- **Interfaz íntegramente en español**, incluidos los controles de dibujo.

## 12. Comandos frecuentes

```bash
# Levantar / apagar
cd ~/sitd && docker compose up -d
docker compose down                    # conserva datos
docker compose down -v                 # ⚠️ BORRA los datos

# Estado y pruebas
docker compose ps
docker compose exec api pytest tests/ -v
curl http://localhost:8000/health

# ETL (ojo: python -m, no python archivo.py)
docker compose exec api python -m app.etl.carga_comunas --archivo /data/maule_base_censal_unificada_32719.gpkg
docker compose exec api python -m app.etl.etl_censo --archivo /data/maule_base_censal_unificada_32719.gpkg
docker compose exec api python -m app.etl.etl_conaf --shapefile /data/conaf/07__regi_n_del_maule_actualizaci_n_2024.shp
docker compose exec api python -m app.api.crear_usuarios

# Contra Supabase: anteponer -e DATABASE_URL="$DATABASE_URL"

# Git
git add -A && git commit -m "mensaje" && git push
```

**URLs locales:** dashboard `localhost:5173` · API `localhost:8000` ·
docs `localhost:8000/docs`

---

## 13. Problemas conocidos y su causa

| Problema | Causa | Solución |
|---|---|---|
| `docker: command not found` en WSL | Integración WSL de Docker Desktop desactivada | Settings → Resources → WSL Integration |
| Mapa Leaflet en blanco o cortado | Leaflet mide el contenedor antes de que el layout flex se aplique | `invalidateSize()` + estilos inline (pendiente verificar) |
| Error de mount `/app/index.html` | Docker Desktop pierde referencia del bind-mount en WSL | `docker compose down && up` o `wsl --shutdown` |
| `ModuleNotFoundError: catalogo` | Import relativo con ejecución `-m` | Import absoluto `from app.etl.catalogo` |
| ETL muy lento contra Supabase | Inserción fila por fila = un round-trip por fila | Inserción por lotes de 500 (ya aplicado) |
| Deploy fallido en Render | Sin diagnosticar — probablemente faltan variables de entorno | Revisar Logs y pestaña Environment |
| Frontend sin responder tras reiniciar `api` | El servicio comparte red (`network_mode: service:api`); al reiniciar api pierde la conexión | `docker compose restart frontend` después |
| `read-only file system` durante el build | Disco C lleno (98%); Docker se queda sin espacio | `docker builder prune -a`; liberar espacio en Windows |
| Tiles de OSM bloqueados (403) en el PDF | Descarga automatizada desde el servidor viola la política de uso de OSM | El informe ya no usa OSM: dibuja con datos propios |

---

## 14. Documentación generada

| Archivo | Contenido |
|---|---|
| `DOCUMENTACION_TECNICA.md` | 15 secciones: arquitectura, modelo de datos, 8 ADRs, API, testing, despliegue |
| `COMO_FUNCIONA_SIMPLE.md` | Explicación sin jerga + preguntas probables de defensa |
| `METODOLOGIA_Y_EJECUCION.md` | Enfoque híbrido, cronología real, burndown |
| `PRODUCT_BACKLOG.md` | 31 historias de usuario, épicas, story points |
| `DESPLIEGUE_NUBE.md` | Guía de despliegue en Supabase / Render / Vercel |
| `decisiones.md` | ADRs originales de Fase I |
| `MIGRACION.md` | Refactor a `unidad_censal` + umbral adaptativo |
| `PRODUCT_BACKLOG.md` | 31 historias en 5 épicas, story points, trazabilidad con OE y ADR, correspondencia commits↔historias |
| `CONTEXTO_MAESTRO.md` | Este documento: contexto completo del proyecto |

---

## 15. Pendientes

**Solicitado por el profesor guía:**
1. ✅ Product Backlog
2. ✅ Burndown chart
3. ⏳ **Arquitectura con modelo 4+1 de Kruchten** (5 vistas: lógica/clases,
   procesos/actividad, desarrollo/paquetes, física/despliegue, escenarios/casos de uso)
4. ⏳ Plan de pruebas (base: tests existentes)
5. ⏳ Plan de entregables
6. ⏳ Manual de usuario
7. ⏳ Manual de proyecto/técnico (base: `DOCUMENTACION_TECNICA.md`)

**Pendientes del tablero Kanban:**
- HU-30 (en progreso): empaquetar el sistema con Docker Compose
- HU-31 (backlog): consolidar código en `main` con documentación técnica

**Otros técnicos:**
- Medición SUS con usuarios reales (OE3) — no automatizable
- (Fuera de alcance) Deploy de API en Render y frontend en Vercel

**Correcciones sugeridas al documento de tesis:**
1. "Microservicios" → es arquitectura contenedorizada de tres capas con BD centralizada
2. Sección 7 asigna el criterio de tiempo a OE1; en la Tabla 1 corresponde a OE2
3. CIREN aparece en Figura 5 pero está fuera del alcance (solo INE y CONAF)
4. Precisar que dentro de lo ágil se optó por **Kanban** (no Scrum)
5. Si se mencionan librerías, actualizar passlib → bcrypt
