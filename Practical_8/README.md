# Practical 8: Query Processing and Optimization

## 1. Title and Objective
**Title:** Analytical Query Optimization, Execution Plan Profiling, and Columnar Data Partitioning  
**Course Code:** ITUC301 – Data Engineering  
**Objective:** Execute complex analytical aggregation queries across high-cardinality multi-thousand/million row clickstream datasets, profile internal database execution plans (`EXPLAIN` / `EXPLAIN ANALYZE`), diagnose processing bottlenecks (such as full table linear disk scans and repeated subquery sorting overheads), and implement concrete optimizations including projection pushdown, ART indexing, date-based Parquet partition pruning, and Common Table Expression (CTE) / Window Function query refactoring.

---

## 2. Tools and Technologies Used
- **DuckDB (v1.x):** Embedded in-process analytical columnar database engine with vectorized execution.
- **Apache Parquet:** Columnar storage format supporting dictionary encoding and Hive-style directory partitioning.
- **Python 3.x (`duckdb`, `pandas`):** Dataset generation, automated benchmark harness, and execution plan parsing.
- **Pytest:** Automated test suite validating result set equivalence and performance constraints.

---

## 3. Optimization Architecture and Techniques

```
+-------------------------------------------------------------------------------------------------+
|                       150,000+ Record High-Cardinality Clickstream Stream                       |
+-------------------------------------------------------------------------------------------------+
                                      |
         +----------------------------+----------------------------+
         |                                                         |
         v                                                         v
   [UNOPTIMIZED]                                              [OPTIMIZED]
   Table: raw_clickstream                                     1. Columnar Projection Pushdown
   - Full linear sequential scan                              2. Secondary ART Indexing
   - Evaluates all row columns in memory                      3. Hive Partition Pruning (Parquet)
   - Correlated nested subqueries                             4. CTE + Window Functions (1-pass)
```

### Key Optimizations Demonstrated:
1. **Columnar Projection & Predicate Pushdown:** The query engine pushes filter predicates directly into the physical scan operator, avoiding decompression and memory loading of discarded rows and unselected columns.
2. **Hive-Style Parquet Partition Pruning:** Partitioning data by `event_date/` allows DuckDB's query planner to skip non-matching partition folders entirely, converting an $O(N)$ full table scan into targeted partition reads.
3. **Window Function Query Refactoring (Supplementary Problem):** Replaces $O(N \times M)$ correlated subquery scans with an $O(N \log N)$ single vectorized pass using `AVG(...) OVER(PARTITION BY page_url)` and `COUNT(...) OVER(PARTITION BY user_id)`.

---

## 4. Directory Structure
```
Practical_8/
├── data/                            # Synthetic clickstream CSV files
├── sql/
│   ├── baseline_queries.sql         # Unoptimized queries (full scans, subqueries)
│   └── optimized_queries.sql        # Optimized queries (indexes, partitions, windows)
├── src/
│   ├── clickstream_generator.py     # High-cardinality synthetic clickstream generator
│   ├── db_manager.py                # DuckDB setup and Parquet partitioning
│   ├── optimizer_benchmark.py       # Benchmark runner and EXPLAIN ANALYZE profiler
│   └── report_generator.py          # Markdown and JSON report generator
├── tests/
│   └── test_optimization.py         # Pytest automated verification suite
├── outputs/
│   ├── analytics.duckdb             # Persistent DuckDB database file
│   ├── partitioned_clickstream/     # Hive-partitioned Parquet files
│   ├── benchmark_results.json       # Measured execution statistics
│   ├── baseline_execution_plans.txt # Physical execution plans (baseline)
│   ├── optimized_execution_plans.txt# Physical execution plans (optimized)
│   └── query_optimization_report.md # Summary comparison report
├── requirements.txt                 # Dependencies (duckdb, pandas, pytest)
├── main.py                          # Benchmark entry point
└── README.md                        # Complete documentation
```

---

## 5. Execution Instructions

### A. Environment Setup
```powershell
# Activate project virtual environment
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r Practical_8\requirements.txt
```

### B. Run Full Benchmark & Plan Capture
```powershell
python Practical_8\main.py
```

### C. Run Automated Tests
```powershell
pytest Practical_8\tests\ -v
```

---

## 6. Answers to Key Evaluation Questions

### Question 1: Explain what a full table disk scan operation means within an execution plan, and describe its computational impact on large datasets.
- **Definition:** A full table disk scan (`SEQ_SCAN` in DuckDB/PostgreSQL) means the database storage engine reads every single page, block, and record from disk into memory buffers, evaluating filter predicates row by row or vector by vector.
- **Computational Impact on Large Datasets:**
  - **Severe I/O Bandwidth Consumption:** Saturates storage channel throughput by transferring gigabytes or terabytes of irrelevant data across the storage-compute bus.
  - **Buffer Cache Thrashing:** Displaces frequently accessed "hot" data from memory buffer pools (e.g., PostgreSQL `shared_buffers` or DuckDB memory manager) to make room for cold scan pages.
  - **High CPU Overhead:** Evaluates expressions across millions of tuples that are ultimately discarded by filter predicates.
  - **Linear Time Complexity ($O(N)$):** Execution latency scales linearly with table size, making real-time interactive analytics impossible without partitioning or indexes.

---

### Question 2: How does a columnar storage layout fundamentally change query processing and optimization compared to a traditional row-oriented layout?
- **Row-Oriented Layout (OLTP - e.g., standard PostgreSQL heap tables):**
  - Stores all column values for a single record contiguously on disk pages (`[id1, name1, date1, payload1], [id2, name2, ...]`).
  - Great for single-row inserts and point lookups by primary key, but analytical queries requesting only 2 columns out of 50 must still load the entire row from disk.
- **Columnar Storage Layout (OLAP - e.g., DuckDB, Parquet):**
  - Stores each column in separate, contiguous disk blocks (`[id1, id2, id3], [date1, date2, date3]`).
  - **Projection Pruning:** Queries selecting only 2 columns read **only those 2 column blocks**, reducing disk I/O by 80–95%.
  - **Superior Compression:** Identical data types stored together achieve 3x–10x higher compression ratios using Run-Length Encoding (RLE), Bit-Packing, and Dictionary Encoding.
  - **Vectorized SIMD Processing:** Modern CPUs process 1024-element column vectors in registers using SIMD instructions, achieving orders-of-magnitude faster arithmetic and aggregation.

---

### Question 3: What are the architectural costs and performance penalties associated with creating too many secondary indices on volatile, frequently updated database tables?
1. **Write Amplification (DML Degradation):** Every `INSERT`, `UPDATE`, or `DELETE` must synchronously traverse and update every affected secondary B-tree or ART index. A table with 10 secondary indexes turns a single row write into 11 discrete write operations.
2. **Lock Contention & Concurrency Bottlenecks:** Index page splits require exclusive latching, causing lock serialization during high-concurrency ingestion spikes.
3. **Storage Bloat:** Secondary indexes consume massive storage space (often exceeding the raw table size). In MVCC engines like PostgreSQL, dead index tuples generate substantial fragmentation requiring frequent vacuuming.
4. **Suboptimal Optimizer Choices:** A proliferation of overlapping indexes increases query planner complexity and risk of choosing an index scan when a sequential vectorized scan would be faster.

---

## 7. Supplementary Problem Implementation
**Requirement:** Take a highly nested SQL query containing multiple subqueries, profile its execution plan, and rewrite it using optimized Common Table Expressions (CTEs) or window functions to reduce execution costs.

**Implementation Details:**
- **Baseline Query:**
  ```sql
  SELECT m.user_id, m.page_url, m.response_time_ms,
      (SELECT AVG(s.response_time_ms) FROM raw_clickstream s WHERE s.page_url = m.page_url) AS avg_page_latency,
      (SELECT COUNT(*) FROM raw_clickstream s2 WHERE s2.user_id = m.user_id) AS total_user_events
  FROM raw_clickstream m
  WHERE m.device_type = 'mobile' AND m.response_time_ms > 500
  ORDER BY m.response_time_ms DESC LIMIT 50;
  ```
  *Bottleneck:* Evaluates correlated nested subqueries by repeatedly scanning `raw_clickstream` for each candidate record.
- **Optimized Rewrite (Window Functions & CTE):**
  ```sql
  WITH filtered_events AS (
      SELECT user_id, page_url, device_type, response_time_ms,
          AVG(response_time_ms) OVER(PARTITION BY page_url) AS avg_page_latency,
          COUNT(*) OVER(PARTITION BY user_id) AS total_user_events
      FROM clickstream_indexed
      WHERE device_type = 'mobile' AND response_time_ms > 500
  )
  SELECT user_id, page_url, device_type, response_time_ms, avg_page_latency, total_user_events
  FROM filtered_events ORDER BY response_time_ms DESC LIMIT 50;
  ```
- **Performance Impact:** Computes the analytical metrics in a **single linear pass** using vectorized hash partitions, eliminating repetitive table rescans and yielding a measured speedup factor over the unoptimized nested subquery version.
