import json
from pathlib import Path
from typing import Dict, List

def export_optimization_reports(benchmark_results: List[Dict], outputs_dir: Path, total_records: int):
    outputs_dir = Path(outputs_dir)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # 1. JSON Export
    with open(outputs_dir / "benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump({"total_dataset_rows": total_records, "queries": benchmark_results}, f, indent=2)

    # 2. Markdown Summary Report
    rows_md = ""
    for q in benchmark_results:
        rows_md += f"| **{q['query_name']}** | {q['baseline_time_ms']} ms | {q['optimized_time_ms']} ms | **{q['speedup_factor']}** | {q['row_count']} |\n"

    md_content = f"""# Practical 8: Query Processing and Optimization Benchmark Report

## 1. Executive Summary
- **Dataset Size:** {total_records:,} Clickstream Events
- **Engine:** DuckDB Columnar Vectorized Query Engine
- **Storage Modalities:** In-Memory Table, ART Indexing, Hive-Partitioned Parquet

## 2. Performance Comparison Table
| Benchmark Scenario | Baseline Runtime (ms) | Optimized Runtime (ms) | Speedup Factor | Result Rows |
|---------------------|-----------------------|------------------------|----------------|-------------|
{rows_md}

## 3. Optimization Techniques Applied
1. **Columnar Projection & Early Filter Pushdown:** Eliminates reading unwanted columns, filtering early in the physical scan operator before aggregation.
2. **Hive-Style Parquet Partition Pruning:** Replaces sequential scans across 60 days of logs by pruning 88%+ of the files, loading only the directory partitions matching the `event_date` predicate.
3. **Supplementary Refactoring (Correlated Subqueries -> Window Functions & CTEs):** Eliminates repeated $O(N \\times M)$ subquery scans by computing partition aggregates in a single vectorized pass.

## 4. Physical Execution Plan Highlights
```
{benchmark_results[2]['query_name']} (Supplementary Problem Refactoring)
Optimized Window Execution:
{benchmark_results[2]['optimized_plan_snippet']}
```
"""
    with open(outputs_dir / "query_optimization_report.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    # 3. Execution Plan Text Dumps
    with open(outputs_dir / "baseline_execution_plans.txt", "w", encoding="utf-8") as f:
        for q in benchmark_results:
            f.write(f"=== {q['query_name']} BASELINE PLAN ===\n{q['full_baseline_plan']}\n\n")

    with open(outputs_dir / "optimized_execution_plans.txt", "w", encoding="utf-8") as f:
        for q in benchmark_results:
            f.write(f"=== {q['query_name']} OPTIMIZED PLAN ===\n{q['full_optimized_plan']}\n\n")
