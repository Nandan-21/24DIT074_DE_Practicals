import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

def generate_synthetic_operational_logs(
    base_dir: Path,
    num_objects: int = 50,
    seed: int = 42
) -> Tuple[List[Dict], List[Dict]]:
    """
    Generates synthetic historical operational logs, access time manifests,
    and audit records spanning multiple simulated quarters (Q1 to Q4 and recent).
    """
    random.seed(seed)
    base_dir = Path(base_dir)
    data_dir = base_dir / "data" / "generated_logs"
    data_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    log_types = ["api_gateway", "payment_service", "auth_broker", "order_processor"]
    log_levels = ["INFO", "WARN", "ERROR", "DEBUG"]

    metadata_manifest: List[Dict] = []
    access_logs: List[Dict] = []

    # Distribution of age across quarters:
    # 0: Very recent (1-15 days ago) - should classify HOT
    # 1: Recent active (16-30 days ago, high access) - should classify HOT
    # 2: Mid age (35-80 days ago, occasional access) - should classify WARM
    # 3: Inactive older (95-180 days ago, no recent access) - should classify COLD
    # 4: Deep archive (>180 days ago, 0 access) - should classify COLD
    # 5: Long untouched (>90 days since last access) - flagged by access analyzer for demotion

    for i in range(num_objects):
        obj_id = f"log_{i+1:04d}"
        category = i % 5

        if category == 0:
            age_days = random.randint(1, 15)
            access_last_7d = random.randint(8, 25)
            days_since_access = random.randint(0, 2)
        elif category == 1:
            age_days = random.randint(16, 30)
            access_last_7d = random.randint(5, 15)
            days_since_access = random.randint(1, 5)
        elif category == 2:
            age_days = random.randint(35, 80)
            access_last_7d = random.randint(1, 3)
            days_since_access = random.randint(10, 45)
        elif category == 3:
            age_days = random.randint(95, 175)
            access_last_7d = 0
            days_since_access = random.randint(91, 150)
        else: # category 4
            age_days = random.randint(180, 330)
            access_last_7d = 0
            days_since_access = random.randint(95, 250)

        created_at = now - timedelta(days=age_days, hours=random.randint(0, 23))
        last_accessed_at = now - timedelta(days=days_since_access, hours=random.randint(0, 23))
        log_type = random.choice(log_types)
        quarter = f"Q{((created_at.month - 1) // 3) + 1}_{created_at.year}"

        file_name = f"{quarter}_{log_type}_{obj_id}.log"
        file_path = data_dir / file_name

        # Create realistic synthetic log file content
        num_lines = random.randint(20, 100)
        lines = []
        for line_idx in range(num_lines):
            ts = (created_at + timedelta(minutes=line_idx * 5)).isoformat()
            lvl = random.choice(log_levels)
            msg = f"[{ts}] [{lvl}] [{log_type}] Transaction ID txn_{random.randint(10000, 99999)} processed with status 200 OK."
            lines.append(msg)
        content = "\n".join(lines) + "\n"

        file_path.write_text(content, encoding="utf-8")
        size_bytes = file_path.stat().st_size

        meta = {
            "object_id": obj_id,
            "object_key": file_name,
            "local_path": str(file_path),
            "size_bytes": size_bytes,
            "created_at": created_at.isoformat(),
            "age_days": age_days,
            "last_accessed_at": last_accessed_at.isoformat(),
            "days_since_last_access": days_since_access,
            "access_count_last_7_days": access_last_7d,
            "quarter": quarter,
            "log_type": log_type
        }
        metadata_manifest.append(meta)

        # Generate access logs
        for _ in range(access_last_7d):
            access_logs.append({
                "object_key": file_name,
                "access_timestamp": (now - timedelta(days=random.randint(0, 6))).isoformat(),
                "accessor_service": "analytical_dashboard",
                "operation": "GET_OBJECT"
            })

    manifest_file = base_dir / "data" / "object_metadata_manifest.json"
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(metadata_manifest, f, indent=2)

    access_log_file = base_dir / "data" / "access_time_manifest.json"
    with open(access_log_file, "w", encoding="utf-8") as f:
        json.dump(access_logs, f, indent=2)

    return metadata_manifest, access_logs
