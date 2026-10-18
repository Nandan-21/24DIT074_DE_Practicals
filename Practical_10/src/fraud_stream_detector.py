import json
from pathlib import Path
from typing import Dict, List
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum, to_timestamp, window
from pyspark.sql.types import (
    DoubleType, StringType, StructField, StructType
)

def run_fraud_detection_streaming(
    spark: SparkSession,
    transactions_feed_dir: Path,
    checkpoint_dir: Path,
    output_alerts_file: Path
) -> List[Dict]:
    """
    Supplementary Problem:
    Builds a stream transformation block that detects financial fraud by calculating
    rolling, windowed transaction volume checks per user_id over 5-minute intervals with a 1-minute slide.
    Flags high-frequency bursts (>= 5 tx in 5 mins) or large velocity amounts (>= $5000).
    """
    schema = StructType([
        StructField("transaction_id", StringType(), True),
        StructField("user_id", StringType(), True),
        StructField("amount", DoubleType(), True),
        StructField("transaction_timestamp", StringType(), True)
    ])

    stream_df = (
        spark.readStream
        .schema(schema)
        .json(transactions_feed_dir.as_posix())
        .withColumn("tx_time", to_timestamp("transaction_timestamp", "yyyy-MM-dd HH:mm:ss"))
        .withWatermark("tx_time", "5 minutes")
    )

    # 5-minute rolling window with 1-minute slide
    rolling_volume = (
        stream_df
        .groupBy(
            window("tx_time", "5 minutes", "1 minute"),
            "user_id"
        )
        .agg(
            count("*").alias("tx_count"),
            sum("amount").alias("total_volume_usd")
        )
        # Alert filter: velocity burst >= 4 transactions OR total volume >= $4000
        .filter((col("tx_count") >= 4) | (col("total_volume_usd") >= 4000.0))
    )

    query = (
        rolling_volume
        .writeStream
        .queryName("fraud_alerts")
        .format("memory")
        .outputMode("update")
        .option("checkpointLocation", checkpoint_dir.as_posix())
        .start()
    )

    query.processAllAvailable()

    alerts_df = spark.sql("""
        SELECT 
            window.start AS window_start,
            window.end AS window_end,
            user_id,
            tx_count,
            ROUND(total_volume_usd, 2) AS total_volume_usd
        FROM fraud_alerts
        ORDER BY window.start, tx_count DESC
    """).toPandas()

    alerts = alerts_df.to_dict(orient="records")

    # Serialize window timestamps to string for json export
    formatted_alerts = []
    for a in alerts:
        formatted_alerts.append({
            "window_start": str(a["window_start"]),
            "window_end": str(a["window_end"]),
            "user_id": str(a["user_id"]),
            "tx_count": int(a["tx_count"]),
            "total_volume_usd": float(a["total_volume_usd"]),
            "alert_reason": "VELOCITY_BURST" if a["tx_count"] >= 4 else "HIGH_VOLUME_SPIKE"
        })

    with open(output_alerts_file, "w", encoding="utf-8") as f:
        json.dump(formatted_alerts, f, indent=2)

    query.stop()
    return formatted_alerts
