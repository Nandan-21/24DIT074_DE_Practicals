-- ====================================================================
-- PRACTICAL 9: SNOWFLAKE SCHEMA DDL (SUPPLEMENTARY PROBLEM)
-- ====================================================================

DROP TABLE IF EXISTS fact_sales_snow;
DROP TABLE IF EXISTS dim_product_snow;
DROP TABLE IF EXISTS dim_subcategory_snow;
DROP TABLE IF EXISTS dim_category_snow;
DROP TABLE IF EXISTS dim_store_snow;
DROP TABLE IF EXISTS dim_region_snow;

-- Normalized Category Hierarchy
CREATE TABLE dim_category_snow (
    category_id INT PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE dim_subcategory_snow (
    subcategory_id INT PRIMARY KEY,
    category_id INT NOT NULL REFERENCES dim_category_snow(category_id),
    subcategory_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE dim_product_snow (
    product_key INT PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(100) NOT NULL,
    subcategory_id INT NOT NULL REFERENCES dim_subcategory_snow(subcategory_id),
    unit_cost DOUBLE NOT NULL,
    unit_price DOUBLE NOT NULL
);

-- Normalized Store Geography Hierarchy
CREATE TABLE dim_region_snow (
    region_id INT PRIMARY KEY,
    region_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE dim_store_snow (
    store_key INT PRIMARY KEY,
    store_id VARCHAR(50) NOT NULL UNIQUE,
    store_name VARCHAR(100) NOT NULL,
    region_id INT NOT NULL REFERENCES dim_region_snow(region_id),
    store_type VARCHAR(50) NOT NULL
);

-- Fact table pointing to normalized dimensions
CREATE TABLE fact_sales_snow (
    sales_key BIGINT PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    line_item INT NOT NULL,
    date_key INT NOT NULL,
    customer_key INT NOT NULL,
    product_key INT NOT NULL REFERENCES dim_product_snow(product_key),
    store_key INT NOT NULL REFERENCES dim_store_snow(store_key),
    quantity INT NOT NULL,
    gross_amount DOUBLE NOT NULL,
    discount_amount DOUBLE NOT NULL,
    net_amount DOUBLE NOT NULL,
    cost_amount DOUBLE NOT NULL,
    profit_amount DOUBLE NOT NULL
);
