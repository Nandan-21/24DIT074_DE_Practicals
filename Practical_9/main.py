import json
import sys
from pathlib import Path
import duckdb

PRAC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PRAC_DIR))

from src.raw_data_generator import generate_raw_sales_csv
from src.staging_cleaner import clean_staging_data
from src.dimensional_loader import populate_star_schema
from src.snowflake_loader import populate_snowflake_schema
from src.model_comparator import compare_star_and_snowflake

def run_pipeline():
    print("=" * 70)
    print("PRACTICAL 9: DATA MODELING FOR ANALYTICS")
    print("Kimball Star Schema, SCD Type 2, & Supplementary Snowflake Variant")
    print("=" * 70)

    data_dir = PRAC_DIR / "data"
    outputs_dir = PRAC_DIR / "outputs"
    sql_dir = PRAC_DIR / "sql"
    data_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    csv_path = data_dir / "raw_sales.csv"
    db_path = outputs_dir / "warehouse.duckdb"

    # Step 1: Generate Raw Transactional Sales Data
    print("\n[Step 1] Generating raw transactional retail sales dataset...")
    generate_raw_sales_csv(csv_path, num_orders=1000, seed=42)
    print(f"Generated raw dataset: {csv_path}")

    # Step 2: Initialize Database and DDL
    print("\n[Step 2] Compiling DDL schemas in DuckDB warehouse...")
    con = duckdb.connect(str(db_path))

    with open(sql_dir / "01_staging_schema.sql", "r", encoding="utf-8") as f:
        con.execute(f.read())
    with open(sql_dir / "02_star_schema_ddl.sql", "r", encoding="utf-8") as f:
        con.execute(f.read())
    with open(sql_dir / "03_snowflake_schema_ddl.sql", "r", encoding="utf-8") as f:
        con.execute(f.read())
    print("Staging, Star Schema, and Snowflake Schema tables successfully created.")

    # Step 3: Clean and Staging
    print("\n[Step 3] Executing data cleaning and staging transformation...")
    clean_staging_data(con, csv_path)
    cleaned_count = con.execute("SELECT COUNT(*) FROM stg_sales_cleaned;").fetchone()[0]
    print(f"Cleaned and staged {cleaned_count:,} line items.")

    # Step 4: Populate Star Schema & SCD Type 2
    print("\n[Step 4] Populating Kimball Star Schema & SCD Type 2 Customer Tracking...")
    populate_star_schema(con)
    fact_count = con.execute("SELECT COUNT(*) FROM fact_sales;").fetchone()[0]
    cust_versions = con.execute("SELECT COUNT(*) FROM dim_customer;").fetchone()[0]
    print(f"Loaded {fact_count:,} fact rows into fact_sales.")
    print(f"Loaded {cust_versions} customer records into dim_customer (active + historical versions).")

    # Step 5: Populate Supplementary Snowflake Schema
    print("\n[Step 5] Populating Supplementary Snowflake Schema...")
    populate_snowflake_schema(con)
    snow_fact_count = con.execute("SELECT COUNT(*) FROM fact_sales_snow;").fetchone()[0]
    print(f"Loaded {snow_fact_count:,} rows into fact_sales_snow.")

    # Step 6: Execute Business OLAP Queries
    print("\n[Step 6] Running Sample Business OLAP Query (Monthly Category Sales)...")
    with open(sql_dir / "04_analytical_queries.sql", "r", encoding="utf-8") as f:
        olap_queries = f.read().split(";")
        for idx, qry in enumerate(olap_queries):
            cleaned_qry = qry.strip()
            if cleaned_qry:
                res = con.execute(cleaned_qry).fetchdf()
                print(f"\n--- OLAP Query #{idx + 1} Sample Results (Top 3 rows) ---")
                print(res.head(3).to_string(index=False))

    # Step 7: Compare Star vs Snowflake Schemas
    print("\n[Step 7] Benchmarking Star Schema vs Snowflake Schema Performance...")
    comp_report = compare_star_and_snowflake(con)
    print(f"  Star Schema Join Latency:      {comp_report['query_performance']['star_schema_avg_ms']} ms (2 joins)")
    print(f"  Snowflake Schema Join Latency: {comp_report['query_performance']['snowflake_schema_avg_ms']} ms (5 joins)")

    # Step 8: Export Reports
    print("\n[Step 8] Exporting Validation and Modeling Reports...")
    with open(outputs_dir / "validation_report.json", "w", encoding="utf-8") as f:
        json.dump(comp_report, f, indent=2)

    md_report = f"""# Practical 9: Data Modeling for Analytics - Validation Report

## 1. Dimensional Architecture Overview
- **Modeling Paradigm:** Kimball Dimensional Modeling (Star Schema)
- **Central Fact Table:** `fact_sales`
- **Fact Grain:** Exactly **one row per product line item** within a customer order
- **Dimensions:** `dim_date`, `dim_customer` (SCD Type 2), `dim_product`, `dim_store`

## 2. Slowly Changing Dimension (SCD Type 2) Implementation
- **Total Customer Surrogate Records:** {comp_report['customer_dimension']['total_surrogate_records']}
- **Current Active Customer Records (`is_current = TRUE`):** {comp_report['customer_dimension']['active_current_records']}
- **Historical Superseded Records (`is_current = FALSE`):** {comp_report['customer_dimension']['historical_scd2_records']}
- **Historical Fact Integrity:** Historical orders prior to 2025-07-01 accurately resolve to the customer's prior address, preserving historical analytical accuracy.

## 3. Star Schema vs Snowflake Schema Comparison (Supplementary Problem)
| Dimension Feature | Kimball Star Schema | Normalized Snowflake Schema |
|-------------------|---------------------|-----------------------------|
| **Total Dimension Tables** | 4 | 7 |
| **Hierarchy Storage** | Denormalized in `dim_product`, `dim_store` | Normalized into `dim_category`, `dim_subcategory`, `dim_region` |
| **Required Joins (Category/Region Report)** | 2 Joins | 5 Joins |
| **Average Query Latency (10 runs)** | **{comp_report['query_performance']['star_schema_avg_ms']} ms** | **{comp_report['query_performance']['snowflake_schema_avg_ms']} ms** |
| **Analysis** | Simpler SQL queries, faster aggregations, optimal for BI tools | Eliminates redundant text storage at cost of extra join overhead |
"""
    with open(outputs_dir / "modeling_comparison_report.md", "w", encoding="utf-8") as f:
        f.write(md_report)

    con.close()
    print(f"Artifacts exported to {outputs_dir}")
    print("=" * 70)
    print("PRACTICAL 9 EXECUTION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    run_pipeline()
