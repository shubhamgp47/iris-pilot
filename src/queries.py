# src/queries.py
import json
from src.db import get_connection

def query_bess_proximity(cur, max_distance_meters: float = 2000.0):
    """
    Vertical 1: BESS Screening.
    Finds parcels within max_distance_meters of electrical substations,
    scoped by country_code.
    """
    print("\n" + "=" * 70)
    print(f"VERTICAL 1: BESS PROSPECTING (Substations within {max_distance_meters}m)")
    print("=" * 70)
    
    sql = """
    SELECT 
        p.country_code,
        p.source_id AS parcel_source_id,
        p.area_sqm AS parcel_area_sqm,
        s.source_id AS substation_source_id,
        s.name AS substation_name,
        s.voltage_kv,
        ROUND(ST_Distance(p.geom::geography, s.geom::geography)::numeric, 1) AS distance_meters
    FROM iris_core.parcel p
    JOIN iris_core.substation s 
      ON p.country_code = s.country_code
     AND ST_DWithin(p.geom::geography, s.geom::geography, %s)
    ORDER BY distance_meters ASC;
    """
    cur.execute(sql, (max_distance_meters,))
    results = cur.fetchall()
    
    for r in results:
        print(f"  [PASS] Parcel: {r[0]}-{r[1]} ({r[2]} m²) is {r[6]}m from Substation {r[3]} ({r[4]}, {r[5]} kV)")
    
    return results

def query_peatland_screening_and_record_evidence(cur):
    """
    Vertical 2: Peatland Restoration & Eco-Points Screening.
    Computes overlap area (m²), calculates commercial baseline eco-points (8/m²),
    and records an audit trail record in iris_core.evidence.
    """
    print("\n" + "=" * 70)
    print("VERTICAL 2: PEATLAND RESTORATION & ECO-POINTS SCREENING")
    print("=" * 70)

    # 1. Fetch layer ID for PEATLAND_RESTORATION
    cur.execute("SELECT layer_id FROM iris_core.screening_layer WHERE layer_code = 'PEATLAND_RESTORATION';")
    layer_row = cur.fetchone()
    if not layer_row:
        raise RuntimeError("Screening layer 'PEATLAND_RESTORATION' missing.")
    layer_id = layer_row[0]

    # 2. Compute spatial overlap and eco-points
    sql = """
    SELECT 
        p.country_code,
        p.parcel_id,
        p.source_id AS parcel_source_id,
        peat.source_id AS peatland_source_id,
        peat.condition_class,
        peat.baseline_eco_factor,
        ROUND(ST_Area(ST_Intersection(p.geom, peat.geom)::geography)::numeric, 2) AS overlap_area_sqm,
        ROUND(
            (ST_Area(ST_Intersection(p.geom, peat.geom)::geography) * peat.baseline_eco_factor)::numeric, 
            2
        ) AS estimated_eco_points
    FROM iris_core.parcel p
    JOIN iris_core.peatland peat
      ON p.country_code = peat.country_code
     AND ST_Intersects(p.geom, peat.geom)
    WHERE ST_Area(ST_Intersection(p.geom, peat.geom)::geography) > 0;
    """
    cur.execute(sql)
    records = cur.fetchall()

    evidence_records = []
    for r in records:
        country_code = r[0]
        parcel_id = r[1]
        parcel_source_id = r[2]
        peat_source_id = r[3]
        condition_class = r[4]
        factor = float(r[5])
        overlap_sqm = float(r[6])
        eco_points = float(r[7])

        print(f"  [MATCH] Parcel: {country_code}-{parcel_source_id} intersects Peatland: {peat_source_id}")
        print(f"          Condition Class : {condition_class}")
        print(f"          Overlap Area    : {overlap_sqm:,.2f} m²")
        print(f"          Baseline Factor : {factor} eco-points/m²")
        print(f"          Estimated Yield : {eco_points:,.2f} eco-points")

        metrics_payload = {
            "peatland_source_id": peat_source_id,
            "condition_class": condition_class,
            "overlap_area_sqm": overlap_sqm,
            "baseline_eco_factor": factor,
            "estimated_eco_points": eco_points,
            "uncertainty_note": "Preliminary prospecting material. Figures and eco-point estimates are indicative."
        }

        evidence_records.append((
            country_code,
            parcel_id,
            layer_id,
            "PASS" if eco_points > 0 else "FAIL",
            json.dumps(metrics_payload)
        ))

    # 3. Insert audit records into iris_core.evidence
    if evidence_records:
        cur.executemany(
            """
            INSERT INTO iris_core.evidence (country_code, parcel_id, layer_id, verdict, metrics)
            VALUES (%s, %s, %s, %s, %s);
            """,
            evidence_records
        )
        print(f"\n  Audited: Persisted {len(evidence_records)} screening record(s) into iris_core.evidence.")

    return records

def demonstrate_index_usage(cur):
    """
    Acceptance Criteria 4: Prove spatial GIST index usage with EXPLAIN.
    """
    print("\n" + "=" * 70)
    print("ACCEPTANCE CRITERIA 4: PROOF OF SPATIAL GIST INDEX USAGE")
    print("=" * 70)

    # Disable sequential scans in this session to display the index scan path
    cur.execute("SET enable_seqscan = OFF;")

    explain_sql = """
    EXPLAIN (COSTS OFF)
    SELECT p.parcel_id, peat.peatland_id
    FROM iris_core.parcel p
    JOIN iris_core.peatland peat
      ON ST_Intersects(p.geom, peat.geom);
    """
    cur.execute(explain_sql)
    plan_lines = cur.fetchall()

    for line in plan_lines:
        print(f"  {line[0]}")

    cur.execute("SET enable_seqscan = ON;")

def run_all_queries():
    with get_connection() as conn:
        with conn.cursor() as cur:
            query_bess_proximity(cur)
            query_peatland_screening_and_record_evidence(cur)
            demonstrate_index_usage(cur)

if __name__ == "__main__":
    run_all_queries()