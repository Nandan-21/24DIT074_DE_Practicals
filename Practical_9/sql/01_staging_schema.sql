-- ====================================================================
-- PRACTICAL 9: STAGING SCHEMA DEFINITION
-- ====================================================================

DROP TABLE IF EXISTS stg_sales_raw;
DROP TABLE IF EXISTS stg_sales_cleaned;

CREATE TABLE stg_sales_raw (
    raw_order_id VARCHAR,
    line_item INT,
    order_date VARCHAR,
    customer_id VARCHAR,
    customer_name VARCHAR,
    customer_email VARCHAR,
    customer_city VARCHAR,
    customer_segment VARCHAR,
    product_id VARCHAR,
    product_name VARCHAR,
    category VARCHAR,
    subcategory VARCHAR,
    unit_cost DOUBLE,
    unit_price DOUBLE,
    store_id VARCHAR,
    store_name VARCHAR,
    store_region VARCHAR,
    store_type VARCHAR,
    quantity INT,
    discount_rate DOUBLE
);

CREATE TABLE stg_sales_cleaned AS
SELECT
    TRIM(raw_order_id) AS order_id,
    line_item,
    CAST(order_date AS DATE) AS order_date,
    CAST(STRFTIME(CAST(order_date AS DATE), '%Y%m%d') AS INT) AS date_key,
    TRIM(customer_id) AS customer_id,
    TRIM(customer_name) AS customer_name,
    LOWER(TRIM(customer_email)) AS customer_email,
    TRIM(customer_city) AS customer_city,
    TRIM(customer_segment) AS customer_segment,
    TRIM(product_id) AS product_id,
    TRIM(product_name) AS product_name,
    TRIM(category) AS category,
    TRIM(subcategory) AS subcategory,
    unit_cost,
    unit_price,
    TRIM(store_id) AS store_id,
    TRIM(store_name) AS store_name,
    TRIM(store_region) AS store_region,
    TRIM(store_type) AS store_type,
    quantity,
    discount_rate,
    ROUND(quantity * unit_price, 2) AS gross_amount,
    ROUND(quantity * unit_price * discount_rate, 2) AS discount_amount,
    ROUND(quantity * unit_price, 2) - ROUND(quantity * unit_price * discount_rate, 2) AS net_amount,
    ROUND(quantity * unit_cost, 2) AS cost_amount,
    (ROUND(quantity * unit_price, 2) - ROUND(quantity * unit_price * discount_rate, 2)) - ROUND(quantity * unit_cost, 2) AS profit_amount
FROM stg_sales_raw
WHERE raw_order_id IS NOT NULL;
