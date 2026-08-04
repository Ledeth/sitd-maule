# Decisiones de arquitectura (Fase I)

Registro breve tipo ADR. Cada entrada explica el porqué antes de implementar,
según la instrucción de estilo del CLAUDE.md.

## ADR-001 — La manzana es la unidad indivisible del motor (regla de centroide)

**Problema.** El OE2 exige coincidencia *exacta* entre los totales sumados por el
motor y las cifras oficiales del INE. Pero un clip espacial puro corta las
manzanas que quedan en el borde del polígono ad-hoc y prorratea su población
por área, produciendo decimales de personas y rompiendo la exactitud.

**Decisión.** El polígono ad-hoc dibujado por el usuario funciona como
*selector*, no como *cuchillo*:

- Una manzana se incluye **completa** si su `ST_PointOnSurface` cae dentro del
  polígono ad-hoc (columna generada `centroide` en `manzana_censal`). Se usa
  PointOnSurface y no ST_Centroid porque el centroide geométrico de un polígono
  cóncavo puede caer fuera de él.
- Los indicadores demográficos se suman sobre manzanas enteras ⇒ la suma
  coincide por construcción con los totales INE (OE2 garantizado
  matemáticamente, el test solo lo confirma).
- Las capas CONAF sí admiten proporción por área (`manzana_conaf.fraccion_manzana`),
  porque la cobertura de suelo es un fenómeno continuo, no conteo de personas.

**Consecuencia.** El frontend debe mostrar al usuario las manzanas efectivamente
seleccionadas (no el polígono crudo), para que entienda qué área se está
agregando realmente.

## ADR-002 — Cruce manzana × CONAF materializado en el ETL

**Problema.** La intersección espacial entre ~decenas de miles de manzanas y el
catastro CONAF regional es la operación cara. Hacerla en cada consulta del
dashboard arriesga el límite de 10 minutos del OE2.

**Decisión.** La intersección se calcula **una sola vez** en la Fase II (ETL) y
se persiste en `manzana_conaf` con área y fracción. Las consultas del dashboard
solo filtran manzanas por centroide (índice GIST) y suman filas precalculadas
⇒ tiempos de segundos. El límite de 10 minutos queda reservado para la carga
ETL completa, no para la interacción del usuario.

## ADR-003 — CRS único EPSG:32719 impuesto en la capa de datos

El esquema declara `geometry(..., 32719)` en todas las tablas: PostGIS rechaza
inserciones en otro SRID. Así el riesgo de CRS mezclados (identificado en el
plan de riesgos) se vuelve un error explícito de carga en vez de un bug
silencioso de cálculo de áreas. El ETL de Fase II reproyecta antes de insertar.

## ADR-004 — Cumplimiento Ley 21.719 por diseño de esquema

`manzana_censal` solo admite agregados (`poblacion_total`, `total_viviendas`,
`atributos_extra` JSONB documentado como no-individualizable). No existen
tablas de personas ni viviendas individuales. La revisión de Fase V debe
verificar que ningún atributo cargado en `atributos_extra` permita
reidentificación (celdas con población < umbral se revisan ahí).

## ADR-005 — JWT simple con dos roles, comuna en el token

RBAC mínimo del brief: `regional` (región completa) y `tecnico` (SECPLAN,
restringido a `codigo_comuna`). La restricción territorial se aplica en el
backend (filtro SQL por comuna), nunca solo en el frontend.
