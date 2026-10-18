# Practical 10: Batch vs Streaming Transformations Comparative Analysis

## 1. Executive Summary
- **Framework:** Apache Spark 4.x / PySpark Engine
- **Batch Processing Scope:** 5,000 Historical IoT Telemetry Records
- **Streaming Processing Scope:** Structured Streaming Micro-batches with 10-Minute Event-Time Watermark

## 2. Architectural Comparison Matrix
| Architectural Dimension | PySpark Batch Pipeline | PySpark Structured Streaming Pipeline |
|-------------------------|------------------------|---------------------------------------|
| **Execution Trigger** | Scheduled cron / orchestrator interval | Micro-batch trigger (continuous / available-now) |
| **Data Bound** | Bounded dataset (fixed file / table snapshot) | Unbounded continuous data stream |
| **Processing Latency** | Minutes to hours | Sub-second to few seconds |
| **State Management** | Stateless between runs (entire dataset re-evaluated) | Stateful RocksDB / HDFS state store maintained across micro-batches |
| **Event Time Handling** | Simple `GROUP BY` on static timestamps | Dynamic `.withWatermark()` + tumbling/sliding window tracking |
| **Late Data Handling** | Naturally included if present in input files | Evaluated against watermark: on-time & within watermark retained; beyond dropped |
| **Enrichment Joins** | Static-to-static distributed broadcast hash join | Stream-to-static lookup join against broadcasted device metadata |
| **Fault Recovery** | Idempotent full pipeline re-run from source | Checkpointed write-ahead log (WAL) and state store recovery |

## 3. Watermark Behavior and Late Data Eviction Analysis
- **Configured Watermark:** 10 minutes (`withWatermark("event_time", "10 minutes")`)
- **Watermark Mechanism:** Watermark is computed as max(event_time seen so far) - 10 minutes.
- **Late Event Classification:**
  1. **On-time events:** Ingested and updated in the corresponding 5-minute tumbling window.
  2. **Acceptable late events (within 10m):** Arriving out of order, but timestamp >= current watermark. State store updates the historical window in memory.
  3. **Excessively late events (> 10m):** Arriving with event timestamp older than the watermark. The streaming engine discards the record immediately without evicting or updating closed window state.

## 4. Supplementary Fraud Detection Stream Summary
- **Window Strategy:** 5-minute sliding window with 1-minute slide interval.
- **Rule Engine:** Detects transaction velocity bursts (>= 4 transactions/window) and high-volume surges (>= $4,000).
