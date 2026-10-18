import json
from typing import Dict, List, Tuple
from psycopg2.extras import RealDictCursor
from src.db_connection import get_connection

class CDCConsumer:
    """Incremental CDC Consumer that replays captured events onto analytical_inventory."""

    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size

    def fetch_pending_events(self, conn) -> List[Dict]:
        """Fetches unprocessed CDC events in deterministic chronological order."""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT event_id, table_name, operation, row_key, old_row, new_row, row_version, captured_at
                FROM cdc_audit_ledger
                WHERE is_processed = FALSE
                ORDER BY event_id ASC
                LIMIT %s
                FOR UPDATE;
            """, (self.batch_size,))
            return cur.fetchall()

    def process_event(self, cur, event: Dict) -> Tuple[bool, str]:
        """
        Processes a single CDC event within an open transaction.
        Enforces row-version ordering to prevent stale or duplicate out-of-order writes.
        """
        op = event["operation"]
        row_key = event["row_key"]
        row_version = event["row_version"]

        # Check existing version in analytical target table
        cur.execute("""
            SELECT replicated_version, is_deleted 
            FROM analytical_inventory 
            WHERE item_id = %s;
        """, (row_key,))
        target_row = cur.fetchone()

        if target_row:
            curr_ver = target_row[0]
            # Deduplicate / drop stale out-of-order events:
            # For UPDATE/INSERT, row_version must be strictly greater than current replicated version
            if op in ("INSERT", "UPDATE") and row_version <= curr_ver:
                return False, f"STALE_OR_DUPLICATE (event ver {row_version} <= curr ver {curr_ver})"
            # For DELETE, event version must be at least the current replicated version
            if op == "DELETE" and row_version < curr_ver:
                return False, f"STALE_DELETE (event ver {row_version} < curr ver {curr_ver})"

        if op in ("INSERT", "UPDATE"):
            new_data = event["new_row"]
            if isinstance(new_data, str):
                new_data = json.loads(new_data)

            cur.execute("""
                INSERT INTO analytical_inventory (
                    item_id, sku, item_name, category, quantity, unit_price,
                    replicated_version, last_cdc_operation, replicated_at, is_deleted
                ) VALUES (
                    %(item_id)s, %(sku)s, %(item_name)s, %(category)s, %(quantity)s, %(unit_price)s,
                    %(replicated_version)s, %(last_cdc_operation)s, CURRENT_TIMESTAMP, FALSE
                )
                ON CONFLICT (item_id) DO UPDATE SET
                    sku = EXCLUDED.sku,
                    item_name = EXCLUDED.item_name,
                    category = EXCLUDED.category,
                    quantity = EXCLUDED.quantity,
                    unit_price = EXCLUDED.unit_price,
                    replicated_version = EXCLUDED.replicated_version,
                    last_cdc_operation = EXCLUDED.last_cdc_operation,
                    replicated_at = EXCLUDED.replicated_at,
                    is_deleted = FALSE
                WHERE analytical_inventory.replicated_version < EXCLUDED.replicated_version;
            """, {
                "item_id": new_data["item_id"],
                "sku": new_data["sku"],
                "item_name": new_data["item_name"],
                "category": new_data["category"],
                "quantity": new_data["quantity"],
                "unit_price": new_data["unit_price"],
                "replicated_version": row_version,
                "last_cdc_operation": op
            })
            return True, f"APPLIED_{op}"

        elif op == "DELETE":
            # Replicate delete by marking is_deleted = TRUE and updating version
            cur.execute("""
                UPDATE analytical_inventory
                SET is_deleted = TRUE,
                    last_cdc_operation = 'DELETE',
                    replicated_version = %s,
                    replicated_at = CURRENT_TIMESTAMP
                WHERE item_id = %s;
            """, (row_version, row_key))
            return True, "APPLIED_DELETE"

        return False, f"UNKNOWN_OP_{op}"

    def run_replication_cycle(self) -> Dict[str, int]:
        """
        Executes an atomic CDC replication cycle.
        Changes to target table and ledger processed status commit in the SAME transaction.
        """
        conn = get_connection()
        summary = {"events_read": 0, "events_applied": 0, "stale_skipped": 0}
        try:
            with conn:
                events = self.fetch_pending_events(conn)
                summary["events_read"] = len(events)

                if not events:
                    return summary

                with conn.cursor() as cur:
                    for ev in events:
                        applied, reason = self.process_event(cur, ev)
                        if applied:
                            summary["events_applied"] += 1
                        else:
                            summary["stale_skipped"] += 1

                        # Mark event processed in audit ledger
                        cur.execute("""
                            UPDATE cdc_audit_ledger
                            SET is_processed = TRUE,
                                processed_at = CURRENT_TIMESTAMP
                            WHERE event_id = %s;
                        """, (ev["event_id"],))

            # Commit happens automatically when exiting 'with conn:' context
        finally:
            conn.close()

        return summary
