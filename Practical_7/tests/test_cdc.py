import sys
from pathlib import Path

PRAC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PRAC_DIR))

import pytest
from src.db_connection import get_connection, initialize_database
from src.cdc_consumer import CDCConsumer
from src.verifier import verify_source_target_consistency

@pytest.fixture(scope="module")
def setup_db():
    sql_file = PRAC_DIR / "sql" / "01_init_cdc_schema.sql"
    initialize_database(sql_file)

def test_insert_and_audit_capture(setup_db):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO operational_inventory (sku, item_name, category, quantity, unit_price)
                VALUES ('TEST-SKU-1', 'Test Monitor', 'Electronics', 10, 199.99)
                RETURNING item_id;
            """)
            item_id = cur.fetchone()[0]
        conn.commit()

        # Check ledger
        with conn.cursor() as cur:
            cur.execute("""
                SELECT operation, row_key, row_version, new_row->>'sku'
                FROM cdc_audit_ledger
                WHERE table_name = 'operational_inventory' AND row_key = %s AND operation = 'INSERT';
            """, (item_id,))
            record = cur.fetchone()
            assert record is not None
            assert record[0] == "INSERT"
            assert record[1] == item_id
            assert record[2] == 1
            assert record[3] == "TEST-SKU-1"
    finally:
        conn.close()

def test_update_version_increment_and_capture(setup_db):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT item_id FROM operational_inventory WHERE sku = 'TEST-SKU-1';")
            item_id = cur.fetchone()[0]

            cur.execute("""
                UPDATE operational_inventory
                SET quantity = 15, unit_price = 189.99
                WHERE item_id = %s;
            """, (item_id,))
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT row_version FROM operational_inventory WHERE item_id = %s;", (item_id,))
            v = cur.fetchone()[0]
            assert v == 2

            cur.execute("""
                SELECT operation, row_version, old_row->>'quantity', new_row->>'quantity'
                FROM cdc_audit_ledger
                WHERE row_key = %s AND operation = 'UPDATE';
            """, (item_id,))
            upd = cur.fetchone()
            assert upd is not None
            assert upd[1] == 2
            assert int(upd[2]) == 10
            assert int(upd[3]) == 15
    finally:
        conn.close()

def test_transaction_rollback_prevents_cdc_event(setup_db):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO operational_inventory (sku, item_name, category, quantity, unit_price)
                VALUES ('ROLLBACK-SKU', 'Phantom Widget', 'Office Supplies', 5, 29.99)
                RETURNING item_id;
            """)
            phantom_id = cur.fetchone()[0]
        # Deliberate rollback!
        conn.rollback()

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM operational_inventory WHERE sku = 'ROLLBACK-SKU';")
            assert cur.fetchone()[0] == 0

            cur.execute("SELECT COUNT(*) FROM cdc_audit_ledger WHERE new_row->>'sku' = 'ROLLBACK-SKU';")
            assert cur.fetchone()[0] == 0
    finally:
        conn.close()

def test_cdc_consumer_replication_and_deduplication(setup_db):
    consumer = CDCConsumer(batch_size=50)
    summary = consumer.run_replication_cycle()
    assert summary["events_read"] > 0
    assert summary["events_applied"] > 0

    # Test out-of-order / duplicate event: simulated old event with version 1
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT item_id FROM operational_inventory WHERE sku = 'TEST-SKU-1';")
            item_id = cur.fetchone()[0]

            # Manually inject an out-of-order stale event with row_version 1
            cur.execute("""
                INSERT INTO cdc_audit_ledger (table_name, operation, row_key, old_row, new_row, row_version)
                VALUES ('operational_inventory', 'UPDATE', %s, NULL, '{"item_id": %s, "sku": "STALE", "item_name": "Stale", "category": "Electronics", "quantity": 1, "unit_price": 10.0}', 1);
            """, (item_id, item_id))
        conn.commit()

        # Run consumer - should skip stale event
        dup_summary = consumer.run_replication_cycle()
        assert dup_summary["stale_skipped"] >= 1
    finally:
        conn.close()
