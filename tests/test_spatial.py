import pytest

def test_canonical_column_contracts(db_cursor):
    """
    Must contain geom, country_code, region_code, source_id, source_date, created_at.
    Column 'geometry' must NOT exist in iris_core entities.
    """
    tables = ["parcel", "substation", "peatland"]
    required_cols = {"geom", "country_code", "region_code", "source_id", "source_date", "created_at"}

    for table in tables:
        db_cursor.execute(
            """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'iris_core' AND table_name = %s;
            """,
            (table,)
        )
        cols = {row[0] for row in db_cursor.fetchall()}
        
        # Verify all required canonical columns are present
        assert required_cols.issubset(cols), f"Missing canonical columns in iris_core.{table}"
        
        # Explicit constraint check: avoid 'geometry' name in core
        assert "geometry" not in cols, f"Forbidden column name 'geometry' detected in iris_core.{table}"

def test_spatial_round_trip_and_srid(db_cursor):
    """
    Verify SRID is 4326 and coordinates round-trip accurately.
    """
    db_cursor.execute(
        """
        SELECT 
            source_id, 
            ST_SRID(geom) as srid, 
            ST_GeometryType(geom) as geom_type,
            ST_AsText(geom) as wkt
        FROM iris_core.substation
        WHERE source_id = 'SUB-DE-001';
        """
    )
    row = db_cursor.fetchone()
    assert row is not None
    assert row[1] == 4326
    assert row[2] == "ST_Point"
    assert "POINT(11.01 49.59)" in row[3]

def test_metric_geodesic_distance_calculation(db_cursor):
    """
    Verify distance calculation produces geodesic meters rather than degrees.
    """
    db_cursor.execute(
        """
        SELECT ST_Distance(p.geom::geography, s.geom::geography)
        FROM iris_core.parcel p, iris_core.substation s
        WHERE p.source_id = 'PARCEL-DE-001' AND s.source_id = 'SUB-DE-001';
        """
    )
    distance_meters = db_cursor.fetchone()[0]
    # Physical distance between (11.0100, 49.5900) and parcel border (11.0120, 49.5910) is ~182 meters
    assert 150.0 < distance_meters < 220.0

def test_peatland_eco_point_formula(db_cursor):
    """
    Verify commercial baseline factor calculation: overlap area * 8 eco-points/m².
    """
    db_cursor.execute(
        """
        SELECT 
            ST_Area(ST_Intersection(p.geom, peat.geom)::geography) AS overlap_area,
            peat.baseline_eco_factor
        FROM iris_core.parcel p
        JOIN iris_core.peatland peat ON ST_Intersects(p.geom, peat.geom)
        WHERE p.source_id = 'PARCEL-DE-001' AND peat.source_id = 'PEAT-DE-001';
        """
    )
    overlap_area, factor = db_cursor.fetchone()
    assert overlap_area > 90000.0
    assert float(factor) == 8.00
    
    expected_points = overlap_area * float(factor)
    assert 750000.0 < expected_points < 800000.0