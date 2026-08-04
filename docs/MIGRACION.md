# Refactor v2 — nomenclatura `unidad_censal` + umbral adaptativo

## Qué cambió

**1. Nomenclatura.** El Censo usa MANZANAS en zonas urbanas y ENTIDADES en zonas
rurales. Llamar "manzana" a todo era impreciso. Renombrado:

| Antes | Ahora |
|---|---|
| `manzana_censal` | `unidad_censal` |
| `manzana_conaf` | `unidad_conaf` |
| `id_manzana` | `id_unidad` |
| `fraccion_manzana` | `fraccion_unidad` |

El campo `area_tipo` (URBANO/RURAL) distingue ambos casos.

**2. Umbral adaptativo de slivers.** Antes se descartaba todo trozo <100 m².
Eso eliminaba por completo 209 unidades urbanas diminutas (mediana 59 m², todas
con 0 habitantes), dejando el OE1 en 98,9%.

Ahora un trozo se descarta solo si cumple AMBAS: es menor a 100 m² **y**
representa menos del 5% de la unidad. Verificado: recupera las 209 unidades
(OE1 = 100%) agregando apenas 244 filas.

**3. Esquema enriquecido.** `unidad_censal` ahora guarda `nombre_comuna`,
`area_tipo` y `total_hogares` como columnas propias. `unidad_conaf` guarda
`subuso` y `es_bosque_nativo` como columnas (antes el subuso no se persistía).

## Cómo aplicarlo

⚠️ Requiere recrear la base de datos (el esquema cambió).

```bash
cd ~/sitd

# 1. Reemplazar el esquema y los scripts con los del zip
#    (db/init/01_schema.sql y backend/app/etl/*.py)

# 2. Bajar contenedores BORRANDO el volumen (los datos se recargan después)
docker compose down -v

# 3. Levantar de nuevo: el esquema v2 se crea automáticamente
docker compose up -d
docker compose ps          # esperar sitd_db healthy

# 4. Recargar en orden
docker compose exec api python app/etl/carga_comunas.py \
    --archivo /data/maule_base_censal_unificada_32719.gpkg

docker compose exec api python app/etl/etl_censo.py \
    --archivo /data/maule_base_censal_unificada_32719.gpkg

docker compose exec api python app/etl/etl_conaf.py \
    --shapefile /data/conaf/07__regi_n_del_maule_actualizaci_n_2024.shp

# 5. Verificar
docker compose exec db psql -U sitd -d sitd -c \
  "SELECT COUNT(*), SUM(poblacion_total) FROM unidad_censal;"
docker compose exec db psql -U sitd -d sitd -c \
  "SELECT COUNT(DISTINCT id_unidad), COUNT(*) FROM unidad_conaf;"
```

Resultados esperados:
- `unidad_censal`: 18.653 filas, 1.114.486 población
- `unidad_conaf`: 18.653 unidades distintas (OE1 = 100%), ~38.600 filas

## Nota metodológica para la tesis

La regla de centroide (ADR-001) trata cada unidad como indivisible. En manzanas
urbanas (mediana ~4.100 m²) el error de borde es despreciable. En entidades
rurales (mediana ~1.130.000 m², máximo 1.783 km²) puede ser significativo: un
polígono ad-hoc que cubra parte de una entidad grande sumará el 100% de su
población. Se acepta esta limitación porque la alternativa (prorratear por área)
sería peor: la población rural no se distribuye uniformemente sino concentrada
en caseríos, de modo que el prorrateo inventaría habitantes donde no los hay.
Declarar esta limitación explícitamente es parte del rigor metodológico.
