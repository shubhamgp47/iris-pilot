# Verification Queries & Index Usage Output

Execution log from running `python -m src.queries`:

```text
======================================================================
VERTICAL 1: BESS PROSPECTING (Substations within 2000.0m)
======================================================================
  [PASS] Parcel: DE-PARCEL-DE-001 (241233.65 m²) is 182.4m from Substation SUB-DE-001 (Erlangen Nord Substation, 110.00 kV)

======================================================================
VERTICAL 2: PEATLAND RESTORATION & ECO-POINTS SCREENING
======================================================================
  [MATCH] Parcel: DE-PARCEL-DE-001 intersects Peatland: PEAT-DE-001
          Condition Class : drained_agricultural
          Overlap Area    : 96,492.48 m²
          Baseline Factor : 8.00 eco-points/m²
          Estimated Yield : 771,939.84 eco-points

  Audited: Persisted 1 screening record(s) into iris_core.evidence.

======================================================================
ACCEPTANCE CRITERIA 4: PROOF OF SPATIAL GIST INDEX USAGE
======================================================================
  Nested Loop
    ->  Seq Scan on peatland peat
    ->  Index Scan using idx_parcel_geom on parcel p
          Index Cond: (geom && peat.geom)
          Filter: st_intersects(geom, peat.geom)