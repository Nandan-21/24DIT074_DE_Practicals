import sys
from pathlib import Path

PRAC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PRAC_DIR))

import pytest
import psycopg2
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
from src.db_service import get_db_connection, execute_sql_file
from src.reverse_etl_engine import ReverseETLEngine

@pytest.fixture(scope="module")
def setup_security_db(tmp_path_factory):
    sql_dir = PRAC_DIR / "sql"
    execute_sql_file(sql_dir / "01_analytical_serving_schema.sql")
    execute_sql_file(sql_dir / "02_operational_crm_schema.sql")
    execute_sql_file(sql_dir / "03_rbac_roles_and_grants.sql")

def test_hashing_and_canonicalization():
    h1 = hash_identity_sha256(" Alice.Johnson@Example.COM ")
    h2 = hash_identity_sha256("alice.johnson@example.com")
    assert h1 == h2
    assert len(h1) == 64

def test_fernet_column_encryption_roundtrip(tmp_path):
    key = get_or_create_encryption_key(tmp_path / "test.key")
    secret_text = "patient_medical_history_or_ssn"
    ciphertext = encrypt_column_value(secret_text, key)

    assert ciphertext != secret_text
    assert "patient" not in ciphertext

    decrypted = decrypt_column_value(ciphertext, key)
    assert decrypted == secret_text

def test_masking_functions():
    assert mask_email("alice.smith@example.com") == "a***h@example.com"
    assert mask_email("bob@corp.org") == "b***b@corp.org"
    assert mask_name("Alice Johnson") == "A**** J******"

def test_analyst_rbac_enforcement(setup_security_db):
    # 1. Analyst can select from view
    analyst_conn = get_db_connection(user="analyst_role", password="analyst_pass123")
    try:
        with analyst_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM view_analyst_customer_metrics;")
            assert cur.fetchone() is not None
    finally:
        analyst_conn.close()

    # 2. Analyst is DENIED direct access to base secure table
    analyst_conn2 = get_db_connection(user="analyst_role", password="analyst_pass123")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        with analyst_conn2.cursor() as cur:
            cur.execute("SELECT * FROM customer_analytics_secure;")
    analyst_conn2.close()

def test_reverse_etl_idempotency(setup_security_db, tmp_path):
    logger = SecurityAuditLogger(tmp_path / "test_audit.log")
    
    # Insert test record into base table
    key = get_or_create_encryption_key(tmp_path / "test2.key")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO customer_analytics_secure (
                    customer_id, email_hash, encrypted_email, masked_email, masked_name,
                    segment, ltv_score, churn_risk_score, total_orders, last_active_date
                ) VALUES (
                    'TEST_VIP_1', 'hash_test_vip', %s, 't***1@vip.com', 'T*** V**',
                    'High-Value VIP', 12000.00, 0.05, 50, '2026-03-01'
                ) ON CONFLICT (customer_id) DO NOTHING;
            """, (encrypt_column_value("test1@vip.com", key),))
        conn.commit()
    finally:
        conn.close()

    engine = ReverseETLEngine(logger)
    # Run 1
    res1 = engine.run_sync()
    assert res1["upserted_records"] >= 1

    # Run 2: idempotent repeat
    res2 = engine.run_sync()
    assert res2["upserted_records"] == 0
    assert res2["skipped_unmodified"] >= 1
