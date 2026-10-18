import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import duckdb
import pandas as pd

PAGES = [
    "/home", "/search?q=laptop", "/products/electronics/401",
    "/products/fashion/209", "/cart", "/checkout", "/account/orders",
    "/help/faq", "/categories/electronics", "/categories/clothing"
]
EVENT_TYPES = ["page_view", "click", "search", "add_to_cart", "purchase"]
DEVICES = ["mobile", "desktop", "tablet"]
REGIONS = ["US-East", "US-West", "EU-West", "AP-South", "AP-East"]

def generate_clickstream_dataset(
    output_csv: Path,
    num_records: int = 150000,
    seed: int = 42
) -> Path:
    """Generates synthetic high-cardinality clickstream records."""
    random.seed(seed)
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    base_time = datetime(2026, 1, 1, 0, 0, 0)
    
    # Generate data in chunks for memory efficiency
    chunk_size = 50000
    is_first = True

    for start_idx in range(0, num_records, chunk_size):
        current_chunk_len = min(chunk_size, num_records - start_idx)
        rows = []
        for i in range(current_chunk_len):
            idx = start_idx + i
            user_id = random.randint(1000, 25000)
            session_id = f"sess_{user_id}_{random.randint(1, 100)}"
            event_type = random.choices(
                EVENT_TYPES,
                weights=[0.50, 0.25, 0.12, 0.09, 0.04],
                k=1
            )[0]
            page = random.choice(PAGES)
            device = random.choice(DEVICES)
            region = random.choice(REGIONS)
            resp_time = random.randint(25, 850)
            delta_seconds = random.randint(0, 86400 * 60) # 60 days range
            ts = base_time + timedelta(seconds=delta_seconds)
            date_str = ts.strftime("%Y-%m-%d")

            rows.append({
                "event_id": idx + 1,
                "user_id": user_id,
                "session_id": session_id,
                "event_type": event_type,
                "page_url": page,
                "device_type": device,
                "region": region,
                "response_time_ms": resp_time,
                "event_date": date_str,
                "event_timestamp": ts.isoformat()
            })

        df = pd.DataFrame(rows)
        df.to_csv(output_csv, mode="w" if is_first else "a", header=is_first, index=False)
        is_first = False

    return output_csv
