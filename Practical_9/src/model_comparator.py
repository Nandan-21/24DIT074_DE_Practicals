import time
from typing import Dict
import duckdb

def compare_star_and_snowflake(con: duckdb.DuckDBPyConnection) -> Dict:
    """
    Compares Star Schema vs Snowflake Schema across schema complexity,
    join overhead, query runtimes, and row counts.
    """
    # 1. Row count checks
    fact_star_cnt = con.execute("SELECT COUNT(*) FROM fact_sales;").fetchone()[0]
    fact_snow_cnt = con.execute("SELECT COUNT(*) FROM fact_sales_snow;").fetchone()[0]
    cust_dim_cnt = con.execute("SELECT COUNT(*) FROM dim_customer;").fetchone()[0]
    cust_current_cnt = con.execute("SELECT COUNT(*) FROM dim_customer WHERE is_current = TRUE;").fetchone()[0]
    cust_historical_cnt = con.execute("SELECT COUNT(*) FROM dim_customer WHERE is_current = FALSE;").fetchone()[0]

    # 2. Benchmark Query on Star Schema (Single level joins)
    star_query = """
        SELECT 
            p.category,
            s.region,
            SUM(f.net_amount) AS total_revenue
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        JOIN dim_store s ON f.store_key = s.store_key
        GROUP BY p.category, s.region;
    """
    star_times = []
    for _ in range(10):
        t0 = time.perf_counter()
        con.execute(star_query).fetchall()
        t1 = time.perf_counter()
        star_times.append((t1 - t0) * 1000.0)
    avg_star_ms = round(sum(star_times) / len(star_times), 3)

    # 3. Benchmark Equivalent Query on Snowflake Schema (Normalized multi-level joins)
    snow_query = """
        SELECT 
            c.category_name AS category,
            r.region_name AS region,
            SUM(f.net_amount) AS total_revenue
        FROM fact_sales_snow f
        JOIN dim_product_snow p ON f.product_key = p.product_key
        JOIN dim_subcategory_snow sub ON p.subcategory_id = sub.subcategory_id
        JOIN dim_category_snow c ON sub.category_id = c.category_id
        JOIN dim_store_snow s ON f.store_key = s.store_key
        JOIN dim_region_snow r ON s.region_id = r.region_id
        GROUP BY c.category_name, r.region_name;
    """
    snow_times = []
    for _ in range(10):
        t0 = time.perf_counter()
        con.execute(snow_query).fetchall()
        t1 = time.perf_counter()
        snow_times.append((t1 - t0) * 1000.0)
    avg_snow_ms = round(sum(snow_times) / len(snow_times), 3)

    return {
        "fact_star_rows": fact_star_cnt,
        "fact_snow_rows": fact_snow_cnt,
        "customer_dimension": {
            "total_surrogate_records": cust_dim_cnt,
            "active_current_records": cust_current_cnt,
            "historical_scd2_records": cust_historical_cnt
        },
        "query_performance": {
            "star_schema_avg_ms": avg_star_ms,
            "snowflake_schema_avg_ms": avg_snow_ms,
            "star_join_count": 2,
            "snowflake_join_count": 5,
            "difference_pct": round(((avg_snow_ms - avg_star_ms) / avg_star_ms) * 100, 2) if avg_star_ms > 0 else 0
        }
    }
