-- ====================================================================
-- PRACTICAL 11: SECURE ANALYTICAL SERVING LAYER SCHEMA
-- ====================================================================

DROP VIEW IF EXISTS view_analyst_customer_metrics CASCADE;
DROP TABLE IF EXISTS reverse_etl_sync_state CASCADE;
DROP TABLE IF EXISTS customer_analytics_secure CASCADE;

-- Base analytical table storing encrypted and tokenized/hashed customer data
CREATE TABLE customer_analytics_secure (
    customer_id VARCHAR(50) PRIMARY KEY,
    email_hash VARCHAR(64) NOT NULL UNIQUE,     -- Canonicalized SHA-256 hash for identity matching
    encrypted_email TEXT NOT NULL,              -- Column-level Fernet encrypted ciphertext
    masked_email VARCHAR(100) NOT NULL,         -- Masked string for analytical display (e.g. a***h@domain.com)
    masked_name VARCHAR(100) NOT NULL,          -- Masked name (e.g. J*** S*****)
    segment VARCHAR(50) NOT NULL,
    ltv_score NUMERIC(10, 2) NOT NULL,
    churn_risk_score NUMERIC(5, 3) NOT NULL,
    total_orders INT NOT NULL,
    last_active_date DATE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Reverse ETL sync state tracking table
CREATE TABLE reverse_etl_sync_state (
    sync_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customer_analytics_secure(customer_id),
    target_system VARCHAR(50) NOT NULL,
    synced_hash VARCHAR(64) NOT NULL,
    sync_status VARCHAR(20) NOT NULL,
    retry_count INT DEFAULT 0,
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Restricted Analyst View: Exposes strictly non-sensitive fields and masked identifiers
CREATE VIEW view_analyst_customer_metrics AS
SELECT 
    customer_id,
    email_hash,
    masked_email,
    masked_name,
    segment,
    ltv_score,
    churn_risk_score,
    total_orders,
    last_active_date
FROM customer_analytics_secure;
