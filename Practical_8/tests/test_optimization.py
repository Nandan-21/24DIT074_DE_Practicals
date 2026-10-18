import sys
from pathlib import Path

PRAC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PRAC_DIR))

import pytest
import duckdb
from src.clickstream_generator import generate_clickstream_dataset
from src.db_manager import setup_analytical_database
from src.optimizer_benchmark import OptimizerBenchmark

@pytest.fixture(scope="module")
def setup_test_data(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("p8_test")
    csv_file = tmp_dir / "test_clickstream.csv"
    db_file = tmp_dir / "test_analytics.duckdb"
    part_dir = tmp_dir / "test_partitions"

    generate_clickstream_dataset(csv_file, num_records=2000, seed=123)
    con = setup_analytical_database(db_file, csv_file, part_dir)
    yield con, part_dir
    con.close()

def test_dataset_generation_and_counts(setup_test_data):
    con, _ = setup_test_data
    cnt = con.execute("SELECT COUNT(*) FROM raw_clickstream;").fetchone()[0]
    assert cnt == 2000

def test_query_1_result_validity(setup_test_data):
    con, _ = setup_test_data
    q_base = "SELECT region, COUNT(*) FROM raw_clickstream GROUP BY region ORDER BY region;"
    q_opt = "SELECT region, COUNT(*) FROM clickstream_indexed GROUP BY region ORDER BY region;"
    res1 = con.execute(q_base).fetchall()
    res2 = con.execute(q_opt).fetchall()
    assert res1 == res2

def test_supplementary_window_vs_subquery_equivalence(setup_test_data):
    con, _ = setup_test_data
    # Subquery calculation
    q_sub = """
    SELECT m.user_id, m.page_url, m.response_time_ms,
        (SELECT AVG(s.response_time_ms) FROM raw_clickstream s WHERE s.page_url = m.page_url) AS avg_page
    FROM raw_clickstream m
    WHERE m.response_time_ms > 400
    ORDER BY m.user_id, m.page_url, m.response_time_ms
    LIMIT 20;
    """
    # Window function calculation
    q_win = """
    WITH w AS (
        SELECT user_id, page_url, response_time_ms,
            AVG(response_time_ms) OVER(PARTITION BY page_url) AS avg_page
        FROM raw_clickstream
        WHERE response_time_ms > 400
    )
    SELECT user_id, page_url, response_time_ms, avg_page
    FROM w
    ORDER BY user_id, page_url, response_time_ms
    LIMIT 20;
    """
    sub_res = con.execute(q_sub).fetchall()
    win_res = con.execute(q_win).fetchall()
    assert len(sub_res) == len(win_res)
    # Check that response_time and user_id match
    for r1, r2 in zip(sub_res, win_res):
        assert r1[0] == r2[0] # user_id
        assert r1[1] == r2[1] # page_url
