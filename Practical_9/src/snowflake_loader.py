import duckdb

def populate_snowflake_schema(con: duckdb.DuckDBPyConnection):
    """
    Populates normalized Snowflake dimensions and fact table from cleaned staging data.
    """
    # 1. dim_category_snow
    con.execute("DELETE FROM dim_category_snow;")
    con.execute("""
        INSERT INTO dim_category_snow (category_id, category_name)
        SELECT ROW_NUMBER() OVER (ORDER BY category) AS category_id, category
        FROM (SELECT DISTINCT category FROM stg_sales_cleaned);
    """)

    # 2. dim_subcategory_snow
    con.execute("DELETE FROM dim_subcategory_snow;")
    con.execute("""
        INSERT INTO dim_subcategory_snow (subcategory_id, category_id, subcategory_name)
        SELECT 
            ROW_NUMBER() OVER (ORDER BY s.subcategory) AS subcategory_id,
            c.category_id,
            s.subcategory
        FROM (SELECT DISTINCT category, subcategory FROM stg_sales_cleaned) s
        JOIN dim_category_snow c ON s.category = c.category_name;
    """)

    # 3. dim_product_snow
    con.execute("DELETE FROM dim_product_snow;")
    con.execute("""
        INSERT INTO dim_product_snow (product_key, product_id, product_name, subcategory_id, unit_cost, unit_price)
        SELECT 
            ROW_NUMBER() OVER (ORDER BY p.product_id) AS product_key,
            p.product_id,
            p.product_name,
            sub.subcategory_id,
            p.unit_cost,
            p.unit_price
        FROM (SELECT DISTINCT product_id, product_name, subcategory, unit_cost, unit_price FROM stg_sales_cleaned) p
        JOIN dim_subcategory_snow sub ON p.subcategory = sub.subcategory_name;
    """)

    # 4. dim_region_snow
    con.execute("DELETE FROM dim_region_snow;")
    con.execute("""
        INSERT INTO dim_region_snow (region_id, region_name)
        SELECT ROW_NUMBER() OVER (ORDER BY store_region) AS region_id, store_region
        FROM (SELECT DISTINCT store_region FROM stg_sales_cleaned);
    """)

    # 5. dim_store_snow
    con.execute("DELETE FROM dim_store_snow;")
    con.execute("""
        INSERT INTO dim_store_snow (store_key, store_id, store_name, region_id, store_type)
        SELECT 
            ROW_NUMBER() OVER (ORDER BY s.store_id) AS store_key,
            s.store_id,
            s.store_name,
            r.region_id,
            s.store_type
        FROM (SELECT DISTINCT store_id, store_name, store_region, store_type FROM stg_sales_cleaned) s
        JOIN dim_region_snow r ON s.store_region = r.region_name;
    """)

    # 6. fact_sales_snow
    con.execute("DELETE FROM fact_sales_snow;")
    con.execute("""
        INSERT INTO fact_sales_snow (
            sales_key, order_id, line_item, date_key, customer_key, product_key, store_key,
            quantity, gross_amount, discount_amount, net_amount, cost_amount, profit_amount
        )
        SELECT 
            f.sales_key,
            f.order_id,
            f.line_item,
            f.date_key,
            f.customer_key,
            ps.product_key,
            ss.store_key,
            f.quantity,
            f.gross_amount,
            f.discount_amount,
            f.net_amount,
            f.cost_amount,
            f.profit_amount
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        JOIN dim_product_snow ps ON p.product_id = ps.product_id
        JOIN dim_store s ON f.store_key = s.store_key
        JOIN dim_store_snow ss ON s.store_id = ss.store_id;
    """)
