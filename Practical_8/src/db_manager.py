from pathlib import Path
import duckdb

def setup_analytical_database(db_path: Path, csv_path: Path, parquet_partition_dir: Path) -> duckdb.DuckDBPyConnection:
    """
    Initializes DuckDB database with baseline unpartitioned table,
    indexed table, and date-partitioned Parquet datasets.
    """
    con = duckdb.connect(str(db_path))

    # 1. Baseline unindexed table
    con.execute("DROP TABLE IF EXISTS raw_clickstream;")
    con.execute(f"""
        CREATE TABLE raw_clickstream AS
        SELECT 
            event_id,
            user_id,
            session_id,
            event_type,
            page_url,
            device_type,
            region,
            response_time_ms,
            CAST(event_date AS DATE) AS event_date,
            CAST(event_timestamp AS TIMESTAMP) AS event_timestamp
        FROM read_csv_auto('{csv_path.as_posix()}');
    """)

    # 2. Table with secondary ART indexes
    con.execute("DROP TABLE IF EXISTS clickstream_indexed;")
    con.execute("CREATE TABLE clickstream_indexed AS SELECT * FROM raw_clickstream;")
    con.execute("CREATE INDEX idx_user_id ON clickstream_indexed(user_id);")
    con.execute("CREATE INDEX idx_event_date ON clickstream_indexed(event_date);")
    con.execute("CREATE INDEX idx_page_url ON clickstream_indexed(page_url);")

    # 3. Partitioned Parquet dataset (partitioned by event_date)
    parquet_partition_dir.mkdir(parents=True, exist_ok=True)
    con.execute(f"""
        COPY raw_clickstream TO '{parquet_partition_dir.as_posix()}' 
        (FORMAT PARQUET, PARTITION_BY (event_date), OVERWRITE_OR_IGNORE 1);
    """)

    return con
