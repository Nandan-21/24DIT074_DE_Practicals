-- ====================================================================
-- PRACTICAL 7: CHANGE DATA CAPTURE (CDC) SCHEMA DEFINITIONS
-- ====================================================================

DROP TABLE IF EXISTS analytical_inventory CASCADE;
DROP TABLE IF EXISTS cdc_audit_ledger CASCADE;
DROP TABLE IF EXISTS operational_inventory CASCADE;

-- 1. Source Operational Inventory Table
CREATE TABLE IF NOT EXISTS operational_inventory (
    item_id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    item_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    quantity INT NOT NULL CHECK (quantity >= 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    row_version INT NOT NULL DEFAULT 1,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Append-Only CDC Audit Ledger
CREATE TABLE IF NOT EXISTS cdc_audit_ledger (
    event_id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    row_key INT NOT NULL,
    old_row JSONB,
    new_row JSONB,
    row_version INT NOT NULL,
    captured_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_processed BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_cdc_audit_unprocessed ON cdc_audit_ledger (is_processed, event_id);

-- 3. Analytical Target Table (Replica)
CREATE TABLE IF NOT EXISTS analytical_inventory (
    item_id INT PRIMARY KEY,
    sku VARCHAR(50) NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    quantity INT NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    replicated_version INT NOT NULL,
    last_cdc_operation VARCHAR(10) NOT NULL,
    replicated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- 4. Version Increment Trigger (BEFORE UPDATE on operational_inventory)
CREATE OR REPLACE FUNCTION fn_bump_inventory_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.row_version := OLD.row_version + 1;
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_bump_version ON operational_inventory;
CREATE TRIGGER trg_bump_version
BEFORE UPDATE ON operational_inventory
FOR EACH ROW
EXECUTE FUNCTION fn_bump_inventory_version();

-- 5. CDC Event Capture Trigger (AFTER INSERT OR UPDATE OR DELETE on operational_inventory)
CREATE OR REPLACE FUNCTION fn_capture_inventory_cdc()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO cdc_audit_ledger (
            table_name, operation, row_key, old_row, new_row, row_version, captured_at
        ) VALUES (
            TG_TABLE_NAME, 'INSERT', NEW.item_id, NULL, to_jsonb(NEW), NEW.row_version, CURRENT_TIMESTAMP
        );
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO cdc_audit_ledger (
            table_name, operation, row_key, old_row, new_row, row_version, captured_at
        ) VALUES (
            TG_TABLE_NAME, 'UPDATE', NEW.item_id, to_jsonb(OLD), to_jsonb(NEW), NEW.row_version, CURRENT_TIMESTAMP
        );
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO cdc_audit_ledger (
            table_name, operation, row_key, old_row, new_row, row_version, captured_at
        ) VALUES (
            TG_TABLE_NAME, 'DELETE', OLD.item_id, to_jsonb(OLD), NULL, OLD.row_version, CURRENT_TIMESTAMP
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_capture_cdc ON operational_inventory;
CREATE TRIGGER trg_capture_cdc
AFTER INSERT OR UPDATE OR DELETE ON operational_inventory
FOR EACH ROW
EXECUTE FUNCTION fn_capture_inventory_cdc();
