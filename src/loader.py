import json
from pathlib import Path
from src.db import get_connection

SEEDS_DIR = Path(__file__).parent.parent / "fixtures" / "seeds"

def seed_screening_layers(cur):
    """Seed the iris_core.screening_layer table with predefined screening layers"""
    layers = [
        ("GRID_BESS_PROXIMITY", "Substation Grid Proximity", "Evaluates parcel distance to nearest electrical substation", "BESS"), # BESS prospecting rule
        ("PEATLAND_RESTORATION", "Peatland Restoration Overlap", "Screens parcel area overlapping degraded peatland for eco-points", "PEATLAND"), # paetland restoration rule
    ]
    cur.executemany( # prepares the SQL statement once and executes it for every tuple in the layers sequence
        """
        INSERT INTO iris_core.screening_layer (layer_code, layer_name, description, vertical)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (layer_code) DO NOTHING;
        """,
        layers
    )

def seed_source_run(cur, source_name: str, country_code: str, count: int):
    cur.execute(
        """
        INSERT INTO iris_core.source_run (source_name, country_code, dataset_version, extracted_at, records_loaded)
        VALUES (%s, %s, 'v2024.1', clock_timestamp(), %s);
        """,
        (source_name, country_code, count)
    )

def load_and_promote_substations(cur):
    """Load substations from JSON and promote to iris_core.substation"""
    with open(SEEDS_DIR / "substations.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Ingest into staging
    for item in data:
        cur.execute(
            """
            INSERT INTO iris_staging.stg_substation 
                (source_id, country_code, region_code, substation_name, voltage_kv, raw_geom, source_date, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                item["source_id"],
                item["country_code"],
                item["region_code"],
                item["name"],
                str(item["voltage_kv"]),
                json.dumps(item["geometry"]),
                item["source_date"],
                json.dumps({"vendor": "TestGridDE"})
            )
        )

    # 2. Promote to core
    cur.execute(
        """
        INSERT INTO iris_core.substation (country_code, region_code, source_id, source_date, name, voltage_kv, geom)
        SELECT 
            country_code::CHAR(2),
            region_code,
            source_id,
            source_date::DATE,
            substation_name,
            voltage_kv::NUMERIC(6,2),
            ST_SetSRID(ST_GeomFromGeoJSON(raw_geom), 4326)
        FROM iris_staging.stg_substation
        ON CONFLICT (country_code, source_id) DO UPDATE 
        SET name = EXCLUDED.name,
            voltage_kv = EXCLUDED.voltage_kv,
            geom = EXCLUDED.geom;
        """
    )
    seed_source_run(cur, "cadastre_substations_de", "DE", len(data))

def load_and_promote_parcels(cur):
    with open(SEEDS_DIR / "parcels.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        cur.execute(
            """
            INSERT INTO iris_staging.stg_parcel 
                (source_id, country_code, region_code, raw_geom, source_date, metadata)
            VALUES (%s, %s, %s, %s, %s, %s);
            """,
            (
                item["source_id"],
                item["country_code"],
                item["region_code"],
                json.dumps(item["geometry"]),
                item["source_date"],
                json.dumps({"cadastre_authority": "BayernVermessung"})
            )
        )

    # Promote into core and compute geodesic area in square meters using geography
    cur.execute(
        """
        INSERT INTO iris_core.parcel (country_code, region_code, source_id, source_date, area_sqm, geom)
        SELECT 
            country_code::CHAR(2),
            region_code,
            source_id,
            source_date::DATE,
            ROUND(ST_Area(ST_SetSRID(ST_GeomFromGeoJSON(raw_geom), 4326)::geography)::numeric, 2),
            ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(raw_geom), 4326))
        FROM iris_staging.stg_parcel
        ON CONFLICT (country_code, source_id) DO UPDATE 
        SET area_sqm = EXCLUDED.area_sqm,
            geom = EXCLUDED.geom;
        """
    )
    seed_source_run(cur, "cadastre_parcels_de", "DE", len(data))

def load_and_promote_peatlands(cur):
    with open(SEEDS_DIR / "peatlands.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        cur.execute(
            """
            INSERT INTO iris_staging.stg_peatland 
                (source_id, country_code, region_code, condition_class, raw_geom, source_date, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            """,
            (
                item["source_id"],
                item["country_code"],
                item["region_code"],
                item["condition_class"],
                json.dumps(item["geometry"]),
                item["source_date"],
                json.dumps({"survey_standard": "EU_SOIL_2023"})
            )
        )

    cur.execute(
        """
        INSERT INTO iris_core.peatland (country_code, region_code, source_id, source_date, condition_class, baseline_eco_factor, geom)
        SELECT 
            country_code::CHAR(2),
            region_code,
            source_id,
            source_date::DATE,
            condition_class,
            8.00,
            ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(raw_geom), 4326))
        FROM iris_staging.stg_peatland
        ON CONFLICT (country_code, source_id) DO UPDATE 
        SET condition_class = EXCLUDED.condition_class,
            geom = EXCLUDED.geom;
        """
    )
    seed_source_run(cur, "soil_peatland_inventory_de", "DE", len(data))

def run_loader():
    with get_connection() as conn:
        with conn.cursor() as cur:
            print("Seeding screening layers...")
            seed_screening_layers(cur)
            print("Loading and promoting substations...")
            load_and_promote_substations(cur)
            print("Loading and promoting parcels...")
            load_and_promote_parcels(cur)
            print("Loading and promoting peatlands...")
            load_and_promote_peatlands(cur)
    print("Database successfully seeded and promoted to iris_core.")

if __name__ == "__main__":
    run_loader()