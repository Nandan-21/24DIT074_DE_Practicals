import sys
from pathlib import Path

PRAC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PRAC_DIR))

from src.clickstream_generator import generate_clickstream_dataset
from src.db_manager import setup_analytical_database
from src.optimizer_benchmark import OptimizerBenchmark
from src.report_generator import export_optimization_reports

def run_pipeline():
    print("=" * 70)
    print("PRACTICAL 8: QUERY PROCESSING AND OPTIMIZATION")
    print("Execution Plan Profiling, Indexing, Partition Pruning & CTEs")
    print("=" * 70)

    data_dir = PRAC_DIR / "data"
    outputs_dir = PRAC_DIR / "outputs"
    data_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    csv_path = data_dir / "clickstream.csv"
    db_path = outputs_dir / "analytics.duckdb"
    parquet_partition_dir = outputs_dir / "partitioned_clickstream"

    # Step 1: Generate Clickstream Data
    num_records = 150000
    print(f"\n[Step 1] Generating {num_records:,} synthetic clickstream records...")
    generate_clickstream_dataset(csv_path, num_records=num_records, seed=42)
    print(f"Generated {csv_path} ({csv_path.stat().st_size / (1024*1024):.2f} MB)")

    # Step 2: Initialize DuckDB & Partitioned Storage
    print("\n[Step 2] Initializing DuckDB and partitioning Parquet files...")
    con = setup_analytical_database(db_path, csv_path, parquet_partition_dir)
    print("DuckDB tables (raw_clickstream, clickstream_indexed) and partitioned Parquet created.")

    # Step 3: Benchmarking
    print("\n[Step 3] Executing Query Benchmarks with Execution Plan Capture...")
    benchmark = OptimizerBenchmark(con)
    results = []

    # Scenario 1: Aggregation & Projection
    q1_base = """
    SELECT region, device_type, event_type, COUNT(*) AS total_events, COUNT(DISTINCT user_id) AS unique_users, AVG(response_time_ms) AS avg_time
    FROM raw_clickstream WHERE response_time_ms > 100
    GROUP BY region, device_type, event_type ORDER BY total_events DESC;
    """
    q1_opt = """
    SELECT region, device_type, event_type, COUNT(*) AS total_events, APPROX_COUNT_DISTINCT(user_id) AS unique_users, AVG(response_time_ms) AS avg_time
    FROM clickstream_indexed WHERE response_time_ms > 100
    GROUP BY region, device_type, event_type ORDER BY total_events DESC;
    """
    print("  -> Benchmarking Query 1: High-Cardinality Multi-Stage Aggregation...")
    res1 = benchmark.run_comparison("Query 1 (High-Cardinality Aggregation)", q1_base, q1_opt, runs=5)
    results.append(res1)
    print(f"     Baseline: {res1['baseline_time_ms']} ms | Optimized: {res1['optimized_time_ms']} ms | Speedup: {res1['speedup_factor']}")

    # Scenario 2: Partition Pruning
    q2_base = """
    SELECT region, event_date, COUNT(*) as daily_events, AVG(response_time_ms) as avg_latency
    FROM raw_clickstream WHERE event_date BETWEEN '2026-01-10' AND '2026-01-17'
    GROUP BY region, event_date ORDER BY region, event_date;
    """
    parquet_glob = (parquet_partition_dir / "**" / "*.parquet").as_posix()
    q2_opt = f"""
    SELECT region, event_date, COUNT(*) as daily_events, AVG(response_time_ms) as avg_latency
    FROM read_parquet('{parquet_glob}', hive_partitioning=1)
    WHERE event_date BETWEEN '2026-01-10' AND '2026-01-17'
    GROUP BY region, event_date ORDER BY region, event_date;
    """
    print("  -> Benchmarking Query 2: Date-Range Filter (Linear Scan vs Hive Partition Pruning)...")
    res2 = benchmark.run_comparison("Query 2 (Partition Pruning vs Full Scan)", q2_base, q2_opt, runs=5)
    results.append(res2)
    print(f"     Baseline: {res2['baseline_time_ms']} ms | Optimized: {res2['optimized_time_ms']} ms | Speedup: {res2['speedup_factor']}")

    # Scenario 3: Supplementary Problem - Correlated Subqueries vs Window Functions
    q3_base = """
    SELECT m.user_id, m.page_url, m.device_type, m.response_time_ms,
        (SELECT AVG(s.response_time_ms) FROM raw_clickstream s WHERE s.page_url = m.page_url) AS avg_page_latency,
        (SELECT COUNT(*) FROM raw_clickstream s2 WHERE s2.user_id = m.user_id) AS total_user_events
    FROM raw_clickstream m
    WHERE m.device_type = 'mobile' AND m.response_time_ms > 500
    ORDER BY m.response_time_ms DESC LIMIT 50;
    """
    q3_opt = """
    WITH filtered_events AS (
        SELECT user_id, page_url, device_type, response_time_ms,
            AVG(response_time_ms) OVER(PARTITION BY page_url) AS avg_page_latency,
            COUNT(*) OVER(PARTITION BY user_id) AS total_user_events
        FROM clickstream_indexed
        WHERE device_type = 'mobile' AND response_time_ms > 500
    )
    SELECT user_id, page_url, device_type, response_time_ms, avg_page_latency, total_user_events
    FROM filtered_events ORDER BY response_time_ms DESC LIMIT 50;
    """
    print("  -> Benchmarking Query 3 (Supplementary): Nested Subqueries vs Window Functions...")
    res3 = benchmark.run_comparison("Query 3 (Nested Subqueries vs CTE/Window)", q3_base, q3_opt, runs=3)
    results.append(res3)
    print(f"     Baseline: {res3['baseline_time_ms']} ms | Optimized: {res3['optimized_time_ms']} ms | Speedup: {res3['speedup_factor']}")

    # Step 4: Export Reports
    print("\n[Step 4] Exporting Reports & Execution Plans...")
    export_optimization_reports(results, outputs_dir, total_records=num_records)
    con.close()
    print(f"Reports and plans generated in {outputs_dir}")
    print("=" * 70)
    print("PRACTICAL 8 EXECUTION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    run_pipeline()
