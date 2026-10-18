import json
import sys
from pathlib import Path

PRAC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PRAC_DIR))

import pytest
from src.spark_session_factory import get_spark_session
from src.metadata_generator import generate_device_metadata
from src.telemetry_generator import (
    generate_batch_telemetry_dataset,
    generate_streaming_microbatches
)
from src.batch_pipeline import run_batch_transformation_pipeline
from src.fraud_stream_detector import run_fraud_detection_streaming

@pytest.fixture(scope="module")
def spark_session():
    spark = get_spark_session("PySpark_Test_Session")
    yield spark
    spark.stop()

def test_batch_transformation_pipeline(spark_session, tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("p10_batch_test")
    meta_csv = tmp_dir / "meta.csv"
    data_csv = tmp_dir / "data.csv"
    out_parquet = tmp_dir / "out_parquet"

    generate_device_metadata(meta_csv, num_devices=5)
    generate_batch_telemetry_dataset(data_csv, num_records=200, seed=123)

    df_out = run_batch_transformation_pipeline(spark_session, data_csv, meta_csv, out_parquet)
    assert df_out.count() > 0
    # Verify columns exist
    cols = df_out.columns
    assert "window" in cols
    assert "facility_zone" in cols
    assert "avg_temp" in cols
    assert "telemetry_events" in cols

def test_fraud_stream_detector(spark_session, tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("p10_fraud_test")
    feed_dir = tmp_dir / "feed"
    chk_dir = tmp_dir / "chk"
    alerts_file = tmp_dir / "alerts.json"
    feed_dir.mkdir(parents=True, exist_ok=True)

    txs = [
        {"transaction_id": "T1", "user_id": "U100", "amount": 1000.0, "transaction_timestamp": "2026-03-01 10:00:00"},
        {"transaction_id": "T2", "user_id": "U100", "amount": 1000.0, "transaction_timestamp": "2026-03-01 10:01:00"},
        {"transaction_id": "T3", "user_id": "U100", "amount": 1000.0, "transaction_timestamp": "2026-03-01 10:02:00"},
        {"transaction_id": "T4", "user_id": "U100", "amount": 1500.0, "transaction_timestamp": "2026-03-01 10:03:00"}, # 4th tx in 3 mins -> alert!
        {"transaction_id": "T5", "user_id": "U200", "amount": 5500.0, "transaction_timestamp": "2026-03-01 10:01:30"}, # High single volume -> alert!
        {"transaction_id": "T6", "user_id": "U300", "amount": 20.0, "transaction_timestamp": "2026-03-01 10:02:00"},
    ]
    with open(feed_dir / "batch.json", "w", encoding="utf-8") as f:
        for t in txs:
            f.write(json.dumps(t) + "\n")

    alerts = run_fraud_detection_streaming(spark_session, feed_dir, chk_dir, alerts_file)
    assert len(alerts) >= 2
    users_alerted = {a["user_id"] for a in alerts}
    assert "U100" in users_alerted
    assert "U200" in users_alerted
    assert "U300" not in users_alerted
