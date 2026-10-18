import json
from pathlib import Path
from typing import Dict, List, Tuple
from src.audit_logger import AuditLogger
from src.storage_client import StorageClient

class LifecyclePolicyEngine:
    """Configurable lifecycle policy engine for classifying and transitioning objects across tiers."""

    def __init__(self, policy_path: Path, audit_logger: AuditLogger, storage_client: StorageClient = None):
        self.policy_path = Path(policy_path)
        with open(self.policy_path, "r", encoding="utf-8") as f:
            self.policy = json.load(f)
        self.audit_logger = audit_logger
        self.storage_client = storage_client or StorageClient()
        self.tiers = self.policy.get("tiers", {})

    def evaluate_object(self, meta: Dict) -> str:
        """
        Classifies an object into HOT, WARM, COLD, or EXPIRED based on policy criteria:
        - age_days
        - access_count_last_7_days
        - days_since_last_access
        """
        age_days = meta.get("age_days", 0)
        access_freq_weekly = meta.get("access_count_last_7_days", 0)
        days_since_access = meta.get("days_since_last_access", 0)

        # Check for expiration (> 365 days)
        if age_days > 365:
            return "EXPIRED"

        # Cold rule: older than 90 days OR inactive for > 90 days
        if age_days > 90 or days_since_access > 90:
            return "COLD"

        # Warm rule: between 31 and 90 days AND low access
        if age_days > 30 and access_freq_weekly < 5:
            return "WARM"

        # Hot: recent (<= 30 days) OR frequently accessed (>= 5 per week)
        return "HOT"

    def process_all_objects(
        self,
        metadata_list: List[Dict],
        current_tier: str = "HOT"
    ) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Evaluates all objects in the metadata list, transitions them if target tier differs
        from current tier, and records audit trails.
        """
        results = []
        tier_counts = {"HOT": 0, "WARM": 0, "COLD": 0, "EXPIRED": 0}

        for meta in metadata_list:
            key = meta["object_key"]
            target_tier = self.evaluate_object(meta)
            tier_counts[target_tier] = tier_counts.get(target_tier, 0) + 1

            eval_event = self.audit_logger.log_event(
                action="POLICY_EVALUATION",
                object_key=key,
                status="SUCCESS",
                details={
                    "current_tier": current_tier,
                    "target_tier": target_tier,
                    "age_days": meta.get("age_days"),
                    "days_since_last_access": meta.get("days_since_last_access"),
                    "access_freq_weekly": meta.get("access_count_last_7_days")
                }
            )

            # Check if transition is needed
            transition_details = None
            if current_tier != target_tier and target_tier in ["WARM", "COLD"]:
                src_bucket = self.tiers[current_tier]["target_bucket"]
                dest_bucket = self.tiers[target_tier]["target_bucket"]
                compress = (self.tiers[target_tier].get("compression") == "gzip")

                try:
                    success, msg, details = self.storage_client.transition_object(
                        src_bucket=src_bucket,
                        dest_bucket=dest_bucket,
                        object_key=key,
                        compress=compress
                    )
                    status = "SUCCESS" if success else "FAILED"
                    self.audit_logger.log_event(
                        action=f"TRANSITION_{current_tier}_TO_{target_tier}",
                        object_key=key,
                        status=status,
                        details={"message": msg, **details}
                    )
                    transition_details = details
                except Exception as ex:
                    self.audit_logger.log_event(
                        action=f"TRANSITION_{current_tier}_TO_{target_tier}",
                        object_key=key,
                        status="FAILED",
                        details={"error": str(ex)}
                    )

            results.append({
                "object_key": key,
                "current_tier": current_tier,
                "target_tier": target_tier,
                "age_days": meta.get("age_days"),
                "days_since_last_access": meta.get("days_since_last_access"),
                "size_bytes": meta.get("size_bytes"),
                "transition_details": transition_details
            })

        return results, tier_counts
