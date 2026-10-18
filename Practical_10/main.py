import json
import sys
from pathlib import Path
from datetime import datetime

PRAC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PRAC_DIR))

from src.spark_session_factory import get_spark_session
from src.metadata_generator import generate_device_metadata
from src.telemetry_generator import (
    generate_batch_telemetry_dataset,
    generate_streaming_microbatches
)
from src.batch_pipeline import run_batch_transformation_pipeline
from src.streaming_pipeline import run_streaming_watermark_pipeline
from src.fraud_stream_detector import run_fraud_detection_streaming
from src.comparison_reporter import generate_comparison_report

def run_pipeline():
    print("=" * 70)
    print("PRACTICAL 10: BATCH AND STREAMING TRANSFORMATIONS")
    print("PySpark DataFrames, Structured Streaming, Watermarks & Fraud Detection")
    print("=" * 70)

    data_dir = PRAC_DIR / "data"
    feed_dir = data_dir / "streaming_feed"
    fraud_feed_dir = data_dir / "fraud_feed"
    outputs_dir = PRAC_DIR / "outputs"
    checkpoints_dir = outputs_dir / "checkpoints"
    fraud_checkpoints_dir = outputs_dir / "fraud_checkpoints"

    data_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    spark = get_spark_session()
    print("PySpark SparkSession initialized successfully.")

    try:
        # Step 1: Generate Device Metadata and Batch Telemetry
        print("\n[Step 1] Generating device metadata and synthetic batch telemetry...")
        meta_csv = data_dir / "device_metadata.csv"
        generate_device_metadata(meta_csv, num_devices=20)

        batch_csv = data_dir / "batch_telemetry.csv"
        generate_batch_telemetry_dataset(batch_csv, num_records=5000, seed=42)
        print(f"Generated {meta_csv.name} and {batch_csv.name} (5,000 records).")

        # Step 2: Execute Batch Pipeline
        print("\n[Step 2] Executing PySpark Batch Transformation Pipeline...")
        batch_parquet_dir = outputs_dir / "batch_parquet"
        df_batch_res = run_batch_transformation_pipeline(spark, batch_csv, meta_csv, batch_parquet_dir)
        batch_rows = df_batch_res.count()
        print(f"Batch transformation completed: generated {batch_rows} 15-minute zone aggregation rows.")
        print("Sample Batch Aggregations:")
        df_batch_res.show(4, truncate=False)

        # Step 3: Generate Streaming Micro-batches (On-time, Acceptable Late, Excessively Late)
        print("\n[Step 3] Preparing Structured Streaming micro-batch feed fixtures...")
        microbatches = generate_streaming_microbatches(feed_dir)
        print(f"Created {len(microbatches)} streaming micro-batch fixtures with on-time & late events.")

        # Step 4: Execute Structured Streaming Pipeline with Watermarks
        print("\n[Step 4] Running PySpark Structured Streaming Pipeline with 10-Minute Watermark...")
        log_file = outputs_dir / "streaming_watermark_log.txt"
        watermark_logs = run_streaming_watermark_pipeline(
            spark,
            feed_dir=feed_dir,
            metadata_csv=meta_csv,
            checkpoint_dir=checkpoints_dir,
            output_log_file=log_file
        )
        print(f"Streaming execution completed. Progress logs written to {log_file.name}.")

        # Step 5: Supplementary Problem - Streaming Fraud Detection
        print("\n[Step 5] Running Supplementary Streaming Fraud Detection Module...")
        fraud_feed_dir.mkdir(parents=True, exist_ok=True)
        # Create sample financial transactions in streaming feed
        tx_fixture = fraud_feed_dir / "tx_batch_01.json"
        base_tx_time = datetime(2026, 3, 1, 14, 0, 0)
        sample_txs = [
            {"transaction_id": "TX_01", "user_id": "USER_999", "amount": 1200.0, "transaction_timestamp": "2026-03-01 14:01:00"},
            {"transaction_id": "TX_02", "user_id": "USER_999", "amount": 1500.0, "transaction_timestamp": "2026-03-01 14:02:00"},
            {"transaction_id": "TX_03", "user_id": "USER_999", "amount": 1800.0, "transaction_timestamp": "2026-03-01 14:03:00"},
            {"transaction_id": "TX_04", "user_id": "USER_999", "amount": 950.0, "transaction_timestamp": "2026-03-01 14:04:00"},
            {"transaction_id": "TX_05", "user_id": "USER_888", "amount": 6500.0, "transaction_timestamp": "2026-03-01 14:02:30"},
            {"transaction_id": "TX_06", "user_id": "USER_111", "amount": 45.0, "transaction_timestamp": "2026-03-01 14:02:45"},
        ]
        with open(tx_fixture, "w", encoding="utf-8") as f:
            for tx in sample_txs:
                f.write(json.dumps(tx) + "\n")

        alerts_file = outputs_dir / "fraud_alerts.json"
        fraud_alerts = run_fraud_detection_streaming(
            spark,
            transactions_feed_dir=fraud_feed_dir,
            checkpoint_dir=fraud_checkpoints_dir,
            output_alerts_file=alerts_file
        )
        print(f"Detected {len(fraud_alerts)} streaming fraud alerts: {json.dumps(fraud_alerts, indent=2)}")

        # Step 6: Generate Comparison Report
        print("\n[Step 6] Compiling Batch vs Streaming Comparative Analysis Report...")
        report_file = outputs_dir / "batch_vs_streaming_report.md"
        generate_comparison_report(report_file, batch_rows=5000, streaming_watermark_logs=watermark_logs)
        print(f"Report successfully saved to {report_file}")

        print("=" * 70)
        print("PRACTICAL 10 EXECUTION COMPLETE")
        print("=" * 70)
    finally:
        spark.stop()

if __name__ == "__main__":
    run_pipeline()
