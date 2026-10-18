from datetime import datetime, timezone
from typing import Dict, List, Tuple
from src.audit_logger import AuditLogger
from src.storage_client import StorageClient

class AccessLogAnalyzer:
    """
    Evaluates data access manifests and logs, flags objects not read for > 90 days,
    and automatically executes demotion to COLD tier via StorageClient API.
    """

    def __init__(self, audit_logger: AuditLogger, storage_client: StorageClient = None):
        self.audit_logger = audit_logger
        self.storage_client = storage_client or StorageClient()

    def analyze_and_demote_inactive(
        self,
        metadata_list: List[Dict],
        inactivity_threshold_days: int = 90,
        hot_bucket: str = "logs-hot",
        cold_bucket: str = "logs-cold"
    ) -> Tuple[List[Dict], int]:
        """
        Flags any object with days_since_last_access > 90 and executes demotion to COLD.
        """
        flagged_objects = []
        demoted_count = 0

        for item in metadata_list:
            days_since = item.get("days_since_last_access", 0)
            key = item["object_key"]

            if days_since > inactivity_threshold_days:
                flagged_objects.append({
                    "object_key": key,
                    "days_since_last_access": days_since,
                    "age_days": item.get("age_days"),
                    "size_bytes": item.get("size_bytes"),
                    "recommendation": "DEMOTE_TO_COLD"
                })

                self.audit_logger.log_event(
                    action="ACCESS_LOG_FLAG_INACTIVE",
                    object_key=key,
                    status="SUCCESS",
                    details={
                        "days_since_last_access": days_since,
                        "threshold": inactivity_threshold_days,
                        "action_taken": "INITIATE_AUTOMATIC_DEMOTION"
                    }
                )

                # Attempt automatic demotion
                try:
                    success, msg, details = self.storage_client.transition_object(
                        src_bucket=hot_bucket,
                        dest_bucket=cold_bucket,
                        object_key=key,
                        compress=True
                    )
                    if success:
                        demoted_count += 1
                        self.audit_logger.log_event(
                            action="AUTOMATIC_DEMOTION_EXECUTED",
                            object_key=key,
                            status="SUCCESS",
                            details={"destination": cold_bucket, **details}
                        )
                except Exception as ex:
                    self.audit_logger.log_event(
                        action="AUTOMATIC_DEMOTION_EXECUTED",
                        object_key=key,
                        status="FAILED",
                        details={"error": str(ex)}
                    )

        return flagged_objects, demoted_count
