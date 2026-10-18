import os
from pathlib import Path
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection(user: Optional[str] = None, password: Optional[str] = None):
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = int(os.getenv("POSTGRES_PORT", 5432))
    database = os.getenv("POSTGRES_DB", "cdc_db")
    db_user = user or os.getenv("POSTGRES_USER", "postgres")
    db_pass = password or os.getenv("POSTGRES_PASSWORD", "postgres")

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=database,
        user=db_user,
        password=db_pass
    )
    conn.autocommit = False
    return conn

def execute_sql_file(sql_file_path: Path):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            with open(sql_file_path, "r", encoding="utf-8") as f:
                cur.execute(f.read())
        conn.commit()
    finally:
        conn.close()
