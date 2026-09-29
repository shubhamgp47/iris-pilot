DROP TABLE IF EXISTS iris_staging.stg_parcel CASCADE;
DROP TABLE IF EXISTS iris_staging.stg_substation CASCADE;
DROP TABLE IF EXISTS iris_staging.stg_peatland CASCADE;

-- One staging table per raw data source

--  Unconstrained tables with loose typing (text fields, staging IDs, ingestion timestamps) to allow ingestion without failing
--  on dirty source data.

-- Raw landing table for parcels (land ownership boundaries, land registry in XYZ country)
CREATE TABLE iris_staging.stg_parcel (
    staging_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id TEXT,
    country_code TEXT,
    region_code TEXT,
    raw_geom TEXT,          --raw geometric text representations, WKT[POLYGON((...))] or GeoJSON geometry string
    source_date TEXT,
    metadata JSONB, -- semi-structured metadata as owner names, land use, etc.
    ingested_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

-- Raw landing table for electrical substations (Transmission / Distribution System, electrical grid connection nodes)
CREATE TABLE iris_staging.stg_substation (
    staging_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id TEXT,
    country_code TEXT,
    region_code TEXT,
    substation_name TEXT, --substation identifier
    voltage_kv TEXT, --voltage level of the substation
    raw_geom TEXT,
    source_date TEXT,
    metadata JSONB,
    ingested_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

-- Raw landing table for peatlands (for Environmental screening, environmental classification areas)
CREATE TABLE iris_staging.stg_peatland (
    staging_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id TEXT,
    country_code TEXT,
    region_code TEXT,
    condition_class TEXT,   -- drained, degraded, near-natural, etc
    raw_geom TEXT,
    source_date TEXT,
    metadata JSONB,
    ingested_at TIMESTAMPTZ DEFAULT clock_timestamp()
);