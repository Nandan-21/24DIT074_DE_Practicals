-- ====================================================================
-- PRACTICAL 11: OPERATIONAL CRM DESTINATION SCHEMA (REVERSE ETL SINK)
-- ====================================================================

DROP TABLE IF EXISTS crm_customer_profiles CASCADE;

-- Target operational destination table (simulates Salesforce / HubSpot CRM customer store)
CREATE TABLE crm_customer_profiles (
    customer_id VARCHAR(50) PRIMARY KEY,
    identity_hash VARCHAR(64) NOT NULL UNIQUE,
    current_segment VARCHAR(50) NOT NULL,
    churn_risk NUMERIC(5, 3) NOT NULL,
    lifetime_value NUMERIC(10, 2) NOT NULL,
    crm_activation_flag VARCHAR(50),            -- e.g. 'CHURN_PREVENTION_CAMPAIGN', 'VIP_CONCIERGE'
    sync_source VARCHAR(50) DEFAULT 'REVERSE_ETL_PIPELINE',
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
