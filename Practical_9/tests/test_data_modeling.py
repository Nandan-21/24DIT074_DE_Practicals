import sys
from pathlib import Path

PRAC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PRAC_DIR))

import pytest
import duckdb
from src.raw_data_generator import generate_raw_sales_csv
from src.staging_cleaner import clean_staging_data
from src.dimensional_loader import populate_star_schema

@pytest.fixture(scope="module")
def setup_warehouse(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("p9_test")
    csv_file = tmp_dir / "test_sales.csv"
    generate_raw_sales_csv(csv_file, num_orders=300, seed=42)

    con = duckdb.connect(str(tmp_dir / "test_warehouse.duckdb"))
    sql_dir = PRAC_DIR / "sql"

    with open(sql_dir / "01_staging_schema.sql", "r", encoding="utf-8") as f:
        con.execute(f.read())
    with open(sql_dir / "02_star_schema_ddl.sql", "r", encoding="utf-8") as f:
        con.execute(f.read())

    clean_staging_data(con, csv_file)
    populate_star_schema(con)
    yield con
    con.close()

def test_fact_table_grain(setup_warehouse):
    con = setup_warehouse
    total_facts = con.execute("SELECT COUNT(*) FROM fact_sales;").fetchone()[0]
    unique_grain = con.execute("SELECT COUNT(DISTINCT (order_id, line_item)) FROM fact_sales;").fetchone()[0]
    assert total_facts == unique_grain
    assert total_facts > 0

def test_referential_integrity(setup_warehouse):
    con = setup_warehouse
    # Check date foreign keys
    orphan_dates = con.execute("""
        SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_date d ON f.date_key = d.date_key WHERE d.date_key IS NULL;
    """).fetchone()[0]
    assert orphan_dates == 0

    # Check customer foreign keys
    orphan_custs = con.execute("""
        SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_customer c ON f.customer_key = c.customer_key WHERE c.customer_key IS NULL;
    """).fetchone()[0]
    assert orphan_custs == 0

    # Check product foreign keys
    orphan_prods = con.execute("""
        SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_product p ON f.product_key = p.product_key WHERE p.product_key IS NULL;
    """).fetchone()[0]
    assert orphan_prods == 0

def test_scd_type_2_customer_tracking(setup_warehouse):
    con = setup_warehouse
    # Exactly 8 active customers
    active_custs = con.execute("SELECT COUNT(*) FROM dim_customer WHERE is_current = TRUE;").fetchone()[0]
    assert active_custs == 8

    # Check that historical orders correctly joined to historical surrogate key
    hist_facts = con.execute("""
        SELECT COUNT(*) 
        FROM fact_sales f
        JOIN dim_customer c ON f.customer_key = c.customer_key
        JOIN dim_date d ON f.date_key = d.date_key
        WHERE d.full_date < CAST('2025-07-01' AS DATE) AND c.is_current = FALSE;
    """).fetchone()[0]
    assert hist_facts > 0

def test_additive_measures_calculation(setup_warehouse):
    con = setup_warehouse
    # Verify net_amount == gross_amount - discount_amount
    mismatches = con.execute("""
        SELECT COUNT(*) FROM fact_sales 
        WHERE ABS(net_amount - (gross_amount - discount_amount)) > 0.01;
    """).fetchone()[0]
    assert mismatches == 0
