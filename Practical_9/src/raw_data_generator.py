import random
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

CUSTOMERS = [
    {"id": "CUST-101", "name": "Alice Johnson", "email": "alice@example.com", "init_city": "New York", "new_city": "Boston", "segment": "Corporate"},
    {"id": "CUST-102", "name": "Bob Smith", "email": "bob@example.com", "init_city": "Chicago", "new_city": "Denver", "segment": "Consumer"},
    {"id": "CUST-103", "name": "Carol White", "email": "carol@example.com", "init_city": "Austin", "new_city": "Dallas", "segment": "Small Business"},
    {"id": "CUST-104", "name": "David Brown", "email": "david@example.com", "init_city": "Seattle", "new_city": "Portland", "segment": "Consumer"},
    {"id": "CUST-105", "name": "Emma Davis", "email": "emma@example.com", "init_city": "San Francisco", "new_city": "San Jose", "segment": "Corporate"},
    {"id": "CUST-106", "name": "Frank Miller", "email": "frank@example.com", "init_city": "Miami", "new_city": "Orlando", "segment": "Consumer"},
    {"id": "CUST-107", "name": "Grace Wilson", "email": "grace@example.com", "init_city": "Atlanta", "new_city": "Charlotte", "segment": "Corporate"},
    {"id": "CUST-108", "name": "Henry Moore", "email": "henry@example.com", "init_city": "Phoenix", "new_city": "Tucson", "segment": "Consumer"},
]

PRODUCTS = [
    {"id": "PROD-01", "name": "4K Ultra Monitor", "cat": "Electronics", "subcat": "Displays", "cost": 180.0, "price": 299.99},
    {"id": "PROD-02", "name": "Ergonomic Desk Chair", "cat": "Furniture", "subcat": "Chairs", "cost": 120.0, "price": 249.50},
    {"id": "PROD-03", "name": "Mechanical Keyboard", "cat": "Electronics", "subcat": "Peripherals", "cost": 45.0, "price": 89.99},
    {"id": "PROD-04", "name": "Standing Desk 60in", "cat": "Furniture", "subcat": "Desks", "cost": 220.0, "price": 420.00},
    {"id": "PROD-05", "name": "Wireless Noise Cancelling Headset", "cat": "Electronics", "subcat": "Audio", "cost": 75.0, "price": 149.99},
    {"id": "PROD-06", "name": "Filing Cabinet 3-Drawer", "cat": "Furniture", "subcat": "Storage", "cost": 85.0, "price": 169.00},
    {"id": "PROD-07", "name": "Laser Multifunction Printer", "cat": "Office Supplies", "subcat": "Printers", "cost": 130.0, "price": 239.00},
    {"id": "PROD-08", "name": "Premium Heavy Duty Stapler", "cat": "Office Supplies", "subcat": "Desk Supplies", "cost": 12.0, "price": 24.99},
]

STORES = [
    {"id": "STR-01", "name": "Downtown Metro Flagship", "region": "Northeast", "type": "Flagship"},
    {"id": "STR-02", "name": "Suburban Galleria Mall", "region": "Midwest", "type": "Retail"},
    {"id": "STR-03", "name": "Tech Corridor Outlet", "region": "West", "type": "Outlet"},
    {"id": "STR-04", "name": "Sunbelt Commerce Hub", "region": "South", "type": "Retail"},
]

def generate_raw_sales_csv(output_path: Path, num_orders: int = 1000, seed: int = 42) -> Path:
    random.seed(seed)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    start_date = datetime(2025, 1, 1)
    rows = []

    # Address change cutoff for SCD Type 2
    scd_change_date = datetime(2025, 7, 1)

    for order_idx in range(1, num_orders + 1):
        order_id = f"ORD-{10000 + order_idx}"
        day_offset = random.randint(0, 364)
        order_date = start_date + timedelta(days=day_offset)
        order_date_str = order_date.strftime("%Y-%m-%d")

        cust = random.choice(CUSTOMERS)
        # SCD Type 2 logic in source: customer moved cities after July 1st 2025
        city = cust["new_city"] if order_date >= scd_change_date else cust["init_city"]

        store = random.choice(STORES)
        num_items = random.randint(1, 4)

        for line_num in range(1, num_items + 1):
            prod = random.choice(PRODUCTS)
            qty = random.randint(1, 5)
            discount = random.choice([0.0, 0.05, 0.10, 0.15])

            # Inconsistent whitespace in some fields to test raw cleaning
            rows.append({
                "raw_order_id": f"  {order_id} " if line_num % 3 == 0 else order_id,
                "line_item": line_num,
                "order_date": order_date_str,
                "customer_id": cust["id"],
                "customer_name": f" {cust['name']} " if line_num % 2 == 0 else cust["name"],
                "customer_email": cust["email"].upper() if line_num % 4 == 0 else cust["email"],
                "customer_city": city,
                "customer_segment": cust["segment"],
                "product_id": prod["id"],
                "product_name": prod["name"],
                "category": prod["cat"],
                "subcategory": prod["subcat"],
                "unit_cost": prod["cost"],
                "unit_price": prod["price"],
                "store_id": store["id"],
                "store_name": store["name"],
                "store_region": store["region"],
                "store_type": store["type"],
                "quantity": qty,
                "discount_rate": discount
            })

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    return output_path
