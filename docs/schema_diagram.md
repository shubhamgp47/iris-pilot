erDiagram
    source_run {
        bigint run_id PK
        varchar source_name
        char country_code
        varchar dataset_version
        timestamptz extracted_at
        int records_loaded
        timestamptz created_at
    }
    screening_layer {
        bigint layer_id PK
        varchar layer_code UK
        varchar layer_name
        text description
        varchar vertical
        timestamptz created_at
    }
    substation {
        bigint substation_id PK
        char country_code PK
        varchar region_code
        varchar source_id UK
        date source_date
        varchar name
        numeric voltage_kv
        geometry geom "Point, SRID 4326"
        timestamptz created_at
    }
    parcel {
        bigint parcel_id PK
        char country_code PK
        varchar region_code
        varchar source_id UK
        date source_date
        numeric area_sqm
        geometry geom "MultiPolygon, SRID 4326"
        timestamptz created_at
    }
    peatland {
        bigint peatland_id PK
        char country_code PK
        varchar region_code
        varchar source_id UK
        date source_date
        varchar condition_class
        numeric baseline_eco_factor
        geometry geom "MultiPolygon, SRID 4326"
        timestamptz created_at
    }
    evidence {
        bigint evidence_id PK
        char country_code FK,PK
        bigint parcel_id FK
        bigint layer_id FK
        varchar verdict
        jsonb metrics
        timestamptz evaluated_at
        timestamptz created_at
    }

    parcel ||--o{ evidence : "scoped by (country_code, parcel_id)"
    screening_layer ||--o{ evidence : "categorized by layer_id"