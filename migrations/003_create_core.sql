DROP TABLE IF EXISTS iris_core.evidence CASCADE;
DROP TABLE IF EXISTS iris_core.peatland CASCADE;
DROP TABLE IF EXISTS iris_core.parcel CASCADE;
DROP TABLE IF EXISTS iris_core.substation CASCADE;
DROP TABLE IF EXISTS iris_core.screening_layer CASCADE;
DROP TABLE IF EXISTS iris_core.source_run CASCADE;

-- Strict constraints, explicit foreign keys, check constraints
-- validated geometry types amd spatial indexes

-- 1. Source Lineage / Runs - Tracks batch/source run metadata
CREATE TABLE iris_core.source_run (
    run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_name VARCHAR(64) NOT NULL, --could be an external data provider or national data registry, etc
    country_code VARCHAR(2) NOT NULL, -- ISO alpha-2 country codes US, CA, GB, DE
    dataset_version VARCHAR(32),
    extracted_at TIMESTAMPTZ NOT NULL,
    records_loaded INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT chk_source_run_country CHECK (country_code ~ '^[A-Z]{2}$') -- ISO alpha-2 country code validation
);

-- 2. Screening Layers - defining rules applied during automated screening
CREATE TABLE iris_core.screening_layer (
    layer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    layer_code VARCHAR(64) NOT NULL UNIQUE,
    layer_name VARCHAR(128) NOT NULL,
    description TEXT,
    vertical VARCHAR(32) NOT NULL, -- 'BESS' or 'PEATLAND'
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- 3. Electrical Substations (Points)
CREATE TABLE iris_core.substation (
    substation_id BIGINT GENERATED ALWAYS AS IDENTITY,
    country_code VARCHAR(2) NOT NULL,
    region_code VARCHAR(10) NOT NULL,
    source_id VARCHAR(128) NOT NULL,
    source_date DATE NOT NULL,
    name VARCHAR(255),
    voltage_kv NUMERIC(6, 2),
    geom GEOMETRY(Point, 4326) NOT NULL, -- EPSG:4326, standard longitude/latitude
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT pk_substation PRIMARY KEY (country_code, substation_id), -- comoposite primary key to allow for multi-country deployments
    CONSTRAINT uq_substation_country_source UNIQUE (country_code, source_id), --  to prevent duplicate substations
    CONSTRAINT chk_substation_country CHECK (country_code ~ '^[A-Z]{2}$')
);
CREATE INDEX idx_substation_geom ON iris_core.substation USING GIST (geom); -- Generalized Search Tree required for PostGIS spatial operators (ST_DWithin, ST_Intersects) to execute fast
CREATE INDEX idx_substation_country_reg ON iris_core.substation (country_code, region_code);

-- 4. Land Parcels (Polygons / MultiPolygons)
CREATE TABLE iris_core.parcel (
    parcel_id BIGINT GENERATED ALWAYS AS IDENTITY,
    country_code VARCHAR(2) NOT NULL,
    region_code VARCHAR(10) NOT NULL,
    source_id VARCHAR(128) NOT NULL,
    source_date DATE NOT NULL,
    area_sqm NUMERIC(12, 2),
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT pk_parcel PRIMARY KEY (country_code, parcel_id),
    CONSTRAINT uq_parcel_country_source UNIQUE (country_code, source_id),
    CONSTRAINT chk_parcel_country CHECK (country_code ~ '^[A-Z]{2}$')
);
CREATE INDEX idx_parcel_geom ON iris_core.parcel USING GIST (geom);
CREATE INDEX idx_parcel_country_reg ON iris_core.parcel (country_code, region_code);

-- 5. Peatland Environmental Soil Polygons
CREATE TABLE iris_core.peatland (
    peatland_id BIGINT GENERATED ALWAYS AS IDENTITY,
    country_code VARCHAR(2) NOT NULL,
    region_code VARCHAR(10) NOT NULL,
    source_id VARCHAR(128) NOT NULL,
    source_date DATE NOT NULL,
    condition_class VARCHAR(64) NOT NULL,
    baseline_eco_factor NUMERIC(5, 2) DEFAULT 8.00,
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT pk_peatland PRIMARY KEY (country_code, peatland_id),
    CONSTRAINT uq_peatland_country_source UNIQUE (country_code, source_id),
    CONSTRAINT chk_peatland_country CHECK (country_code ~ '^[A-Z]{2}$')
);
CREATE INDEX idx_peatland_geom ON iris_core.peatland USING GIST (geom);
CREATE INDEX idx_peatland_country_reg ON iris_core.peatland (country_code, region_code);

-- 6. Evidence / Audit Trail Table for screening evaluations
CREATE TABLE iris_core.evidence (
    evidence_id BIGINT GENERATED ALWAYS AS IDENTITY,
    country_code VARCHAR(2) NOT NULL,
    parcel_id BIGINT NOT NULL,
    layer_id BIGINT NOT NULL REFERENCES iris_core.screening_layer(layer_id),
    verdict VARCHAR(32) NOT NULL, -- 'PASS', 'FAIL', 'WARNING'
    metrics JSONB NOT NULL, -- e.g. {"distance_m": 850}, {"peatland_overlap_sqm": 12400, "eco_points": 99200}
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT pk_evidence PRIMARY KEY (country_code, evidence_id),
    CONSTRAINT fk_evidence_parcel FOREIGN KEY (country_code, parcel_id) 
        REFERENCES iris_core.parcel(country_code, parcel_id) ON DELETE CASCADE,
    CONSTRAINT chk_evidence_country CHECK (country_code ~ '^[A-Z]{2}$')
);
CREATE INDEX idx_evidence_parcel ON iris_core.evidence (country_code, parcel_id);