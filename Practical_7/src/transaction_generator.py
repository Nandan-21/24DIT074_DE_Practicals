import random
from typing import Dict, List
import psycopg2
from src.db_connection import get_connection

CATEGORIES = ["Electronics", "Appliances", "Computers", "Mobile Accessories", "Office Supplies"]

def seed_initial_inventory(num_items: int = 20) -> List[int]:
    """Inserts initial operational inventory items."""
    conn = get_connection()
    inserted_ids = []
    try:
        with conn.cursor() as cur:
            for i in range(1, num_items + 1):
                sku = f"SKU-{1000 + i}"
                name = f"Inventory Item #{i}"
                cat = random.choice(CATEGORIES)
                qty = random.randint(20, 200)
                price = round(random.uniform(9.99, 499.99), 2)

                cur.execute("""
                    INSERT INTO operational_inventory (sku, item_name, category, quantity, unit_price)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (sku) DO UPDATE 
                    SET quantity = EXCLUDED.quantity, unit_price = EXCLUDED.unit_price
                    RETURNING item_id;
                """, (sku, name, cat, qty, price))
                item_id = cur.fetchone()[0]
                inserted_ids.append(item_id)
        conn.commit()
    finally:
        conn.close()
    return inserted_ids

def simulate_stock_updates(item_ids: List[int], num_updates: int = 15) -> int:
    """Simulates rapid inventory movements and price updates."""
    conn = get_connection()
    updates_performed = 0
    try:
        with conn.cursor() as cur:
            for _ in range(num_updates):
                target_id = random.choice(item_ids)
                qty_change = random.randint(-10, 30)
                new_price = round(random.uniform(15.00, 550.00), 2)

                cur.execute("""
                    UPDATE operational_inventory
                    SET quantity = GREATEST(0, quantity + %s),
                        unit_price = %s
                    WHERE item_id = %s;
                """, (qty_change, new_price, target_id))
                updates_performed += 1
        conn.commit()
    finally:
        conn.close()
    return updates_performed

def simulate_item_deletions(item_ids: List[int], num_deletes: int = 3) -> List[int]:
    """Simulates row purge / deletion requests on obsolete inventory items."""
    conn = get_connection()
    deleted_ids = []
    try:
        with conn.cursor() as cur:
            for _ in range(min(num_deletes, len(item_ids))):
                del_id = item_ids.pop(random.randrange(len(item_ids)))
                cur.execute("DELETE FROM operational_inventory WHERE item_id = %s;", (del_id,))
                deleted_ids.append(del_id)
        conn.commit()
    finally:
        conn.close()
    return deleted_ids
