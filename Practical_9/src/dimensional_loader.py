from datetime import datetime, timedelta
import duckdb

def populate_star_schema(con: duckdb.DuckDBPyConnection):
    """
    Populates Kimball Star Schema dimensions and fact table from cleaned staging data,
    including SCD Type 2 handling for customers.
    """
    # 1. Populate dim_date for year 2025
    con.execute("DELETE FROM dim_date;")
    con.execute("""
        WITH RECURSIVE dates AS (
            SELECT CAST('2025-01-01' AS DATE) AS d
            UNION ALL
            SELECT d + INTERVAL 1 DAY FROM dates WHERE d < CAST('2025-12-31' AS DATE)
        )
        INSERT INTO dim_date (date_key, full_date, day_of_month, month, month_name, quarter, year, day_of_week, is_weekend)
        SELECT 
            CAST(STRFTIME(d, '%Y%m%d') AS INT) AS date_key,
            d AS full_date,
            EXTRACT(DAY FROM d) AS day_of_month,
            EXTRACT(MONTH FROM d) AS month,
            STRFTIME(d, '%B') AS month_name,
            EXTRACT(QUARTER FROM d) AS quarter,
            EXTRACT(YEAR FROM d) AS year,
            STRFTIME(d, '%A') AS day_of_week,
            CASE WHEN EXTRACT(DOW FROM d) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend
        FROM dates;
    """)

    # 2. Populate dim_product
    con.execute("DELETE FROM dim_product;")
    con.execute("""
        INSERT INTO dim_product (product_key, product_id, product_name, category, subcategory, unit_cost, unit_price)
        SELECT 
            ROW_NUMBER() OVER (ORDER BY product_id) AS product_key,
            product_id,
            product_name,
            category,
            subcategory,
            unit_cost,
            unit_price
        FROM (
            SELECT DISTINCT product_id, product_name, category, subcategory, unit_cost, unit_price
            FROM stg_sales_cleaned
        );
    """)

    # 3. Populate dim_store
    con.execute("DELETE FROM dim_store;")
    con.execute("""
        INSERT INTO dim_store (store_key, store_id, store_name, region, store_type)
        SELECT 
            ROW_NUMBER() OVER (ORDER BY store_id) AS store_key,
            store_id,
            store_name,
            store_region AS region,
            store_type
        FROM (
            SELECT DISTINCT store_id, store_name, store_region, store_type
            FROM stg_sales_cleaned
        );
    """)

    # 4. Populate dim_customer with SCD Type 2
    con.execute("DELETE FROM dim_customer;")
    
    # We identify early records (< 2025-07-01) and later records (>= 2025-07-01)
    con.execute("""
        -- Version 1 (Historical superseded version)
        INSERT INTO dim_customer (customer_key, customer_id, customer_name, customer_email, customer_city, customer_segment, effective_start_date, effective_end_date, is_current)
        SELECT 
            ROW_NUMBER() OVER (ORDER BY customer_id) AS customer_key,
            customer_id,
            customer_name,
            customer_email,
            customer_city,
            customer_segment,
            CAST('2025-01-01' AS DATE) AS effective_start_date,
            CAST('2025-06-30' AS DATE) AS effective_end_date,
            FALSE AS is_current
        FROM (
            SELECT DISTINCT customer_id, customer_name, customer_email, customer_city, customer_segment
            FROM stg_sales_cleaned
            WHERE order_date < CAST('2025-07-01' AS DATE)
        );

        -- Version 2 (Current active version)
        INSERT INTO dim_customer (customer_key, customer_id, customer_name, customer_email, customer_city, customer_segment, effective_start_date, effective_end_date, is_current)
        SELECT 
            (SELECT COALESCE(MAX(customer_key), 0) FROM dim_customer) + ROW_NUMBER() OVER (ORDER BY customer_id) AS customer_key,
            customer_id,
            customer_name,
            customer_email,
            customer_city,
            customer_segment,
            CAST('2025-07-01' AS DATE) AS effective_start_date,
            NULL AS effective_end_date,
            TRUE AS is_current
        FROM (
            SELECT DISTINCT customer_id, customer_name, customer_email, customer_city, customer_segment
            FROM stg_sales_cleaned
            WHERE order_date >= CAST('2025-07-01' AS DATE)
        );
    """)

    # 5. Populate fact_sales with historical surrogate key resolution
    con.execute("DELETE FROM fact_sales;")
    con.execute("""
        INSERT INTO fact_sales (
            sales_key, order_id, line_item, date_key, customer_key, product_key, store_key,
            quantity, unit_price, discount_rate, gross_amount, discount_amount, net_amount, cost_amount, profit_amount
        )
        SELECT 
            ROW_NUMBER() OVER (ORDER BY s.order_date, s.order_id, s.line_item) AS sales_key,
            s.order_id,
            s.line_item,
            s.date_key,
            c.customer_key,
            p.product_key,
            st.store_key,
            s.quantity,
            s.unit_price,
            s.discount_rate,
            s.gross_amount,
            s.discount_amount,
            s.net_amount,
            s.cost_amount,
            s.profit_amount
        FROM stg_sales_cleaned s
        JOIN dim_product p ON s.product_id = p.product_id
        JOIN dim_store st ON s.store_id = st.store_id
        JOIN dim_customer c ON s.customer_id = c.customer_id 
             AND s.order_date >= c.effective_start_date 
             AND (c.effective_end_date IS NULL OR s.order_date <= c.effective_end_date);
    """)
