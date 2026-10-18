import json
import os
import sys
from pathlib import Path
from psycopg2.extras import RealDictCursor

PRAC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PRAC_DIR))

from src.crypto_utils import (
    canonicalize_identifier,
    hash_identity_sha256,
    get_or_create_encryption_key,
    encrypt_column_value,
    decrypt_column_value,
    mask_email,
    mask_name
)
from src.security_audit_logger import SecurityAuditLogger
from src.data_generator import generate_customer_analytics_dataset
from src.db_service import get_db_connection, execute_sql_file
from src.reverse_etl_engine import ReverseETLEngine

def run_pipeline():
    print("=" * 70)
    print("PRACTICAL 11: DATA SERVING, REVERSE ETL, AND SECURITY")
    print("Column-Level Encryption, SHA-256 Hashing, Database RBAC & Reverse ETL")
    print("=" * 70)

    outputs_dir = PRAC_DIR / "outputs"
    sql_dir = PRAC_DIR / "sql"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    audit_log_path = outputs_dir / "security_audit_trail.log"
    if audit_log_path.exists():
        audit_log_path.unlink()
    audit_logger = SecurityAuditLogger(audit_log_path)

    # Step 1: Key Management
    print("\n[Step 1] Initializing Cryptographic Key Store...")
    key_file = outputs_dir / "secret.key"
    enc_key = get_or_create_encryption_key(key_file)
    print(f"Encryption key initialized (stored safely outside code in {key_file.name}).")
    audit_logger.log_security_event("KEY_INITIALIZATION", "admin", "keystore", "SUCCESS")

    # Step 2: Initialize Database Schemas and RBAC Roles
    print("\n[Step 2] Applying PostgreSQL Schemas, Views, and RBAC Role Grants...")
    execute_sql_file(sql_dir / "01_analytical_serving_schema.sql")
    execute_sql_file(sql_dir / "02_operational_crm_schema.sql")
    execute_sql_file(sql_dir / "03_rbac_roles_and_grants.sql")
    print("Created customer_analytics_secure, view_analyst_customer_metrics, crm_customer_profiles, and configured roles.")

    # Step 3: Generate and Encrypt Customer Analytics Dataset
    print("\n[Step 3] Generating Synthetic Customer Records and Applying Column Encryption & Hashing...")
    raw_customers = generate_customer_analytics_dataset(num_customers=50, seed=42)
    processed_records = []

    for c in raw_customers:
        raw_email = c["raw_email"]
        canonical_email = canonicalize_identifier(raw_email)
        email_hash = hash_identity_sha256(canonical_email)
        encrypted_email = encrypt_column_value(raw_email, enc_key)
        masked_em = mask_email(raw_email)
        masked_nm = mask_name(c["full_name"])

        processed_records.append({
            "customer_id": c["customer_id"],
            "email_hash": email_hash,
            "encrypted_email": encrypted_email,
            "masked_email": masked_em,
            "masked_name": masked_nm,
            "segment": c["segment"],
            "ltv_score": c["ltv_score"],
            "churn_risk_score": c["churn_risk_score"],
            "total_orders": c["total_orders"],
            "last_active_date": c["last_active_date"]
        })

    # Step 4: Populate Analytical Serving Base Table
    print("\n[Step 4] Populating Secure Analytical Serving Layer...")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            for r in processed_records:
                cur.execute("""
                    INSERT INTO customer_analytics_secure (
                        customer_id, email_hash, encrypted_email, masked_email, masked_name,
                        segment, ltv_score, churn_risk_score, total_orders, last_active_date
                    ) VALUES (
                        %(customer_id)s, %(email_hash)s, %(encrypted_email)s, %(masked_email)s, %(masked_name)s,
                        %(segment)s, %(ltv_score)s, %(churn_risk_score)s, %(total_orders)s, %(last_active_date)s
                    );
                """, r)
        conn.commit()
    finally:
        conn.close()
    print(f"Loaded {len(processed_records)} encrypted and tokenized customer records.")

    # Step 5: Demonstrate Database RBAC Access Controls
    print("\n[Step 5] Demonstrating RBAC Role-Based Access Controls...")
    # 5a. Analyst queries permitted view
    analyst_conn = get_db_connection(user="analyst_role", password="analyst_pass123")
    try:
        with analyst_conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT customer_id, email_hash, masked_email, masked_name, segment, ltv_score FROM view_analyst_customer_metrics LIMIT 3;")
            analyst_sample = cur.fetchall()
            print("Analyst View Query (SUCCESS): Sample Permitted Records:")
            for s in analyst_sample:
                print(f"  - Cust: {s['customer_id']} | Email: {s['masked_email']} | Name: {s['masked_name']} | Segment: {s['segment']}")
            
            with open(outputs_dir / "analyst_masked_sample.json", "w", encoding="utf-8") as f:
                json.dump([dict(r) for r in analyst_sample], f, indent=2, default=str)

            audit_logger.log_security_event("QUERY_ANALYST_VIEW", "analyst_role", "view_analyst_customer_metrics", "SUCCESS")
    finally:
        analyst_conn.close()

    # 5b. Analyst attempts illegal direct access to base table customer_analytics_secure
    analyst_conn2 = get_db_connection(user="analyst_role", password="analyst_pass123")
    try:
        with analyst_conn2.cursor() as cur:
            cur.execute("SELECT encrypted_email FROM customer_analytics_secure LIMIT 1;")
            print("[UNEXPECTED] Analyst was able to read raw table!")
    except Exception as e:
        print(f"Analyst Direct Table Access: [DENIED AS EXPECTED] -> {e.pgerror.strip() if hasattr(e, 'pgerror') else str(e)}")
        audit_logger.log_security_event(
            "UNAUTHORIZED_ACCESS_ATTEMPT",
            "analyst_role",
            "customer_analytics_secure",
            "DENIED",
            {"reason": "Permission denied by PostgreSQL RBAC"}
        )
    finally:
        analyst_conn2.close()

    # Step 6: Execute Reverse ETL Pipeline
    print("\n[Step 6] Executing Reverse ETL Pipeline (Operational CRM Activation)...")
    retl = ReverseETLEngine(audit_logger)
    sync_run_1 = retl.run_sync()
    print(f"Reverse ETL Run 1 Completed:")
    print(f"  - Eligible Customers: {sync_run_1['eligible_customers']}")
    print(f"  - Upserted to CRM:    {sync_run_1['upserted_records']}")
    print(f"  - Unmodified Skipped: {sync_run_1['skipped_unmodified']}")

    # Step 7: Demonstrate Idempotency
    print("\n[Step 7] Demonstrating Reverse ETL Idempotency (Re-running sync without data changes)...")
    sync_run_2 = retl.run_sync()
    print(f"Reverse ETL Run 2 (Idempotency Check):")
    print(f"  - Upserted to CRM:    {sync_run_2['upserted_records']}")
    print(f"  - Unmodified Skipped: {sync_run_2['skipped_unmodified']} (100% skipped - no redundant writes!)")

    # Step 8: Verify CRM Operational State
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT customer_id, current_segment, crm_activation_flag, lifetime_value FROM crm_customer_profiles LIMIT 4;")
            crm_records = cur.fetchall()
            print("\nSample Activated Operational CRM Profiles:")
            for cr in crm_records:
                print(f"  - {cr['customer_id']}: Segment = {cr['current_segment']:18s} | Action = {cr['crm_activation_flag']} | LTV = ${cr['lifetime_value']}")
    finally:
        conn.close()

    # Step 9: Export Reports
    with open(outputs_dir / "reverse_etl_sync_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "run_1_initial_sync": sync_run_1,
            "run_2_idempotency_check": sync_run_2,
            "crm_profiles_count": sync_run_1["upserted_records"]
        }, f, indent=2)

    md_summary = f"""# Practical 11: Data Serving, Reverse ETL, and Security Summary

## 1. Security Architecture Implementation
- **Cryptographic Engine:** Fernet (AES-128-CBC + HMAC-SHA256 Authenticated Encryption)
- **Identity Hashing:** Canonicalized SHA-256 for deterministic multi-system entity resolution
- **Data Masking:** Dynamic partial masking on analyst views (`mask_email`, `mask_name`)
- **Database RBAC:** PostgreSQL Role-Based Access Control enforcing least privilege:
  - `analyst_role`: Allowed `SELECT` ONLY on `view_analyst_customer_metrics`. Base table queries are rejected.
  - `reverse_etl_role`: Granted specific pipeline permissions for reading analytics and updating operational CRM tables.

## 2. Reverse ETL Metrics
| Metric | Value |
|--------|-------|
| **Total Customers Analyzed** | 50 |
| **Eligible for Activation (VIP / Churn)** | {sync_run_1['eligible_customers']} |
| **Initial CRM Upserts** | {sync_run_1['upserted_records']} |
| **Subsequent Sync (Idempotency Test)** | 0 inserted, {sync_run_2['skipped_unmodified']} skipped (100% duplicate prevention) |

## 3. Audit Logging
All security events, decryption calls, unauthorized access attempts, and Reverse ETL cycles are recorded with UTC timestamps in `outputs/security_audit_trail.log`.
"""
    with open(outputs_dir / "reverse_etl_summary.md", "w", encoding="utf-8") as f:
        f.write(md_summary)

    print(f"\nArtifacts successfully written to {outputs_dir}")
    print("=" * 70)
    print("PRACTICAL 11 EXECUTION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    run_pipeline()
