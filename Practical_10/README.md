# Practical 10: Batch and Streaming Transformations

## 1. Title and Objective
**Title:** Dual-Paradigm Batch and Structured Streaming Transformation Pipelines with Event-Time Watermarking  
**Course Code:** ITUC301 – Data Engineering  
**Objective:** Implement comprehensive data transformation modules across both batch environments and streaming runtime pipelines using Apache Spark and PySpark. The transformation logic handles real-world IoT telemetry anomalies including conditional data filtering, null value handling, stream-static enrichment joins, multi-level rolling and tumbling window aggregations, and deterministic management of out-of-order and late-arriving events via event-time watermarking constraints.

---

## 2. Tools and Technologies Used
- **Apache Spark 4.x / PySpark:** Distributed batch and Structured Streaming processing engine.
- **Spark Structured Streaming Engine:** Micro-batch streaming architecture with incremental state management.
- **Apache Parquet:** High-performance columnar file format for analytical batch sinks.
- **Python Datetime & Window Functions:** Advanced time-series rolling and tumbling window operators.
- **Pytest:** Automated verification suite for batch and streaming pipelines.

---

## 3. Transformation Architecture

```
                                  [IoT Telemetry Data Stream]
                                               |
             +---------------------------------+---------------------------------+
             |                                                                   |
             v                                                                   v
     [BATCH PIPELINE]                                                 [STREAMING PIPELINE]
  5,000 Historical Records                                         Micro-batches (On-time & Late)
             |                                                                   |
  1. Cast schema & filter outliers                                 1. Ingest JSON Micro-batches
  2. Deduplicate (device_id, event_time)                           2. Apply .withWatermark("event_time", "10m")
  3. Broadcast join with device_metadata                           3. Stream-static join with device_metadata
  4. Rolling window: 4-point moving avg temp                       4. Tumbling (5m) & Sliding (5m/1m) windows
  5. Tumbling window: 15-min zone aggregations                     5. Discard events older than watermark
             |                                                                   |
             v                                                                   v
  [Output: outputs/batch_parquet/]                                 [Output: State Store & Checkpoint Log]
```

---

## 4. Directory Structure
```
Practical_10/
├── data/
│   ├── batch_telemetry.csv          # Synthetic batch IoT telemetry dataset
│   ├── device_metadata.csv          # Metadata for broadcast enrichment joins
│   ├── streaming_feed/              # Deterministic micro-batch test fixtures
│   └── fraud_feed/                  # Streaming financial transaction fixtures
├── src/
│   ├── batch_pipeline.py            # PySpark batch transformation module
│   ├── comparison_reporter.py       # Batch vs streaming analysis report compiler
│   ├── fraud_stream_detector.py     # Supplementary problem: rolling fraud detector
│   ├── metadata_generator.py        # Device metadata generator
│   ├── spark_session_factory.py     # Local SparkSession configuration factory
│   ├── streaming_pipeline.py        # Structured Streaming watermark pipeline
│   └── telemetry_generator.py       # Out-of-order & late-arriving event generator
├── tests/
│   └── test_transformations.py      # Automated PySpark test suite
├── outputs/
│   ├── batch_parquet/               # Generated Parquet analytical files
│   ├── checkpoints/                 # Structured streaming state checkpoint store
│   ├── fraud_checkpoints/           # Checkpoints for fraud streaming query
│   ├── batch_vs_streaming_report.md # Comprehensive comparative analysis
│   ├── fraud_alerts.json            # Detected velocity and volume fraud alerts
│   └── streaming_watermark_log.txt  # Execution logs showing watermark tracking
├── requirements.txt                 # Dependencies (pyspark, pandas, pyarrow, pytest)
├── main.py                          # Dual-pipeline execution entry point
└── README.md                        # Complete documentation
```

---

## 5. Execution Instructions

### A. Environment Setup
```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r Practical_10\requirements.txt
```

### B. Run Complete Dual Pipeline Demonstration
```powershell
python Practical_10\main.py
```

### C. Run Automated Tests
```powershell
pytest Practical_10\tests\ -v
```

---

## 6. Answers to Key Evaluation Questions

### Question 1: Explain how a streaming engine uses watermarks to differentiate between acceptable late-arriving data and obsolete records that should be dropped.
- **Watermark Definition:** A watermark is a dynamic moving threshold in event time defined as:
  $$\text{Watermark} = \max(\text{event\_time seen so far}) - \text{allowed\_delay}$$
- **Differentiating Data:**
  - **On-time and Acceptable Late Data:** If a record arrives with an event timestamp $T_{\text{event}} \ge \text{Watermark}$, the engine accepts it and updates the corresponding window aggregation in memory.
  - **Obsolete Data:** If a record arrives with an event timestamp $T_{\text{event}} < \text{Watermark}$, the engine considers the data past the tolerable delay threshold and drops it immediately.
- **State Store Pruning:** The primary purpose of the watermark is not just filtering; it is **limiting memory consumption**. Once the watermark advances past the end of a time window ($W_{\text{end}} \le \text{Watermark}$), the engine knows no more updates will arrive for that window, and it safely evicts the window's state from RAM/RocksDB, preventing out-of-memory crashes on continuous 24/7 streaming streams.

---

### Question 2: Compare the processing mechanics and memory footprints of a rolling window aggregation against a standard tumbling window block in streaming pipelines.
- **Tumbling Window (Fixed, Non-overlapping):**
  - **Structure:** E.g., `window("event_time", "5 minutes")` produces windows `[12:00-12:05)`, `[12:05-12:10)`.
  - **Mechanics:** Each event belongs to **exactly one window**.
  - **Memory Footprint:** Lean. The state store maintains only one state entry per grouping key per window. State is evicted as soon as the watermark advances past the window end.
- **Rolling / Sliding Window (Overlapping):**
  - **Structure:** E.g., `window("event_time", "5 minutes", "1 minute slide")` produces windows `[12:00-12:05)`, `[12:01-12:06)`, `[12:02-12:07)`, etc.
  - **Mechanics:** A single event falls into **multiple concurrent windows** (5 separate windows in this example). The engine must replicate the event's contribution across all active overlapping windows.
  - **Memory Footprint:** Substantially larger (proportional to $\frac{\text{window\_duration}}{\text{slide\_duration}}$). Intermediate states for all overlapping windows must remain buffered in memory until the watermark clears each window's end.

---

### Question 3: What are the primary structural and operational challenges encountered when joining a fast real-time event stream with a slow batch metadata table?
1. **Metadata Freshness & Cache Coherence:** Fast-moving events arrive in milliseconds, but device metadata (e.g., maintenance zone, firmware) is updated intermittently in a relational store. Stream-static joins evaluate the metadata as it existed when the micro-batch started. In-flight updates to metadata may not reflect immediately without explicit cache invalidation.
2. **Memory Scaling via Broadcast Joins:** To maintain low latency, the streaming engine broadcasts the static metadata table to all worker nodes (`broadcast(df_meta)`). If the metadata table grows from a few thousand devices to hundreds of millions, broadcasting exhausts worker JVM heap space.
3. **Out-of-Order Enrichment:** If an IoT event arrives for a newly provisioned sensor whose metadata record has not yet synced to the batch store, the inner join drops the event. Handling this requires left-outer joins, dead-letter queues, or watermarked stream-to-stream stateful joins.

---

## 7. Supplementary Problem Implementation
**Requirement:** Build a stream transformation block that detects fraud by calculating rolling, windowed transaction volume checks per user ID over 5-minute intervals.

**Implementation Details:**
- Implemented in `src/fraud_stream_detector.py`.
- Evaluates real-time financial transaction streams over a **5-minute sliding window with a 1-minute slide**:
  ```python
  rolling_volume = (
      stream_df
      .groupBy(window("tx_time", "5 minutes", "1 minute"), "user_id")
      .agg(count("*").alias("tx_count"), sum("amount").alias("total_volume_usd"))
      .filter((col("tx_count") >= 4) | (col("total_volume_usd") >= 4000.0))
  )
  ```
- **Alert Trigger:** Automatically triggers alerts when a user executes a high-velocity burst ($\ge 4$ transactions in 5 minutes) or a high-volume spike ($\ge \$4,000$).
- Output alerts are serialized with window boundaries and exported to `outputs/fraud_alerts.json`.
