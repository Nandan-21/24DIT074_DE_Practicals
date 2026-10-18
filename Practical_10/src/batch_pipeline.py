from pathlib import Path
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    avg, broadcast, col, count, max, min, round, to_timestamp, when, window
)
from pyspark.sql.window import Window

def run_batch_transformation_pipeline(
    spark: SparkSession,
    telemetry_csv: Path,
    metadata_csv: Path,
    output_parquet: Path
) -> DataFrame:
    """
    Executes PySpark batch transformation pipeline:
    - Type casting & validation
    - Null handling & duplicate removal
    - Metadata broadcast enrichment join
    - Rolling window & tumbling window aggregations
    - Output to Parquet format
    """
    # 1. Load telemetry
    df_raw = spark.read.option("header", "true").csv(telemetry_csv.as_posix())

    # 2. Schema casting & validation
    df_clean = (
        df_raw
        .withColumn("event_time", to_timestamp("event_timestamp", "yyyy-MM-dd HH:mm:ss"))
        .withColumn("ingest_time", to_timestamp("ingestion_timestamp", "yyyy-MM-dd HH:mm:ss"))
        .withColumn("temp_c", col("temperature_celsius").cast("double"))
        .withColumn("vibe_hz", col("vibration_hz").cast("double"))
        .withColumn("power_w", col("power_watts").cast("double"))
        # Filter invalid nulls or extreme out-of-range sensor spikes
        .filter(col("temp_c").isNotNull() & (col("temp_c") >= -20.0) & (col("temp_c") <= 120.0))
        .filter(col("power_w") > 0.0)
        .dropDuplicates(["device_id", "event_time"])
    )

    # 3. Load device metadata & perform broadcast enrichment join
    df_meta = spark.read.option("header", "true").csv(metadata_csv.as_posix())
    df_enriched = df_clean.join(broadcast(df_meta), on="device_id", how="inner")

    # 4. Multi-level windowed aggregations:
    # 4a. Rolling window: 4-point moving average temperature per device
    dev_window = Window.partitionBy("device_id").orderBy("event_time").rowsBetween(-3, 0)
    df_rolling = df_enriched.withColumn("rolling_avg_temp", round(avg("temp_c").over(dev_window), 2))

    # 4b. Tumbling window: 15-minute zone aggregations
    df_zone_tumbling = (
        df_rolling
        .groupBy(
            window("event_time", "15 minutes"),
            "facility_zone"
        )
        .agg(
            count("*").alias("telemetry_events"),
            round(avg("temp_c"), 2).alias("avg_temp"),
            round(max("temp_c"), 2).alias("max_temp"),
            round(avg("vibe_hz"), 2).alias("avg_vibration"),
            round(avg("power_w"), 2).alias("avg_power")
        )
        .orderBy("window.start", "facility_zone")
    )

    # 5. Write to Parquet
    output_parquet = Path(output_parquet)
    df_zone_tumbling.write.mode("overwrite").parquet(output_parquet.as_posix())

    return df_zone_tumbling
