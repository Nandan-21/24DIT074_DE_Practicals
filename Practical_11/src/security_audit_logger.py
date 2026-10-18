import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

class SecurityAuditLogger:
    """Centralized structured audit logger for secure analytical serving & Reverse ETL."""

    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.events = []

    def log_security_event(
        self,
        event_type: str,
        actor_role: str,
        target_resource: str,
        status: str,
        details: Dict[str, Any] = None
    ):
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "actor_role": actor_role,
            "target_resource": target_resource,
            "status": status,
            "details": details or {}
        }
        self.events.append(event)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        return event
