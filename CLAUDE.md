<!--
PEGA AQUÍ ARRIBA TU BRIEF MAESTRO COMPLETO (secciones 0 a 8 del documento
"PROMPT MAESTRO — SITD"), reemplazando este comentario. La adenda de abajo
se conserva: registra lo ya construido y una decisión que complementa tu
sección 4.
-->

---

# ADENDA — Estado del proyecto y decisiones vigentes

## Fase I: COMPLETADA (no rehacer)

Ya existen y funcionan: `docker-compose.yml` (PostGIS 16-3.4 + API),
`db/init/01_schema.sql` (modelo E-R espacial completo, comentado, SRID 32719
forzado por tipo de columna), esqueleto FastAPI con `/health`,
`backend/tests/test_fase1_setup.py`. Leer `docs/decisiones.md` antes de tocar
cualquier cosa.

## Decisión vinculante para Fases III y IV (ADR-001)

El polígono ad-hoc del usuario **selecciona manzanas completas** por regla de
centroide (`ST_PointOnSurface` dentro del polígono). Nunca cortar geometrías
de manzanas para sumar demografía: eso rompería la exactitud exigida por OE2.
El clip proporcional por área solo se aplica a capas CONAF
(`manzana_conaf.fraccion_manzana`). El frontend debe resaltar las manzanas
efectivamente seleccionadas, no solo el polígono dibujado.

## Próximo paso: Fase II (ETL)

1. El usuario entregará las rutas reales de los archivos INE/CONAF en `./data/`.
2. Antes de escribir código de carga: inspeccionar con
   `geopandas.read_file(...).head()`, `.crs`, `.columns`. No asumir nada.
3. Reproyectar todo a EPSG:32719; si la reproyección falla, es bloqueante.
4. Validación topológica con rechazo logueado en `etl_log` (causa específica).
5. Materializar el cruce en `manzana_conaf`.
6. Implementar `tests/test_oe1_integracion.py`: n° de manzanas de entrada ==
   n° de manzanas con al menos una fila en `manzana_conaf` (o registradas en
   `etl_log` como sin cobertura, decisión a validar con el usuario).
