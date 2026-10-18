import random
from datetime import datetime, timedelta
from typing import Dict, List

FIRST_NAMES = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "David", "Elizabeth"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
SEGMENTS = ["High-Value VIP", "Growing Mid-Tier", "At-Risk Churn", "Dormant"]

def generate_customer_analytics_dataset(num_customers: int = 50, seed: int = 42) -> List[Dict]:
    random.seed(seed)
    records = []
    base_date = datetime(2026, 3, 1)

    for i in range(1, num_customers + 1):
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        cust_id = f"CUST-{1000 + i}"
        email = f"{fn.lower()}.{ln.lower()}{i}@enterprise-example.com"
        seg = random.choice(SEGMENTS)

        if seg == "High-Value VIP":
            churn_risk = round(random.uniform(0.02, 0.18), 3)
            ltv = round(random.uniform(8000.0, 25000.0), 2)
            orders = random.randint(25, 120)
        elif seg == "At-Risk Churn":
            churn_risk = round(random.uniform(0.72, 0.98), 3)
            ltv = round(random.uniform(1200.0, 6000.0), 2)
            orders = random.randint(5, 20)
        else:
            churn_risk = round(random.uniform(0.20, 0.65), 3)
            ltv = round(random.uniform(500.0, 4500.0), 2)
            orders = random.randint(2, 15)

        days_inactive = random.randint(2, 180)
        last_active = base_date - timedelta(days=days_inactive)

        records.append({
            "customer_id": cust_id,
            "raw_email": email,
            "full_name": f"{fn} {ln}",
            "segment": seg,
            "ltv_score": ltv,
            "churn_risk_score": churn_risk,
            "total_orders": orders,
            "last_active_date": last_active.strftime("%Y-%m-%d")
        })

    return records
