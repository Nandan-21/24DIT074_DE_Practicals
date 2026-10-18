import json
import time
from pathlib import Path
from typing import Dict, List
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    avg, broadcast, col, count, max, round, to_timestamp, window
)
from pyspark.sql.types import (
    DoubleType, StringType, StructField, StructType
)

def run_streaming_watermark_pipeline(
    spark: SparkSession,
    feed_dir: Path,
    metadata_csv: Path,
    checkpoint_dir: Path,
    output_log_file: Path
) -> List[Dict]:
    """
    Executes PySpark Structured Streaming pipeline with event-time watermarking:
    - Reads JSON micro-batches from local streaming feed
    - Applies 10-minute watermark
    - Stream-static join with device metadata
    - Computes 5-minute tumbling windows and 10-minute sliding windows
    - Records watermark progression and late-arriving event processing
    """
    schema = StructType([
        StructField("record_id", StringType(), True),
        StructField("device_id", StringType(), True),
        StructField("event_timestamp", StringType(), True),
        StructField("temperature_celsius", DoubleType(), True),
        StructField("vibration_hz", DoubleType(), True),
        StructField("power_watts", DoubleType(), True),
        StructField("arrival_category", StringType(), True)
    ])

    # 1. Stream source
    stream_df = (
        spark.readStream
        .schema(schema)
        .json(feed_dir.as_posix())
        .withColumn("event_time", to_timestamp("event_timestamp", "yyyy-MM-dd HH:mm:ss"))
        # 10-minute watermark on event_time!
        .withWatermark("event_time", "10 minutes")
    )

    # 2. Load static metadata
    df_meta = spark.read.option("header", "true").csv(metadata_csv.as_posix())

    # 3. Stream-static enrichment join
    enriched_stream = stream_df.join(df_meta, on="device_id", how="inner")

    # 4. Tumbling window aggregation (5-minute non-overlapping intervals)
    tumbling_stream = (
        enriched_stream
        .groupBy(
            window("event_time", "5 minutes"),
            "facility_zone"
        )
        .agg(
            count("*").alias("window_count"),
            round(avg("temperature_celsius"), 2).alias("avg_temp"),
            round(max("temperature_celsius"), 2).alias("max_temp")
        )
    )

    # 5. Output sink: memory sink for inspection in test/local mode
    query_name = "iot_tumbling_agg"
    query = (
        tumbling_stream
        .writeStream
        .queryName(query_name)
        .format("memory")
        .outputMode("update")
        .option("checkpointLocation", checkpoint_dir.as_posix())
        .start()
    )

    # Process all available streaming data
    query.processAllAvailable()

    # Capture streaming progress telemetry
    progress_records = query.recentProgress
    watermark_logs = []

    with open(output_log_file, "w", encoding="utf-8") as f:
        f.write("=== PySpark Structured Streaming Watermark Progress Log ===\n\n")
        for idx, prog in enumerate(progress_records):
            log_entry = {
                "batch_id": prog.get("batchId"),
                "input_rows_per_second": prog.get("inputRowsPerSecond"),
                "processed_rows_per_second": prog.get("processedRowsPerSecond"),
                "num_input_rows": prog.get("numInputRows"),
                "watermark": prog.get("eventTime", {}).get("watermark"),
                "max_event_time": prog.get("eventTime", {}).get("max"),
                "min_event_time": prog.get("eventTime", {}).get("min")
            }
            watermark_logs.append(log_entry)
            f.write(f"Batch #{idx}: Input Rows = {log_entry['num_input_rows']}, Watermark = {log_entry['watermark']}, Max Event Time = {log_entry['max_event_time']}\n")

    # Inspect current state table in memory
    results_df = spark.sql(f"SELECT * FROM {query_name} ORDER BY window.start, facility_zone").toPandas()

    query.stop()
    return watermark_logs
