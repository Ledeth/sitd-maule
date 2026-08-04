-- ============================================================================
-- SITD — Sistema de Inteligencia Territorial Dinámica
-- Esquema v2 (Fase II). CRS único de trabajo: EPSG:32719 (UTM 19S).
--
-- NOMENCLATURA: la unidad territorial mínima se llama "unidad censal" porque
-- el Censo usa MANZANAS en áreas urbanas y ENTIDADES en áreas rurales. Ambas
-- conviven en este sistema; el campo area_tipo (URBANO/RURAL) las distingue.
--
-- Cumplimiento normativo:
--  * Ley 21.719: solo agregados a nivel de unidad censal. Ninguna tabla admite
--    atributos individualizables (RUT, nombres, direcciones exactas, etc.).
--  * Ley 21.180: cada tabla y columna relevante lleva COMMENT (metadatos
--    documentados, exportables a estándares abiertos).
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- ----------------------------------------------------------------------------
-- 1. Capa de referencia administrativa (para RBAC por comuna y contexto)
-- ----------------------------------------------------------------------------
CREATE TABLE comuna (
    codigo_comuna   VARCHAR(5) PRIMARY KEY,          -- código único territorial (CUT)
    nombre          TEXT NOT NULL,
    codigo_region   VARCHAR(2) NOT NULL DEFAULT '07',-- Maule
    geom            geometry(MultiPolygon, 32719)
);
COMMENT ON TABLE comuna IS
  'Límites comunales Región del Maule (30 comunas). Usada para RBAC: el rol tecnico (SECPLAN) ve solo su comuna.';

-- ----------------------------------------------------------------------------
-- 2. Fuente 1: unidades censales (Censo 2024, INE)
--    Manzanas urbanas + entidades rurales. Unidad mínima, NUNCA se subdivide
--    para efectos demográficos (ver ADR-001, regla de centroide).
-- ----------------------------------------------------------------------------
CREATE TABLE unidad_censal (
    id_unidad       TEXT PRIMARY KEY,                -- identificador INE (MANZENT)
    codigo_comuna   VARCHAR(5) REFERENCES comuna(codigo_comuna),
    nombre_comuna   TEXT,
    area_tipo       VARCHAR(10) CHECK (area_tipo IN ('URBANO', 'RURAL')),
    poblacion_total INTEGER NOT NULL CHECK (poblacion_total >= 0),
    total_hogares   INTEGER NOT NULL DEFAULT 0 CHECK (total_hogares >= 0),
    total_viviendas INTEGER NOT NULL CHECK (total_viviendas >= 0),
    atributos_extra JSONB DEFAULT '{}'::jsonb,       -- conteos por dimensión, sin reidentificación
    geom            geometry(MultiPolygon, 32719) NOT NULL,
    -- Centroide precalculado: regla de inclusión del motor de agregación
    -- (una unidad pertenece a un polígono ad-hoc si su centroide cae dentro).
    centroide       geometry(Point, 32719) GENERATED ALWAYS AS (ST_PointOnSurface(geom)) STORED
);
COMMENT ON TABLE unidad_censal IS
  'Microdatos agregados y anonimizados por unidad censal (Censo 2024, INE). Manzanas urbanas (area_tipo=URBANO) y entidades rurales (area_tipo=RURAL). Indivisible para agregación demográfica (garantía OE2).';
COMMENT ON COLUMN unidad_censal.area_tipo IS
  'URBANO = manzana censal; RURAL = entidad. Difieren en escala: mediana ~4.100 m2 urbana vs ~1.130.000 m2 rural.';
COMMENT ON COLUMN unidad_censal.centroide IS
  'ST_PointOnSurface (garantiza punto interior incluso en polígonos cóncavos). Regla: centroide dentro del polígono ad-hoc => unidad completa incluida.';

CREATE INDEX idx_unidad_geom      ON unidad_censal USING GIST (geom);
CREATE INDEX idx_unidad_centroide ON unidad_censal USING GIST (centroide);
CREATE INDEX idx_unidad_comuna    ON unidad_censal (codigo_comuna);
CREATE INDEX idx_unidad_area_tipo ON unidad_censal (area_tipo);

-- ----------------------------------------------------------------------------
-- 3. Fuente 2: catastro CONAF (uso de suelo / vegetación)
-- ----------------------------------------------------------------------------
CREATE TABLE conaf_uso_suelo (
    id_poligono     BIGSERIAL PRIMARY KEY,
    uso             TEXT,                            -- macrocategoría (8 valores)
    subuso          TEXT NOT NULL,                   -- clasificación de trabajo (26 valores)
    es_bosque_nativo BOOLEAN NOT NULL DEFAULT false,
    geom            geometry(MultiPolygon, 32719) NOT NULL
);
COMMENT ON TABLE conaf_uso_suelo IS
  'Catastro de uso de suelo y vegetación nativa CONAF, Región del Maule 2024, EPSG:32719.';
COMMENT ON COLUMN conaf_uso_suelo.subuso IS
  'Nivel de clasificación elegido para el sistema (26 categorías). Distingue Plantación / Bosque Nativo / Bosque Mixto, tipos de matorral y uso agrícola.';

CREATE INDEX idx_conaf_geom   ON conaf_uso_suelo USING GIST (geom);
CREATE INDEX idx_conaf_subuso ON conaf_uso_suelo (subuso);

-- ----------------------------------------------------------------------------
-- 4. Cruce materializado unidad × CONAF (soporte de OE1 y rendimiento OE2)
--    Una fila por (unidad, subuso): todos los trozos del mismo subuso dentro
--    de una unidad se suman. Calculado UNA vez en el ETL (ADR-002).
-- ----------------------------------------------------------------------------
CREATE TABLE unidad_conaf (
    id_unidad        TEXT NOT NULL REFERENCES unidad_censal(id_unidad) ON DELETE CASCADE,
    subuso           TEXT NOT NULL,
    es_bosque_nativo BOOLEAN NOT NULL DEFAULT false,
    area_m2          DOUBLE PRECISION NOT NULL CHECK (area_m2 >= 0),
    fraccion_unidad  DOUBLE PRECISION NOT NULL CHECK (fraccion_unidad BETWEEN 0 AND 1),
    PRIMARY KEY (id_unidad, subuso)
);
COMMENT ON TABLE unidad_conaf IS
  'Intersección precalculada unidad censal × subuso CONAF. La unidad actúa como molde que recorta las coberturas. fraccion_unidad = área del subuso / área total cruzada de la unidad (suma 1.0 por unidad).';
COMMENT ON COLUMN unidad_conaf.area_m2 IS
  'Suma de todos los trozos de ese subuso dentro de la unidad. Umbral adaptativo aplicado: se descartan trozos <100 m2 SOLO si representan <5% de la unidad (evita eliminar unidades urbanas diminutas completas).';

CREATE INDEX idx_uc_unidad ON unidad_conaf (id_unidad);
CREATE INDEX idx_uc_subuso ON unidad_conaf (subuso);

-- ----------------------------------------------------------------------------
-- 5. Log de ETL (rechazos topológicos con causa específica — requisito Capa 1)
-- ----------------------------------------------------------------------------
CREATE TABLE etl_log (
    id              BIGSERIAL PRIMARY KEY,
    ejecutado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    fuente          TEXT NOT NULL CHECK (fuente IN ('INE', 'CONAF')),
    id_origen       TEXT,
    resultado       TEXT NOT NULL CHECK (resultado IN ('cargado', 'reparado', 'rechazado')),
    causa           TEXT,
    detalle         JSONB DEFAULT '{}'::jsonb
);
COMMENT ON TABLE etl_log IS
  'Trazabilidad de la validación topológica de ingesta. Todo rechazo lleva causa específica.';

-- ----------------------------------------------------------------------------
-- 6. Usuarios y RBAC (JWT simple, Fase IV)
-- ----------------------------------------------------------------------------
CREATE TABLE usuario (
    id              BIGSERIAL PRIMARY KEY,
    correo          TEXT UNIQUE NOT NULL,
    hash_password   TEXT NOT NULL,                   -- bcrypt; nunca texto plano
    rol             TEXT NOT NULL CHECK (rol IN ('regional', 'tecnico')),
    codigo_comuna   VARCHAR(5) REFERENCES comuna(codigo_comuna),
    activo          BOOLEAN NOT NULL DEFAULT true,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT tecnico_requiere_comuna
        CHECK (rol <> 'tecnico' OR codigo_comuna IS NOT NULL)
);
COMMENT ON TABLE usuario IS
  'Cuentas institucionales. rol regional = GORE/Gobernador/Alcalde (región completa); rol tecnico = SECPLAN (restringido a su comuna).';

-- ----------------------------------------------------------------------------
-- 7. Consultas guardadas del motor (polígonos ad-hoc + resultado, auditable)
-- ----------------------------------------------------------------------------
CREATE TABLE consulta_agregacion (
    id              BIGSERIAL PRIMARY KEY,
    id_usuario      BIGINT REFERENCES usuario(id),
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now(),
    poligono_adhoc  geometry(Polygon, 32719) NOT NULL,
    n_unidades      INTEGER NOT NULL,
    resultado       JSONB NOT NULL,
    duracion_ms     INTEGER NOT NULL
);
COMMENT ON TABLE consulta_agregacion IS
  'Historial de agregaciones elásticas. duracion_ms sirve como evidencia del criterio de rendimiento de OE2.';

CREATE INDEX idx_consulta_geom ON consulta_agregacion USING GIST (poligono_adhoc);
