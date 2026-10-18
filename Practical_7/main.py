import json
import sys
from pathlib import Path

PRAC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PRAC_DIR))

from src.db_connection import initialize_database, get_connection
from src.transaction_generator import (
    seed_initial_inventory,
    simulate_stock_updates,
    simulate_item_deletions
)
from src.cdc_consumer import CDCConsumer
from src.verifier import verify_source_target_consistency

def run_cdc_pipeline():
    print("=" * 70)
    print("PRACTICAL 7: CHANGE DATA CAPTURE (CDC)")
    print("Trigger-Based Incremental Replication with Row-Version Deduplication")
    print("=" * 70)

    outputs_dir = PRAC_DIR / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    sql_file = PRAC_DIR / "sql" / "01_init_cdc_schema.sql"

    # Step 1: Initialize Database Schema
    print("\n[Step 1] Initializing PostgreSQL Tables, Triggers, and CDC Ledger...")
    try:
        initialize_database(sql_file)
        print("Database schema and PL/pgSQL triggers initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to connect/initialize PostgreSQL: {e}")
        print("Please ensure the PostgreSQL container is running: docker compose -f Practical_7/docker-compose.yml up -d")
        sys.exit(1)

    # Step 2: Seed Initial Inventory (INSERT operations)
    print("\n[Step 2] Seeding initial inventory (Simulating INSERT operations)...")
    item_ids = seed_initial_inventory(num_items=25)
    print(f"Inserted {len(item_ids)} inventory records. Trigger captured INSERT events into cdc_audit_ledger.")

    # Step 3: Simulate Real-Time Updates (UPDATE operations)
    print("\n[Step 3] Simulating rapid inventory fluctuations (UPDATE operations)...")
    updates_count = simulate_stock_updates(item_ids, num_updates=20)
    print(f"Executed {updates_count} updates. Trigger bumped row_version and captured UPDATE events.")

    # Step 4: Simulate Record Purges (DELETE operations)
    print("\n[Step 4] Simulating item discontinuations (DELETE operations)...")
    deleted_ids = simulate_item_deletions(item_ids, num_deletes=4)
    print(f"Deleted {len(deleted_ids)} items (IDs: {deleted_ids}). Trigger captured DELETE events.")

    # Step 5: Check Captured Audit Ledger Status
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT operation, COUNT(*) FROM cdc_audit_ledger GROUP BY operation;")
            ledger_stats = dict(cur.fetchall())
            cur.execute("SELECT COUNT(*) FROM cdc_audit_ledger WHERE is_processed = FALSE;")
            pending_count = cur.fetchone()[0]
    finally:
        conn.close()

    print(f"\n[Step 5] CDC Audit Ledger Snapshot:")
    for op, cnt in ledger_stats.items():
        print(f"  - {op:8s}: {cnt} captured")
    print(f"  Pending unprocessed events: {pending_count}")

    # Step 6: Run CDC Consumer Replication
    print("\n[Step 6] Running CDC Consumer to replicate events to analytical_inventory...")
    consumer = CDCConsumer(batch_size=100)
    rep_summary = consumer.run_replication_cycle()
    print(f"Replication Cycle Finished:")
    print(f"  - Events Read:    {rep_summary['events_read']}")
    print(f"  - Events Applied: {rep_summary['events_applied']}")
    print(f"  - Stale Dropped:  {rep_summary['stale_skipped']}")

    # Step 7: Verify Source vs Analytical Consistency
    print("\n[Step 7] Verifying Source vs Target Data Consistency...")
    consistency = verify_source_target_consistency()
    print(f"  Consistent:          {consistency['is_consistent']}")
    print(f"  Source Active Rows:  {consistency['source_active_count']}")
    print(f"  Target Active Rows:  {consistency['target_active_count']}")
    print(f"  Target Deleted Rows: {consistency['target_deleted_count']}")
    print(f"  Mismatches:          {consistency['mismatches_count']}")

    # Step 8: Export Reports
    print("\n[Step 8] Exporting Verification Reports...")
    with open(outputs_dir / "consistency_report.json", "w", encoding="utf-8") as f:
        json.dump(consistency, f, indent=2)

    md_summary = f"""# Change Data Capture (CDC) Replication Summary

## 1. Overview
- **Database Engine:** PostgreSQL 16
- **Capture Mechanism:** PL/pgSQL transactional triggers on `operational_inventory`
- **Replication Target:** `analytical_inventory`
- **Audit Ledger:** `cdc_audit_ledger` (Append-only)

## 2. Execution Metrics
| Metric | Value |
|--------|-------|
| **Total Captured Events** | {sum(ledger_stats.values())} |
| **INSERT Events** | {ledger_stats.get('INSERT', 0)} |
| **UPDATE Events** | {ledger_stats.get('UPDATE', 0)} |
| **DELETE Events** | {ledger_stats.get('DELETE', 0)} |
| **Events Applied by Consumer** | {rep_summary['events_applied']} |
| **Out-of-Order / Stale Deduplicated** | {rep_summary['stale_skipped']} |
| **Final State Consistent** | **{consistency['is_consistent']}** |
| **Active Source Rows** | {consistency['source_active_count']} |
| **Active Analytical Rows** | {consistency['target_active_count']} |
| **Analytical Soft-Deleted Rows** | {consistency['target_deleted_count']} |
"""
    with open(outputs_dir / "cdc_execution_summary.md", "w", encoding="utf-8") as f:
        f.write(md_summary)

    print(f"Reports successfully saved to {outputs_dir}")
    print("=" * 70)
    print("PRACTICAL 7 EXECUTION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    run_cdc_pipeline()
