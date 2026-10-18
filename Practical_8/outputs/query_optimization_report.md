# Practical 8: Query Processing and Optimization Benchmark Report

## 1. Executive Summary
- **Dataset Size:** 150,000 Clickstream Events
- **Engine:** DuckDB Columnar Vectorized Query Engine
- **Storage Modalities:** In-Memory Table, ART Indexing, Hive-Partitioned Parquet

## 2. Performance Comparison Table
| Benchmark Scenario | Baseline Runtime (ms) | Optimized Runtime (ms) | Speedup Factor | Result Rows |
|---------------------|-----------------------|------------------------|----------------|-------------|
| **Query 1 (High-Cardinality Aggregation)** | 28.418 ms | 10.375 ms | **2.74x** | 75 |
| **Query 2 (Partition Pruning vs Full Scan)** | 3.966 ms | 8.723 ms | **0.45x** | 40 |
| **Query 3 (Nested Subqueries vs CTE/Window)** | 35.062 ms | 21.567 ms | **1.63x** | 50 |


## 3. Optimization Techniques Applied
1. **Columnar Projection & Early Filter Pushdown:** Eliminates reading unwanted columns, filtering early in the physical scan operator before aggregation.
2. **Hive-Style Parquet Partition Pruning:** Replaces sequential scans across 60 days of logs by pruning 88%+ of the files, loading only the directory partitions matching the `event_date` predicate.
3. **Supplementary Refactoring (Correlated Subqueries -> Window Functions & CTEs):** Eliminates repeated $O(N \times M)$ subquery scans by computing partition aggregates in a single vectorized pass.

## 4. Physical Execution Plan Highlights
```
Query 3 (Nested Subqueries vs CTE/Window) (Supplementary Problem Refactoring)
Optimized Window Execution:
┌───────────────────────────┐
│           TOP_N           │
│    ────────────────────   │
│          Top: 50          │
│                           │
│         Order By:         │
│      filtered_events      │
│   .response_time_ms DESC  │
└─────────────┬─────────────┘
┌─────────────┴─────────────┐
│         PROJECTION        │
│    ────────────────────   │
│          user_id          │
│          page_url         │
│        device_type        │
│      response_time_ms     │
│      avg_page_late...
```
