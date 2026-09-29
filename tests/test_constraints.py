import pytest
import psycopg

def test_country_code_cannot_be_null(db_conn, db_cursor):
    """
    country_code must be NOT NULL on every persisted business entity.
    """
    with pytest.raises(psycopg.errors.NotNullViolation):
        db_cursor.execute(
            """
            INSERT INTO iris_core.parcel 
                (country_code, region_code, source_id, source_date, geom)
            VALUES 
                (NULL, 'BY', 'PARCEL-FAIL-NULL', '2024-01-01', 
                 ST_Multi(ST_GeomFromText('POLYGON((11 49, 12 49, 12 50, 11 50, 11 49))', 4326)));
            """
        )
    db_conn.rollback()

def test_country_code_format_check(db_conn, db_cursor):
    """
    Ensure country_code enforces 2-letter uppercase ISO format.
    """
    # 1. Invalid lowercase or non-2-char input
    with pytest.raises(psycopg.errors.CheckViolation):
        db_cursor.execute(
            """
            INSERT INTO iris_core.parcel 
                (country_code, region_code, source_id, source_date, geom)
            VALUES 
                ('de', 'BY', 'PARCEL-FAIL-LOWER', '2024-01-01', 
                 ST_Multi(ST_GeomFromText('POLYGON((11 49, 12 49, 12 50, 11 50, 11 49))', 4326)));
            """
        )
    db_conn.rollback()

    # 2. Invalid length (> 2 chars triggers StringDataRightTruncation on VARCHAR(2))
    with pytest.raises(psycopg.errors.StringDataRightTruncation):
        db_cursor.execute(
            """
            INSERT INTO iris_core.parcel 
                (country_code, region_code, source_id, source_date, geom)
            VALUES 
                ('DEU', 'BY', 'PARCEL-FAIL-LEN', '2024-01-01', 
                 ST_Multi(ST_GeomFromText('POLYGON((11 49, 12 49, 12 50, 11 50, 11 49))', 4326)));
            """
        )
    db_conn.rollback()

def test_compound_uniqueness_country_scoped(db_conn, db_cursor):
    """
    Enforce unique constraint (country_code, source_id).
    Inserting an identical source_id in the same country must fail.
    """
    with pytest.raises(psycopg.errors.UniqueViolation):
        db_cursor.execute(
            """
            INSERT INTO iris_core.substation 
                (country_code, region_code, source_id, source_date, name, voltage_kv, geom)
            VALUES 
                ('DE', 'BY', 'SUB-DE-001', '2024-01-01', 'Duplicate Substation', 110.0,
                 ST_GeomFromText('POINT(11.01 49.59)', 4326));
            """
        )
    db_conn.rollback()

def test_country_isolated_namespaces_allowed(db_conn, db_cursor):
    """
    Identical source_ids from different countries MUST be permitted.
    """
    # Clean up test artifact first if left over from previous runs
    db_cursor.execute("DELETE FROM iris_core.substation WHERE country_code = 'GB' AND source_id = 'SUB-DE-001';")
    db_conn.commit()

    db_cursor.execute(
        """
        INSERT INTO iris_core.substation 
            (country_code, region_code, source_id, source_date, name, voltage_kv, geom)
        VALUES 
            ('GB', 'EN', 'SUB-DE-001', '2024-01-01', 'UK Substation with same source_id', 132.0,
             ST_GeomFromText('POINT(-0.12 51.50)', 4326));
        """
    )
    db_conn.commit()

    db_cursor.execute("SELECT count(*) FROM iris_core.substation WHERE source_id = 'SUB-DE-001';")
    count = db_cursor.fetchone()[0]
    assert count == 2

    # Cleanup after test
    db_cursor.execute("DELETE FROM iris_core.substation WHERE country_code = 'GB' AND source_id = 'SUB-DE-001';")
    db_conn.commit()

def test_evidence_foreign_key_country_boundary(db_conn, db_cursor):
    """
    Evidence table requires composite foreign key (country_code, parcel_id).
    Cross-country referencing must fail.
    """
    db_cursor.execute("SELECT parcel_id FROM iris_core.parcel WHERE country_code = 'DE' LIMIT 1;")
    de_parcel_id = db_cursor.fetchone()[0]

    db_cursor.execute("SELECT layer_id FROM iris_core.screening_layer LIMIT 1;")
    layer_id = db_cursor.fetchone()[0]

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        db_cursor.execute(
            """
            INSERT INTO iris_core.evidence 
                (country_code, parcel_id, layer_id, verdict, metrics)
            VALUES 
                ('GB', %s, %s, 'FAIL', '{"reason": "spoofed country"}'::jsonb);
            """,
            (de_parcel_id, layer_id)
        )
    db_conn.rollback()