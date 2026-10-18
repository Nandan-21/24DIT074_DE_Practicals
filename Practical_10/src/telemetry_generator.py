import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import pandas as pd

def generate_batch_telemetry_dataset(
    output_path: Path,
    num_records: int = 5000,
    seed: int = 42
) -> Path:
    """Generates synthetic batch IoT telemetry records with sensor readings."""
    random.seed(seed)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    base_time = datetime(2026, 3, 1, 8, 0, 0)
    devices = [f"DEV-{i:03d}" for i in range(1, 21)]

    records = []
    for i in range(num_records):
        dev = random.choice(devices)
        event_time = base_time + timedelta(seconds=random.randint(0, 14400)) # 4 hour window
        ingest_time = event_time + timedelta(seconds=random.randint(1, 300))

        # Introduce occasional corrupted records (outliers/nulls) to test cleaning
        is_corrupt = (i % 200 == 0)
        temp = None if is_corrupt else round(random.normalvariate(65.0, 12.0), 2)
        vibe = round(random.uniform(5.0, 60.0), 2)
        power = round(random.uniform(150.0, 850.0), 1)
        status = "ERR" if (temp and temp > 85.0) else ("WARN" if (temp and temp > 75.0) else "OK")

        records.append({
            "record_id": f"rec_{i+1:06d}",
            "device_id": dev,
            "event_timestamp": event_time.strftime("%Y-%m-%d %H:%M:%S"),
            "ingestion_timestamp": ingest_time.strftime("%Y-%m-%d %H:%M:%S"),
            "temperature_celsius": temp,
            "vibration_hz": vibe,
            "power_watts": power,
            "status_code": status
        })

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    return output_path

def generate_streaming_microbatches(
    feed_dir: Path,
    base_time: datetime = datetime(2026, 3, 1, 12, 0, 0)
) -> List[Path]:
    """
    Generates deterministic streaming micro-batches illustrating:
    - Microbatch 1: On-time events (12:00 to 12:10)
    - Microbatch 2: On-time (12:10 to 12:20) + Acceptably Late events (12:12 event arriving at 12:19, within 10m watermark)
    - Microbatch 3: Advance watermark (12:25 to 12:35) + Excessively Late events (12:05 event arriving at 12:32, beyond 10m watermark!)
    """
    feed_dir = Path(feed_dir)
    feed_dir.mkdir(parents=True, exist_ok=True)
    created_files = []

    # Batch 1: Initial on-time events (12:00:00 - 12:10:00)
    b1_events = []
    for i in range(15):
        t = base_time + timedelta(minutes=i % 10, seconds=random.randint(1, 50))
        b1_events.append({
            "record_id": f"b1_{i+1:03d}",
            "device_id": f"DEV-{((i % 5) + 1):03d}",
            "event_timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
            "temperature_celsius": round(random.uniform(50.0, 75.0), 2),
            "vibration_hz": round(random.uniform(10.0, 30.0), 2),
            "power_watts": round(random.uniform(200.0, 400.0), 1),
            "arrival_category": "ON_TIME"
        })
    f1 = feed_dir / "microbatch_01.json"
    with open(f1, "w", encoding="utf-8") as f:
        for ev in b1_events:
            f.write(json.dumps(ev) + "\n")
    created_files.append(f1)

    # Batch 2: On-time (12:10 - 12:20) + Acceptably Late (event at 12:08 arriving at 12:16, delay 8 min < 10 min watermark)
    b2_events = []
    for i in range(15):
        t = base_time + timedelta(minutes=10 + (i % 10), seconds=random.randint(1, 50))
        b2_events.append({
            "record_id": f"b2_ontime_{i+1:03d}",
            "device_id": f"DEV-{((i % 5) + 1):03d}",
            "event_timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
            "temperature_celsius": round(random.uniform(55.0, 80.0), 2),
            "vibration_hz": round(random.uniform(15.0, 35.0), 2),
            "power_watts": round(random.uniform(250.0, 450.0), 1),
            "arrival_category": "ON_TIME"
        })
    # Add 3 acceptably late events (timestamp 12:08:00)
    for i in range(3):
        b2_events.append({
            "record_id": f"b2_late_ok_{i+1:03d}",
            "device_id": f"DEV-001",
            "event_timestamp": (base_time + timedelta(minutes=8, seconds=10 * i)).strftime("%Y-%m-%d %H:%M:%S"),
            "temperature_celsius": 68.5,
            "vibration_hz": 22.1,
            "power_watts": 310.0,
            "arrival_category": "ACCEPTABLE_LATE_WITHIN_WATERMARK"
        })
    f2 = feed_dir / "microbatch_02.json"
    with open(f2, "w", encoding="utf-8") as f:
        for ev in b2_events:
            f.write(json.dumps(ev) + "\n")
    created_files.append(f2)

    # Batch 3: High current event time (12:35) -> advances watermark to 12:25 (12:35 - 10 min)
    # Plus excessively late event (timestamp 12:02:00 -> 33 minutes late, older than watermark 12:25!)
    b3_events = []
    for i in range(15):
        t = base_time + timedelta(minutes=25 + (i % 10), seconds=random.randint(1, 50))
        b3_events.append({
            "record_id": f"b3_ontime_{i+1:03d}",
            "device_id": f"DEV-{((i % 5) + 1):03d}",
            "event_timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
            "temperature_celsius": round(random.uniform(60.0, 85.0), 2),
            "vibration_hz": round(random.uniform(20.0, 40.0), 2),
            "power_watts": round(random.uniform(300.0, 500.0), 1),
            "arrival_category": "ON_TIME"
        })
    # Add 3 excessively late records (timestamp 12:02:00 -> should be dropped by watermark)
    for i in range(3):
        b3_events.append({
            "record_id": f"b3_excess_late_{i+1:03d}",
            "device_id": f"DEV-002",
            "event_timestamp": (base_time + timedelta(minutes=2, seconds=15 * i)).strftime("%Y-%m-%d %H:%M:%S"),
            "temperature_celsius": 99.9,
            "vibration_hz": 55.0,
            "power_watts": 600.0,
            "arrival_category": "EXCESSIVELY_LATE_PAST_WATERMARK"
        })
    f3 = feed_dir / "microbatch_03.json"
    with open(f3, "w", encoding="utf-8") as f:
        for ev in b3_events:
            f.write(json.dumps(ev) + "\n")
    created_files.append(f3)

    return created_files
