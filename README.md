# SITD — Sistema de Inteligencia Territorial Dinámica

MVP para la Región del Maule. Integra manzanas censales (Censo 2024, INE) con el
catastro de uso de suelo/vegetación de CONAF y permite **agregación elástica**
sobre polígonos ad-hoc, con dashboard diferenciado por rol (GORE/SECPLAN).

Proyecto de título — Ingeniería en Computación e Informática, UNAB.

## Requisitos

- Docker + Docker Compose
- (Opcional, para desarrollo fuera de contenedor) Python 3.11+ con GDAL instalado

## Arranque rápido

```bash
cp .env.example .env          # ajustar credenciales si se desea
docker compose up -d db       # PostgreSQL + PostGIS; corre db/init/*.sql la 1ª vez
docker compose up -d api      # FastAPI en http://localhost:8000
curl http://localhost:8000/health
```

Los archivos de datos (INE/CONAF) van en `./data/` y **no se versionan**.

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

Mapa tests ↔ objetivos específicos:

| Archivo | Objetivo | Fase |
|---|---|---|
| `tests/test_fase1_setup.py` | Esqueleto coherente (esquema, PostGIS, SRID) | I ✅ |
| `tests/test_oe1_integracion.py` | OE1: 100% manzanas con atributo CONAF | II ⏳ |
| `tests/test_oe2_agregacion.py` | OE2: suma exacta vs. INE + tiempo | III ⏳ |
| `tests/test_oe3_api.py` | OE3: endpoints sin errores de servidor | IV ⏳ |

## Estructura

```
sitd/
├── CLAUDE.md                 # Brief maestro del proyecto (leer primero)
├── docker-compose.yml
├── db/init/01_schema.sql     # Modelo entidad-relación espacial (comentado)
├── docs/decisiones.md        # ADRs — leer ADR-001 (regla de centroide)
├── data/                     # Shapefiles/GPKG de INE y CONAF (gitignored)
├── backend/
│   ├── app/
│   │   ├── core/             # Configuración compartida (CRS, roles, settings)
│   │   ├── etl/              # Fase II — ingesta y validación topológica
│   │   ├── motor/            # Fase III — agregación elástica
│   │   └── api/              # Fase IV — endpoints REST + RBAC
│   └── tests/
└── frontend/                 # Fase IV — React + Tailwind + Leaflet
```

## Decisión clave (leer antes de la Fase III)

El polígono ad-hoc **selecciona manzanas completas por regla de centroide**; no
corta geometrías demográficas. Es lo que hace matemáticamente alcanzable el
100% de coincidencia con los totales INE que exige el OE2. Detalle y
justificación en `docs/decisiones.md` (ADR-001).

## Normativa

- **Ley 21.719**: solo datos agregados/anonimizados a nivel de manzana (ver ADR-004).
- **Ley 21.180**: esquema de BD documentado con `COMMENT ON` en `01_schema.sql`.
