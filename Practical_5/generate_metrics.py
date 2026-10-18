import os
import random
from datetime import datetime, timedelta
import pandas as pd

def generate_analytical_metrics():
    print("Generating multi-year analytical application metric tracking dataset...")
    
    years = [2022, 2023, 2024]
    regions = ["US-EAST", "US-WEST", "EU-CENTRAL", "AP-SOUTH"]
    services = ["auth-service", "payment-service", "order-api", "inventory-engine"]
    
    records = []
    metric_id = 1
    
    # Generate structured metrics across multiple years and geographical regions
    for year in years:
        for region in regions:
            # 100 observations per partition for clean, representative analytical data
            start_date = datetime(year, 1, 1)
            for i in range(100):
                event_time = start_date + timedelta(days=random.randint(0, 360), 
                                                     hours=random.randint(0, 23), 
                                                     minutes=random.randint(0, 59))
                records.append({
                    "metric_id": metric_id,
                    "timestamp": event_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "year": year,
                    "region": region,
                    "service_name": random.choice(services),
                    "cpu_usage_pct": round(random.uniform(10.5, 95.0), 2),
                    "memory_usage_mb": random.randint(256, 8192),
                    "request_count": random.randint(50, 5000),
                    "latency_ms": round(random.uniform(5.0, 350.0), 2)
                })
                metric_id += 1

    df = pd.DataFrame(records)
    output_file = "application_metrics.csv"
    df.to_csv(output_file, index=False)
    print(f"Generated {len(df)} records across {len(years)} years and {len(regions)} regions.")
    print(f"Saved dataset locally to: {output_file}")
    print(df.head())

if __name__ == "__main__":
    generate_analytical_metrics()
