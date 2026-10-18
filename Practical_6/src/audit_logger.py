import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

class AuditLogger:
    """Structured JSON audit logger for storage lifecycle events."""

    def __init__(self, log_file_path: Path):
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.records = []

    def log_event(self, action: str, object_key: str, status: str, details: Dict[str, Any] = None):
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "object_key": object_key,
            "status": status,
            "details": details or {}
        }
        self.records.append(event)
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        return event

    def get_summary(self) -> Dict[str, int]:
        summary = {"total_events": len(self.records), "success": 0, "failure": 0, "demotions": 0}
        for rec in self.records:
            if rec["status"] == "SUCCESS":
                summary["success"] += 1
            elif rec["status"] == "FAILED":
                summary["failure"] += 1
            if "DEMOTE" in rec["action"]:
                summary["demotions"] += 1
        return summary
