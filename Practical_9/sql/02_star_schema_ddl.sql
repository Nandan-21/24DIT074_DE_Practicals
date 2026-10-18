-- ====================================================================
-- PRACTICAL 9: KIMBALL STAR SCHEMA DDL
-- ====================================================================

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_store;
DROP TABLE IF EXISTS dim_date;

-- 1. Date Dimension
CREATE TABLE dim_date (
    date_key INT PRIMARY KEY,
    full_date DATE NOT NULL,
    day_of_month INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    quarter INT NOT NULL,
    year INT NOT NULL,
    day_of_week VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

-- 2. Customer Dimension (SCD Type 2 Enabled)
CREATE TABLE dim_customer (
    customer_key INT PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    customer_email VARCHAR(100) NOT NULL,
    customer_city VARCHAR(100) NOT NULL,
    customer_segment VARCHAR(50) NOT NULL,
    effective_start_date DATE NOT NULL,
    effective_end_date DATE,
    is_current BOOLEAN NOT NULL
);

CREATE INDEX idx_dim_cust_lookup ON dim_customer (customer_id, is_current);

-- 3. Product Dimension
CREATE TABLE dim_product (
    product_key INT PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50) NOT NULL,
    unit_cost DOUBLE NOT NULL,
    unit_price DOUBLE NOT NULL
);

-- 4. Store Dimension
CREATE TABLE dim_store (
    store_key INT PRIMARY KEY,
    store_id VARCHAR(50) NOT NULL UNIQUE,
    store_name VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    store_type VARCHAR(50) NOT NULL
);

-- 5. Fact Sales Table (Grain: 1 row per product line item per order)
CREATE TABLE fact_sales (
    sales_key BIGINT PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    line_item INT NOT NULL,
    date_key INT NOT NULL REFERENCES dim_date(date_key),
    customer_key INT NOT NULL REFERENCES dim_customer(customer_key),
    product_key INT NOT NULL REFERENCES dim_product(product_key),
    store_key INT NOT NULL REFERENCES dim_store(store_key),
    quantity INT NOT NULL,
    unit_price DOUBLE NOT NULL,
    discount_rate DOUBLE NOT NULL,
    gross_amount DOUBLE NOT NULL,
    discount_amount DOUBLE NOT NULL,
    net_amount DOUBLE NOT NULL,
    cost_amount DOUBLE NOT NULL,
    profit_amount DOUBLE NOT NULL
);
