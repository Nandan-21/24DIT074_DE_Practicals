from typing import Dict, List, Tuple
from psycopg2.extras import RealDictCursor
from src.db_connection import get_connection

def verify_source_target_consistency() -> Dict:
    """
    Compares operational_inventory and analytical_inventory to ensure 100% data consistency.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Fetch active source items
            cur.execute("""
                SELECT item_id, sku, item_name, category, quantity, CAST(unit_price AS FLOAT) as unit_price, row_version
                FROM operational_inventory
                ORDER BY item_id;
            """)
            source_rows = {r["item_id"]: dict(r) for r in cur.fetchall()}

            # 2. Fetch active analytical replica items
            cur.execute("""
                SELECT item_id, sku, item_name, category, quantity, CAST(unit_price AS FLOAT) as unit_price, replicated_version, is_deleted
                FROM analytical_inventory
                WHERE is_deleted = FALSE
                ORDER BY item_id;
            """)
            target_rows = {r["item_id"]: dict(r) for r in cur.fetchall()}

            # 3. Fetch deleted analytical items
            cur.execute("""
                SELECT item_id, sku, replicated_version, last_cdc_operation
                FROM analytical_inventory
                WHERE is_deleted = TRUE
                ORDER BY item_id;
            """)
            deleted_rows = cur.fetchall()

            # 4. Compare active records
            mismatches = []
            for item_id, src in source_rows.items():
                if item_id not in target_rows:
                    mismatches.append({"item_id": item_id, "issue": "MISSING_IN_TARGET", "source": src})
                else:
                    tgt = target_rows[item_id]
                    diffs = {}
                    if src["quantity"] != tgt["quantity"]:
                        diffs["quantity"] = {"source": src["quantity"], "target": tgt["quantity"]}
                    if abs(src["unit_price"] - tgt["unit_price"]) > 0.001:
                        diffs["unit_price"] = {"source": src["unit_price"], "target": tgt["unit_price"]}
                    if src["row_version"] != tgt["replicated_version"]:
                        diffs["version"] = {"source": src["row_version"], "target": tgt["replicated_version"]}
                    if diffs:
                        mismatches.append({"item_id": item_id, "issue": "VALUE_MISMATCH", "differences": diffs})

            for item_id in target_rows:
                if item_id not in source_rows:
                    mismatches.append({"item_id": item_id, "issue": "EXTRA_IN_TARGET"})

            is_consistent = (len(mismatches) == 0 and len(source_rows) == len(target_rows))

            return {
                "is_consistent": is_consistent,
                "source_active_count": len(source_rows),
                "target_active_count": len(target_rows),
                "target_deleted_count": len(deleted_rows),
                "mismatches_count": len(mismatches),
                "mismatches": mismatches
            }
    finally:
        conn.close()
