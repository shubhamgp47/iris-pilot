# Project IRIS — Canonical PostGIS Pilot Schema

Foundational spatial database schema and prospecting engine for **Project IRIS**, implementing automated land screening for two pilot verticals:

1. **BESS (Battery Energy Storage Systems):** Land parcel grid proximity screening against high-voltage electrical substations.
2. **Peatland Restoration / Eco-Points:** Environmental land condition screening to calculate indicative baseline ecological compensation units.

Built with **PostgreSQL 16+**, **PostGIS 3.4+**, and **Python 3.12+**.

---

## 1. Quickstart & One-Command Rebuild

### Prerequisites

- Docker & Docker Compose
- Python 3.12+

### Setup & One-Touch Execution

#### On Windows (PowerShell):

```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Upgrade pip and install package
python -m pip install --upgrade pip
pip install -e .

# 3. Complete zero-touch rebuild (teardown, migrate, seed, verify, test)
python run.py reset
```

#### On Linux / macOS (Make):

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Upgrade pip and install package
pip install --upgrade pip
pip install -e .

# 3. Complete zero-touch rebuild
make reset
```

### CLI Command Reference

| Unix | Windows | Purpose |
| :--- | :--- | :--- |
| `make up` | `python run.py up` | Start PostgreSQL 16 + PostGIS 3.4 Docker container |
| `make down` | `python run.py down` | Stop container and wipe data volumes |
| `make migrate` | `python run.py migrate` | Apply sequential DDL migrations (001 through 003) |
| `make seed` | `python run.py seed` | Ingest deterministic fixtures into staging and promote to core |
| `make verify` | `python run.py verify` | Run BESS & Peatland spatial queries with EXPLAIN index proof |
| `make test` | `python run.py test` | Execute the automated pytest test suite |
| `make reset` | `python run.py reset` | Execute end-to-end clean teardown, rebuild, seed, and test |

---

## 2. Architecture & Design Principles

```text
                  RAW INGESTION (ELT Landing Zone)
               ┌─────────────────────────────────────┐
               │         iris_staging schema         │
               │   (stg_parcel, stg_substation, ...) │
               └──────────────────┬──────────────────┘
                                  │ Controlled Promotion
                                  │ (Validation, Type Casting,
                                  │  ST_Area, ST_Multi, ST_SetSRID)
                                  ▼
               ┌─────────────────────────────────────┐
               │          iris_core schema           │
               │        (Canonical Curated)          │
               └──────────────────┬──────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │ 1:N                    │ 1:N                    │ 1:N
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│      parcel      │    │    substation    │    │     peatland      │
└────────┬─────────┘    └──────────────────┘    └─────────┬─────────┘
         │                                                │
         │ Evaluated via Spatial Joins (ST_DWithin,       │
         │ ST_Intersects, ST_Intersection)                │
         ▼                                                │
┌──────────────────┐                                      │
│     evidence     │◄─────────────────────────────────────┘
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ screening_layer  │
└──────────────────┘
```

### A. Dual-Schema Strategy: Staging vs. Core

- **`iris_staging` (Landing Zone):** Ingests raw land boundaries and spatial assets from various sources. Fields are typed permissively (`TEXT`, unparsed `JSON`), with no foreign key dependencies or topological geometry constraints. This guarantees ingestion runs do not fail mid-batch due to minor source anomalies.
- **`iris_core` (Canonical Model):** Represents the curated single source of truth. Enforces strict domain constraints, valid PostGIS geometries, non-null country codes, and normalized referential integrity.
- **Controlled Promotion (`src/loader.py`):** Acts as the ELT transform step. Coordinates are parsed using `ST_GeomFromGeoJSON()`, projected with `ST_SetSRID()`, forced into uniform collections via `ST_Multi()`, geodesic surface areas are computed in $\text{m}^2$, and records are promoted into `iris_core`.

### B. Country-Aware Key Contracts

Land parcels and infrastructure registries are administered nationally:
- An ID like `092701_102` can legitimately appear in both German and UK cadastres.
- **Contract Rule:** Every persisted business entity must include `country_code VARCHAR(2) NOT NULL` validated by an ISO 3166-1 alpha-2 check constraint:
  ```sql
  CHECK (country_code ~ '^[A-Z]{2}$')
  ```
- **Compound Uniqueness:** Natural source keys are country-scoped via compound unique constraints:
  ```sql
  CONSTRAINT uq_parcel_country_source UNIQUE (country_code, source_id)
  ```
- **Referential Boundary Enforcement:** The `iris_core.evidence` audit table references parcels via a composite foreign key:
  ```sql
  CONSTRAINT fk_evidence_parcel FOREIGN KEY (country_code, parcel_id)
      REFERENCES iris_core.parcel (country_code, parcel_id) ON DELETE CASCADE
  ```
  This prevents cross-border data corruption (e.g., an operator cannot attach a German parcel to a UK evidence record).

### C. Canonical Field Contract

All core business entities strictly adhere to the required contract:
- `geom`: Spatial geometry column. (The identifier `geometry` is strictly forbidden in `iris_core`).
- `country_code`: ISO 3166-1 alpha-2 code (`VARCHAR(2) NOT NULL`).
- `region_code`: Administrative boundary code (`VARCHAR(10) NOT NULL`, e.g., `'BY'` for Bavaria).
- `source_id`: Source identifier (`VARCHAR(128) NOT NULL`).
- `source_date`: Provenance dataset publication date (`DATE NOT NULL`).
- `created_at`: Row creation timestamp (`TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()`).

---

## 3. Coordinate Reference System (CRS) & Spatial Policy

### Storage CRS
Canonical geometries in `iris_core` are stored as `GEOMETRY(..., 4326)` (WGS 84, longitude/latitude in angular degrees). This provides a uniform coordinate standard for multi-country platforms.

### Calculation Policy (Ellipsoidal vs. Planar)
Standard distance and area calculations on `GEOMETRY` in SRID 4326 compute in angular degrees, which distorts metric measurements at European latitudes:
- **BESS Proximity Screening:** Uses PostGIS geography casts:
  ```sql
  ST_DWithin(p.geom::geography, s.geom::geography, 2000.0)
  ```
  This forces PostGIS to evaluate great-circle distance over the WGS 84 ellipsoid directly in meters.
- **Peatland Overlap & Eco-Points:** Polygon intersection uses native geometry indexing, but computes overlapping area using geography:
  ```sql
  ST_Area(ST_Intersection(p.geom, peat.geom)::geography)
  ```
  This calculates true geodesic area in square meters ($\text{m}^2$).

### Indexing Strategy
Every geometry column features a Generalized Search Tree (GIST) index (`USING GIST (geom)`). GIST creates a 2D bounding-box R-Tree index, enabling PostgreSQL to prune non-intersecting geometries using bounding-box overlaps (`&&`) before executing fine-grained topological calculations.

---

## 4. Screening Layers & Pilot Verticals

### Vertical 1: BESS (Battery Energy Storage Systems)
- **Objective:** Identify land parcels within economic grid-connection distance of electrical substations.
- **Criteria:** Parcel must be within $2{,}000\text{ meters}$ of a substation, scoped to the same country.
- **Pilot Finding:** Parcel `DE-PARCEL-DE-001` is identified at $182.4\text{ meters}$ from Erlangen Nord Substation ($110\text{ kV}$).

### Vertical 2: Peatland Restoration & Eco-Points
- **Objective:** Identify candidate sites for environmental compensation and peatland re-wetting.
- **Formula:**
  $$\text{Eco-Points} = \text{Overlap Area (m}^2\text{)} \times 8.00\text{ eco-points/m}^2$$
- **Pilot Finding:** Parcel `DE-PARCEL-DE-001` overlaps with degraded peatland `PEAT-DE-001` by $96{,}492.48\text{ m}^2$, yielding $771{,}939.84$ baseline eco-points.
- **Auditing:** The verdict and detailed breakdown are persisted into `iris_core.evidence` with JSONB metrics and reference uncertainty disclaimers.

---

## 5. Verification Queries & Index Usage Demonstration

Executing `python run.py verify` (or `make verify`) demonstrates the spatial round trip and provides `EXPLAIN` query plan output proving active GIST index scans:

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
```

---

## 6. Automated Test Suite

The test suite in `tests/` covers the highest-risk correctness conditions:

- **Constraint Testing (`tests/test_constraints.py`):**
  - Enforces `country_code` cannot be `NULL` (`NotNullViolation`).
  - Enforces ISO 3166-1 alpha-2 formatting (`CheckViolation` and `StringDataRightTruncation`).
  - Enforces uniqueness within country namespace (`UniqueViolation`).
  - Validates isolated namespaces (identical `source_id` across different countries is permitted).
  - Validates foreign key country boundary integrity on evidence.
- **Spatial Testing (`tests/test_spatial.py`):**
  - Asserts canonical column names exist and the identifier `geometry` is absent.
  - Verifies SRID 4326 coordinate round-trip fidelity and geometry typing.
  - Asserts metric geodesic distance calculations.
  - Verifies peatland eco-point mathematical baseline formulas.

---

## 7. Deliberate Simplifications & Production Evolution

| Area | Pilot Implementation | Production Evolution |
| :--- | :--- | :--- |
| **Table Partitioning** | Single unpartitioned tables | Declarative PostgreSQL list partitioning on `country_code` (`PARTITION BY LIST (country_code)`) for parcel and evidence. The composite primary key `(country_code, parcel_id)` was designed to support this migration without schema changes. |
| **CRS Strategy** | Canonical `EPSG:4326` with on-the-fly `geography` casts | In addition to global SRID 4326, maintain projected planar columns per national grid (e.g., `EPSG:25832` / UTM Zone 32N for Germany, `EPSG:27700` for the UK) to run 2D planar metric operations without ellipsoidal math overhead. |
| **Migration Tooling** | Sequential Python script executing raw SQL files | Transition to an enterprise database migration framework like Flyway integrated with CI/CD deployment pipelines. |
| **Ingestion Scale** | Synchronous Python seed loader reading local JSON | Distributed asynchronous ELT pipelines streaming raw national cadastre archives directly into staging tables before executing promotion stored procedures. |
| **Provenance Tracking** | Table-level run logging in `source_run` | Row-level lineage via `source_run_id BIGINT REFERENCES source_run(run_id)` on every core entity row. |

---