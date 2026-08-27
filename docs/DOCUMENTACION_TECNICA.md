# SITD — Documentación Técnica

**Sistema de Inteligencia Territorial Dinámica**
MVP · Región del Maule · Proyecto de título, Ingeniería en Computación e
Informática (Universidad Andrés Bello)

Última actualización: 27 de agosto de 2026.

---

## 1. Descripción general

El SITD integra microdatos demográficos del Censo 2024 (INE) con el catastro de
uso de suelo de CONAF, permitiendo **agregación elástica**: un usuario dibuja un
polígono arbitrario que no respeta límites comunales y el sistema recalcula al
instante la población, once indicadores derivados y la composición de uso de
suelo de esa área.

---

## 2. Arquitectura

Tres capas, contenedorizadas con Docker Compose:

| Capa | Componente | Tecnología |
|---|---|---|
| 1 — Ingesta (ETL) | `backend/app/etl/` | Python 3.11, GeoPandas, Shapely, pyogrio |
| 2 — Procesamiento | `db/` + `backend/app/motor/` | PostgreSQL 16 + PostGIS 3.4 |
| 3 — Presentación | `frontend/` | React 18, Vite, Leaflet, proj4, Tailwind |
| — Exposición | `backend/app/api/` | FastAPI, JWT, bcrypt |

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Fuentes     │ ETL │   PostGIS    │ API │  Dashboard   │
│  INE + CONAF │────▶│  (esquema    │◀───▶│  React +     │
│  (archivos)  │     │   espacial)  │     │  Leaflet     │
└──────────────┘     └──────────────┘     └──────────────┘
                            ▲
                     ┌──────┴──────┐
                     │   Motor de  │──▶ Informe PDF
                     │  agregación │
                     └─────────────┘
```

**Nota sobre nomenclatura.** El documento de tesis menciona "microservicios". La
implementación real es una **arquitectura contenedorizada de tres capas** con
base de datos centralizada, decisión correcta para un MVP y coherente con el
objetivo de eliminar los silos de información. Conviene ajustar esa redacción.

---

## 3. Modelo de datos

CRS único: **EPSG:32719** (UTM 19S), impuesto a nivel de columna.

| Tabla | Contenido | Filas |
|---|---|---|
| `comuna` | 30 comunas del Maule (CUT + nombre) | 30 |
| `unidad_censal` | Geometría, totales, JSONB temático, centroide generado | 18.653 |
| `conaf_uso_suelo` | Polígonos CONAF (solo entorno local) | — |
| `unidad_conaf` | Cruce precalculado unidad × subuso | 38.607 |
| `etl_log` | Trazabilidad de rechazos topológicos | — |
| `usuario` | Cuentas (bcrypt + rol + comuna) | 2 demo |
| `consulta_agregacion` | Historial auditable | — |

### Sobre `unidad_censal`

El Censo usa **manzanas** en zonas urbanas y **entidades** en rurales. El
sistema las unifica bajo *unidad censal*, distinguiéndolas con `area_tipo`:

| Tipo | Cantidad | Área mediana | Población |
|---|---|---|---|
| URBANO (manzanas) | 13.769 | ~4.144 m² | 795.020 |
| RURAL (entidades) | 4.884 | ~1.131.669 m² | 319.466 |

La columna `centroide` se genera con `ST_PointOnSurface(geom)` y está indexada
con GIST: es la base de la selección del motor.

### Cifras de control

Población 1.114.486 · Hogares 403.599 · Viviendas 483.027 · 30 comunas ·
superficie cruzada 30.269,5 km² (la región mide ~30.296 km²).

---

## 4. Decisiones de diseño (ADR)

### ADR-001 — La unidad censal es indivisible (regla de centroide)

El OE2 exige coincidencia exacta con los totales del INE, pero un clip espacial
corta las unidades del borde y prorratea su población por área, produciendo
fracciones de personas.

**Decisión:** el polígono ad-hoc funciona como *selector*, no como *cuchillo*.
Una unidad se incluye completa si su `ST_PointOnSurface` cae dentro. Se usa
PointOnSurface y no ST_Centroid porque el centroide de un polígono cóncavo puede
caer fuera de él.

**Limitación declarada.** En entidades rurales grandes (la mayor mide 1.783 km²)
la inclusión total puede sobreestimar si el polígono cubre solo parte. Se acepta
porque prorratear sería peor: la población rural se concentra en caseríos, de
modo que el prorrateo inventaría habitantes.

### ADR-002 — Cruce CONAF materializado en el ETL

La intersección entre 18.653 unidades y 119.017 polígonos CONAF se calcula una
vez durante la ingesta y se persiste en `unidad_conaf`. Las consultas solo suman
filas precalculadas: respuestas en milisegundos en lugar de minutos.

**Consecuencia no prevista:** al no requerir las geometrías originales de CONAF
en operación, la base desplegable pesa ~60 MB en vez de ~650 MB (reducción del
90%), lo que hizo viable el despliegue en infraestructura gratuita.

### ADR-003 — Asimetría demografía / uso de suelo

- **Demografía** (personas): unidad indivisible. Partir personas por área
  inventa población.
- **Uso de suelo** (superficie): unidad divisible. El suelo es un continuo
  físico; el área de cada trozo es un dato real y medible.

### ADR-004 — Clasificación de suelo por `SUBUSO` (26 categorías)

CONAF ofrece `USO` (8 categorías, muy grueso), `SUBUSO` (26) y `USO_TIERRA` (52,
muy técnico). Se eligió `SUBUSO` porque distingue lo relevante para decisión
—**Plantación vs. Bosque Nativo vs. Bosque Mixto**, tipos de matorral, uso
agrícola— manteniendo nombres legibles. Guardar a este nivel permite agrupar a
las 8 macrocategorías después; al revés no.

El flag `es_bosque_nativo` se deriva de `SUBUSO = 'Bosque Nativo'` (el campo `BN`
del origen es ambiguo).

### ADR-005 — Umbral adaptativo de slivers

Al cruzar dos cartografías aparecen "astillas" de pocos m² en los bordes, que
son artefactos. Un umbral fijo de 100 m² las eliminaba, pero también borraba por
completo **209 unidades urbanas diminutas** (mediana 59 m², todas con 0
habitantes), dejando el OE1 en 98,9%.

**Regla adaptativa:** un trozo se descarta solo si es menor a 100 m² **y**
representa menos del 5% de la unidad. Verificado: recupera las 209 unidades
(OE1 = 100%) añadiendo apenas 244 filas.

### ADR-006 — RBAC aplicado en el servidor

La restricción territorial del rol `tecnico` no es cosmética: el backend
intersecta su polígono con su comuna (`ST_Intersection`) antes de agregar. Un
técnico de SECPLAN no obtiene datos de otra comuna aunque manipule la petición.
Aplica tanto a `/agregacion` como a `/informe`.

### ADR-007 — bcrypt directo en lugar de passlib

`passlib` no es compatible con bcrypt 4.x y su mantenimiento está detenido. Se
usa `bcrypt` directamente: mismo algoritmo, mismo nivel de seguridad, sin capa
intermedia.

### ADR-008 — Imports absolutos de paquete

Los módulos se ejecutan con `python -m app.etl.<modulo>`, lo que exige imports
absolutos (`from app.etl.catalogo import ...`). La forma relativa funciona al
invocar el archivo por ruta pero rompe bajo `-m`.

### ADR-009 — Simplificación adaptativa de geometrías

Las geometrías enviadas al navegador para resaltar unidades se simplifican con
tolerancia variable según el tamaño de la selección (5 m para áreas pequeñas,
hasta 80 m para vistas regionales). A mayor extensión el usuario ve el mapa más
alejado y el detalle fino es imperceptible, de modo que el peso de la respuesta
se mantiene acotado sin dejar de resaltar ninguna unidad. Tope duro: 15.000
unidades.

### ADR-010 — El mapa del informe se genera con datos propios

El primer diseño usaba teselas de OpenStreetMap vía contextily. Los servidores
de OSM **bloquearon las peticiones (HTTP 403)**: su política de uso no permite
la descarga automatizada desde un servidor.

**Decisión:** el mapa del informe se dibuja íntegramente con datos del sistema
—límites comunales derivados de la capa censal, unidades seleccionadas y el
polígono trazado— más una barra de escala. Beneficios: sin dependencias
externas, sin restricciones de licencia, y generación inmediata (~1,8 s frente a
varios segundos de descarga).

El dashboard interactivo sí sigue usando OSM, porque ahí el consumo lo hace el
navegador del usuario, que es uso legítimo según la misma política.

---

## 5. Cumplimiento normativo

### Ley N°21.719 — Protección de Datos Personales

- Solo agregados a nivel de unidad censal. Ninguna tabla de personas o
  viviendas individuales.
- **Secreto estadístico respetado:** `n_inmigrantes` y `n_pueblos_orig` traen
  nulos donde el INE suprimió el dato por baja frecuencia (3.977 y 5.853 casos).
  El ETL los preserva como `null`, no los rellena con 0.
- **Celdas de baja frecuencia marcadas:** unidades con 1-4 habitantes
  etiquetadas con `_flag_baja_frecuencia`. En este dataset es 1 unidad.

### Ley N°21.180 — Transformación Digital del Estado

- Cada tabla y columna relevante lleva `COMMENT ON` en `01_schema.sql`: esquema
  autodocumentado y exportable a estándares abiertos.
- CRS estandarizado y formatos abiertos en toda la cadena.

---

## 6. Los once indicadores

Definidos en `backend/app/etl/catalogo.py`. **Regla fundamental:** los
indicadores derivados NO se almacenan por unidad; se calculan sobre los totales
YA agregados del área. Un porcentaje no es sumable entre unidades.

| Dimensión | Indicador | Fórmula |
|---|---|---|
| Demografía | Índice de dependencia | (<18 + 60+) / población 18–59 |
| Demografía | % adulto mayor | 60+ / población total |
| Vulnerabilidad | Tasa de analfabetismo | analfabetos / población total |
| Vulnerabilidad | Tasa de desocupación | desocupados / fuerza de trabajo |
| Vulnerabilidad | % jefatura femenina | hogares con jefa / total hogares |
| Habitacional | % viviendas hacinadas | hacinadas / total viviendas |
| Habitacional | Déficit cuantitativo | suma absoluta |
| Servicios | % sin alcantarillado | (hogares − con alc.) / hogares |
| Servicios | % sin internet | (hogares − con internet) / hogares |
| Ambiental | % calefacción con leña | leña / total hogares |
| Ambiental | % agua no formal | (pozo + río) / total hogares |

---

## 7. Instalación y operación

### Primera instalación

```bash
git clone https://github.com/Ledeth/sitd-maule.git
cd sitd-maule
cp .env.example .env
```

Colocar en `./data/` (no versionado):
- `maule_base_censal_unificada_32719.gpkg` (Censo 2024, INE)
- `conaf/07__regi_n_del_maule_actualizaci_n_2024.shp` + archivos asociados

```bash
docker compose up -d
docker compose ps            # esperar sitd_db healthy
```

### Carga de datos (orden obligatorio)

> Los módulos se ejecutan con `python -m app.etl.<modulo>`, no con
> `python app/etl/<modulo>.py` (ver ADR-008).

```bash
docker compose exec api python -m app.etl.carga_comunas \
    --archivo /data/maule_base_censal_unificada_32719.gpkg
docker compose exec api python -m app.etl.etl_censo \
    --archivo /data/maule_base_censal_unificada_32719.gpkg
docker compose exec api python -m app.etl.etl_conaf \
    --shapefile /data/conaf/07__regi_n_del_maule_actualizaci_n_2024.shp
docker compose exec api python -m app.api.crear_usuarios
```

El orden importa: `unidad_censal` tiene clave foránea hacia `comuna`, y el cruce
CONAF necesita las unidades cargadas.

### Verificación

```bash
docker compose exec db psql -U sitd -d sitd -c \
  "SELECT COUNT(*), SUM(poblacion_total) FROM unidad_censal;"
# 18653 | 1114486

docker compose exec db psql -U sitd -d sitd -c \
  "SELECT COUNT(DISTINCT id_unidad), COUNT(*) FROM unidad_conaf;"
# 18653 | 38607   (OE1 = 100%)
```

### Uso diario

```bash
docker compose up -d       # levantar (los datos persisten)
docker compose down        # apagar conservando datos
docker compose down -v     # apagar BORRANDO datos (solo para recargar)
```

> Tras reiniciar el servicio `api`, reiniciar también `frontend`: comparten red
> (`network_mode: service:api`) y el frontend pierde conectividad.

Accesos: dashboard `localhost:5173` · API `localhost:8000` ·
documentación interactiva `localhost:8000/docs`

| Correo | Contraseña | Rol | Alcance |
|---|---|---|---|
| `regional@maule.cl` | `demo1234` | regional | Región completa |
| `secplan@curepto.cl` | `demo1234` | tecnico | Solo Curepto (7103) |

---

## 8. API REST

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/auth/login` | — | Devuelve JWT |
| GET | `/me` | Bearer | Usuario autenticado |
| GET | `/comunas` | Bearer | Comunas visibles según rol |
| POST | `/agregacion` | Bearer | Agregación elástica sobre polígono WKT |
| POST | `/informe` | Bearer | Informe PDF del área (descarga) |
| GET | `/health` | — | Estado del servicio y PostGIS |

### Respuesta de `/agregacion`

```json
{
  "n_unidades": 927,
  "poblacion_total": 53205,
  "hogares_total": 18492,
  "viviendas_total": 21154,
  "indicadores": { "...": { "etiqueta": "...", "dimension": "...", "valor": 0 } },
  "uso_suelo": [ { "subuso": "...", "hectareas": 0, "porcentaje": 0, "es_bosque_nativo": false } ],
  "unidades": [ { "id_unidad": "...", "comuna": "...", "tipo": "URBANO", "poblacion": 0, "hogares": 0, "hectareas": 0 } ],
  "geojson": { "type": "FeatureCollection", "features": [] },
  "geometrias_omitidas": false,
  "superficie_total_ha": 2489.3,
  "duracion_ms": 31.2,
  "rol_solicitante": "regional"
}
```

---

## 9. Frontend

| Archivo | Responsabilidad |
|---|---|
| `src/App.jsx` | Estado de sesión; alterna Login / Dashboard |
| `src/Login.jsx` | Autenticación institucional |
| `src/Dashboard.jsx` | Mapa, dibujo, resaltado, tabla, panel, informe |
| `src/api.js` | Cliente HTTP (incluye descarga del PDF como blob) |

**Funcionalidades:** mapa interactivo; trazado y edición de polígonos (al ajustar
vértices se recalcula); resaltado en verde de las unidades incluidas con tooltip;
tabla de atributos desplegable con clic para centrar el mapa; panel de
indicadores; descarga de informe PDF; interfaz íntegramente en español
(incluidos los controles de Leaflet.draw, traducidos vía `L.drawLocal`).

**Conversión de coordenadas.** Leaflet trabaja en WGS84 y el motor en
EPSG:32719. La conversión se hace con proj4 antes de construir el WKT.
Verificado: Talca (−35,4264; −71,6554) → X = 258.925, Y = 6.076.429.

**Sesión en memoria.** El token no se guarda en localStorage: para un perfil
funcionario es preferible que la sesión no persista al cerrar el navegador.

---

## 10. Informe PDF

Generado por `backend/app/motor/informe.py` (reportlab + matplotlib).
Contenido: encabezado con metadatos de la consulta; mapa del área con contexto
comunal, unidades resaltadas y barra de escala; totales; tabla de los once
indicadores; composición de uso de suelo; **anexo con el listado completo de
identificadores** (cuatro columnas, marca U/R) que permite auditar la
agregación; y pie con fuentes, método y aviso normativo.

Tiempo de generación: ~1,8 s. Sin dependencias de red (ver ADR-010).

---

## 11. Testing y resultados

```bash
docker compose exec api pytest tests/ -v
```

| Archivo | Objetivo | Estado |
|---|---|---|
| `test_fase1_setup.py` | Esquema, PostGIS, SRID | 3 ✅ |
| `test_oe2_motor.py` | Exactitud y tiempo del motor | 4 ✅ |
| `test_oe3_api.py` | Login, auth y RBAC territorial | 5 ✅ |

### Evidencia de los objetivos específicos

**OE1 — Integración espacial: 100%.** 18.653 unidades de entrada → 18.653 con
atributo CONAF asignado. Superficie cruzada 30.269,5 km².

**OE2 — Agregación exacta y muy bajo el límite:**

| Comuna | Total INE | Suma del motor | Resultado |
|---|---|---|---|
| Curepto | 9.464 | 9.464 | Exacto |
| Talca | 230.638 | 230.638 | Exacto |
| Linares | 95.855 | 95.855 | Exacto |

Tiempos medidos: 6,5 ms (área urbana), 26,9 ms (vía API con RBAC). Límite del
OE2: 600.000 ms.

**OE3 — Interfaz:** endpoints operativos sin errores de servidor; RBAC
verificado automáticamente. El puntaje SUS ≥ 80 requiere testeo con usuarios
reales (pendiente, no automatizable).

### Métricas del ETL

| Proceso | Resultado |
|---|---|
| Censo: filas procesadas | 18.653 (1 geometría reparada, 0 rechazadas) |
| Censo: integridad | 0 IDs duplicados, 0 nulos |
| CONAF: polígonos | 119.017 (29 reparadas) |
| Cruce: overlay | 38,8 s → 183.503 trozos brutos |
| Cruce: tras agrupar y filtrar | 38.607 filas |

---

## 12. Estructura del repositorio

```
sitd-maule/
├── CLAUDE.md                    Brief maestro del proyecto
├── README.md
├── docker-compose.yml           db + api + frontend
├── .env.example
├── data/                        Fuentes INE y CONAF (gitignored)
├── db/init/01_schema.sql        Modelo entidad-relación espacial
├── docs/                        Documentación, ADRs, backlog, metodología
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py              Punto de entrada FastAPI
│   │   ├── core/config.py       Configuración compartida
│   │   ├── etl/                 Capa 1 — Ingesta
│   │   │   ├── catalogo.py      Mapeo de columnas + fórmulas
│   │   │   ├── carga_comunas.py
│   │   │   ├── etl_censo.py
│   │   │   └── etl_conaf.py
│   │   ├── motor/               Capa 2
│   │   │   ├── agregacion.py    Agregación elástica
│   │   │   └── informe.py       Generación de PDF
│   │   └── api/                 Exposición REST
│   │       ├── rutas.py
│   │       ├── seguridad.py
│   │       └── crear_usuarios.py
│   └── tests/
└── frontend/                    Capa 3 — Dashboard
```

---

## 13. Despliegue en Supabase

Base desplegada en Supabase (PostgreSQL + PostGIS 3.3, São Paulo), organización
`Tesis UNAB`, proyecto `sitd-maule`.

> El plan gratuito permite 2 proyectos **por organización**, no por cuenta:
> crear una organización adicional habilita 2 proyectos más sin costo.

### Qué se despliega

| Tabla | Peso | En la nube |
|---|---|---|
| `unidad_censal` | ~40 MB | Sí |
| `unidad_conaf` | ~3 MB | Sí |
| `comuna`, `usuario`, `etl_log` | < 1 MB | Sí |
| `conaf_uso_suelo` (geometrías CONAF) | **607 MB** | **No** |

El motor consulta únicamente `unidad_censal` y `unidad_conaf`; las geometrías
originales de CONAF solo intervienen en el ETL. Consecuencia del ADR-002.

### Procedimiento

No se usa `pg_dump`. Se **reejecutan los ETL apuntando a Supabase**, lo que evita
conflictos con `spatial_ref_sys` y demuestra que el pipeline es reproducible.

```bash
export DATABASE_URL="postgresql+psycopg://postgres.<ref>:<password>@aws-0-sa-east-1.pooler.supabase.com:5432/postgres"

docker compose exec -e DATABASE_URL="$DATABASE_URL" api \
  python -m app.etl.carga_comunas --archivo /data/maule_base_censal_unificada_32719.gpkg
# ... y así con etl_censo, etl_conaf y crear_usuarios
```

Detalles críticos: añadir `+psycopg` a la URI (Supabase la entrega sin el
driver); codificar en URL los caracteres especiales de la contraseña
(`@` → `%40`).

### Rendimiento de la carga remota

La inserción fila por fila implica un round-trip por fila (~30-50 ms a São
Paulo), lo que hacía la carga inviable. Se implementó **inserción por lotes de
500 filas**, reduciendo la carga de más de 15 minutos a segundos.

---

## 14. Limitaciones conocidas

1. **Regla de centroide en entidades rurales grandes** (ADR-001). Limitación
   metodológica declarada, no defecto.
2. **No se depura la calidad de origen** de INE/CONAF; solo se valida topología
   al ingreso, según el alcance definido.
3. **Sin despliegue institucional.** El MVP opera en entorno local; la base en
   Supabase es un entorno de demostración académica.
4. **Tailwind por CDN** — para producción debería instalarse como plugin PostCSS.
5. **SUS pendiente.** El OE3 incluye una meta de usabilidad ≥ 80 que requiere
   testeo con usuarios reales.
6. **Dos fuentes solamente.** CIREN aparece en los mockups de la tesis pero está
   fuera del alcance declarado.

---

## 15. Correcciones sugeridas al documento de tesis

1. **"Microservicios"** → arquitectura contenedorizada de tres capas con BD
   centralizada (secciones 7, 15, 21).
2. **Numeración OE1/OE2** → la sección 7 asigna el criterio de tiempo a OE1,
   pero en la Tabla 1 corresponde a OE2.
3. **CIREN en Figura 5** → fuera del alcance declarado (solo INE y CONAF).
4. **Marco ágil** → precisar que se optó por **Kanban** (no Scrum), por tratarse
   de un desarrollador único.
5. **Librerías** → actualizar passlib a bcrypt si se mencionan.
