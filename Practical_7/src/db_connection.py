import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path

def get_connection(retries: int = 5, delay: int = 2):
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = int(os.getenv("POSTGRES_PORT", 5432))
    database = os.getenv("POSTGRES_DB", "cdc_db")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")

    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=database,
                user=user,
                password=password
            )
            conn.autocommit = False
            return conn
        except psycopg2.OperationalError as e:
            if attempt == retries:
                raise e
            time.sleep(delay)

def initialize_database(sql_file_path: Path):
    """Executes the DDL script to create tables and triggers."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            with open(sql_file_path, "r", encoding="utf-8") as f:
                cur.execute(f.read())
        conn.commit()
    finally:
        conn.close()
