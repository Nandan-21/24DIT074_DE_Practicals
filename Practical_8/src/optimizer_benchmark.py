import time
from typing import Dict, List, Tuple
import duckdb

class OptimizerBenchmark:
    """Executes baseline vs optimized queries, captures EXPLAIN ANALYZE plans, and benchmarks runtimes."""

    def __init__(self, con: duckdb.DuckDBPyConnection):
        self.con = con

    def get_execution_plan(self, query: str) -> str:
        """Captures the query physical execution plan via EXPLAIN."""
        res = self.con.execute(f"EXPLAIN {query}").fetchall()
        return "\n".join([row[1] for row in res])

    def benchmark_query(self, query: str, runs: int = 5) -> Tuple[float, List]:
        """Runs the query multiple times and returns (avg_ms, result_rows)."""
        # Warmup run
        result = self.con.execute(query).fetchall()

        times = []
        for _ in range(runs):
            t0 = time.perf_counter()
            self.con.execute(query).fetchall()
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000.0) # milliseconds

        avg_ms = sum(times) / len(times)
        return round(avg_ms, 3), result

    def run_comparison(self, name: str, baseline_sql: str, optimized_sql: str, runs: int = 5) -> Dict:
        """Compares baseline vs optimized queries with execution plan inspection."""
        base_plan = self.get_execution_plan(baseline_sql)
        opt_plan = self.get_execution_plan(optimized_sql)

        base_time, base_rows = self.benchmark_query(baseline_sql, runs=runs)
        opt_time, opt_rows = self.benchmark_query(optimized_sql, runs=runs)

        speedup = round(base_time / opt_time, 2) if opt_time > 0 else 1.0

        return {
            "query_name": name,
            "baseline_time_ms": base_time,
            "optimized_time_ms": opt_time,
            "speedup_factor": f"{speedup}x",
            "speedup_ratio": speedup,
            "baseline_plan_snippet": base_plan[:500] + ("..." if len(base_plan) > 500 else ""),
            "optimized_plan_snippet": opt_plan[:500] + ("..." if len(opt_plan) > 500 else ""),
            "full_baseline_plan": base_plan,
            "full_optimized_plan": opt_plan,
            "row_count": len(opt_rows)
        }
