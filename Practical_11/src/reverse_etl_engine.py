import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from psycopg2.extras import RealDictCursor
from src.db_service import get_db_connection
from src.security_audit_logger import SecurityAuditLogger

class ReverseETLEngine:
    """Reverse ETL engine that syncs analytical insights into operational CRM profiles."""

    def __init__(self, audit_logger: SecurityAuditLogger):
        self.audit_logger = audit_logger

    def run_sync(self) -> Dict:
        """
        Extracts high-value and at-risk segments from customer_analytics_secure,
        transforms them with operational activation tags, and performs idempotent upserts into crm_customer_profiles.
        """
        conn = get_db_connection(user="reverse_etl_role", password="retl_pass123")
        sync_stats = {
            "eligible_customers": 0,
            "upserted_records": 0,
            "skipped_unmodified": 0,
            "failed_records": 0
        }

        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # 1. Extract eligible segments for operational activation
                    cur.execute("""
                        SELECT 
                            customer_id,
                            email_hash,
                            segment,
                            churn_risk_score,
                            ltv_score
                        FROM customer_analytics_secure
                        WHERE segment IN ('High-Value VIP', 'At-Risk Churn') OR churn_risk_score >= 0.70;
                    """)
                    candidates = cur.fetchall()
                    sync_stats["eligible_customers"] = len(candidates)

                    for c in candidates:
                        cust_id = c["customer_id"]
                        email_hash = c["email_hash"]
                        segment = c["segment"]
                        churn_risk = float(c["churn_risk_score"])
                        ltv = float(c["ltv_score"])

                        # Determine operational CRM activation campaign
                        if churn_risk >= 0.70:
                            campaign_flag = "URGENT_RETENTION_INTERVENTION"
                        elif segment == "High-Value VIP":
                            campaign_flag = "VIP_CONCIERGE_OUTREACH"
                        else:
                            campaign_flag = "STANDARD_NURTURE"

                        # Compute snapshot hash to detect if customer state changed
                        state_repr = f"{cust_id}:{segment}:{churn_risk:.3f}:{ltv:.2f}:{campaign_flag}"
                        state_hash = hashlib.sha256(state_repr.encode("utf-8")).hexdigest()

                        # Check existing sync state
                        cur.execute("""
                            SELECT synced_hash FROM reverse_etl_sync_state
                            WHERE customer_id = %s AND target_system = 'CRM_SALESFORCE';
                        """, (cust_id,))
                        existing = cur.fetchone()

                        if existing and existing["synced_hash"] == state_hash:
                            sync_stats["skipped_unmodified"] += 1
                            continue

                        # 2. Idempotent Upsert into Operational CRM Store
                        cur.execute("""
                            INSERT INTO crm_customer_profiles (
                                customer_id, identity_hash, current_segment, churn_risk, lifetime_value,
                                crm_activation_flag, sync_source, last_synced_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, 'REVERSE_ETL_PIPELINE', CURRENT_TIMESTAMP
                            )
                            ON CONFLICT (customer_id) DO UPDATE SET
                                identity_hash = EXCLUDED.identity_hash,
                                current_segment = EXCLUDED.current_segment,
                                churn_risk = EXCLUDED.churn_risk,
                                lifetime_value = EXCLUDED.lifetime_value,
                                crm_activation_flag = EXCLUDED.crm_activation_flag,
                                last_synced_at = CURRENT_TIMESTAMP;
                        """, (cust_id, email_hash, segment, churn_risk, ltv, campaign_flag))

                        # 3. Update Sync State Ledger
                        cur.execute("""
                            INSERT INTO reverse_etl_sync_state (
                                customer_id, target_system, synced_hash, sync_status, last_synced_at
                            ) VALUES (
                                %s, 'CRM_SALESFORCE', %s, 'SUCCESS', CURRENT_TIMESTAMP
                            );
                        """, (cust_id, state_hash))

                        sync_stats["upserted_records"] += 1

            self.audit_logger.log_security_event(
                event_type="REVERSE_ETL_SYNC_CYCLE",
                actor_role="reverse_etl_role",
                target_resource="crm_customer_profiles",
                status="SUCCESS",
                details=sync_stats
            )
        except Exception as e:
            self.audit_logger.log_security_event(
                event_type="REVERSE_ETL_SYNC_CYCLE",
                actor_role="reverse_etl_role",
                target_resource="crm_customer_profiles",
                status="FAILED",
                details={"error": str(e)}
            )
            raise e
        finally:
            conn.close()

        return sync_stats
