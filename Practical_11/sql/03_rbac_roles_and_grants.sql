-- ====================================================================
-- PRACTICAL 11: DATABASE ROLE-BASED ACCESS CONTROL (RBAC) GRANTS
-- ====================================================================

-- 1. Create Roles if they do not exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'analyst_role') THEN
        CREATE ROLE analyst_role WITH LOGIN PASSWORD 'analyst_pass123';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'reverse_etl_role') THEN
        CREATE ROLE reverse_etl_role WITH LOGIN PASSWORD 'retl_pass123';
    END IF;
END
$$;

-- 2. Revoke all public permissions on base tables
REVOKE ALL ON customer_analytics_secure FROM PUBLIC;
REVOKE ALL ON reverse_etl_sync_state FROM PUBLIC;
REVOKE ALL ON crm_customer_profiles FROM PUBLIC;

-- 3. Analyst Role Grants: Permitted ONLY to query the sanitized view!
-- Direct access to customer_analytics_secure (containing encrypted/raw data) is strictly blocked.
GRANT USAGE ON SCHEMA public TO analyst_role;
GRANT SELECT ON view_analyst_customer_metrics TO analyst_role;
REVOKE ALL ON customer_analytics_secure FROM analyst_role;

-- 4. Reverse ETL Service Role Grants: Allowed to read secure analytics and write to CRM tables
GRANT USAGE ON SCHEMA public TO reverse_etl_role;
GRANT SELECT ON customer_analytics_secure TO reverse_etl_role;
GRANT SELECT, INSERT, UPDATE ON reverse_etl_sync_state TO reverse_etl_role;
GRANT USAGE, SELECT ON SEQUENCE reverse_etl_sync_state_sync_id_seq TO reverse_etl_role;
GRANT SELECT, INSERT, UPDATE ON crm_customer_profiles TO reverse_etl_role;
