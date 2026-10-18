-- ====================================================================
-- PRACTICAL 9: ANALYTICAL OLAP REPORTING QUERIES
-- ====================================================================

-- Query 1: Monthly Category Revenue and Profit Margin
SELECT 
    d.year,
    d.month_name,
    p.category,
    SUM(f.quantity) AS total_units_sold,
    ROUND(SUM(f.gross_amount), 2) AS total_gross_sales,
    ROUND(SUM(f.net_amount), 2) AS total_net_revenue,
    ROUND(SUM(f.profit_amount), 2) AS total_profit,
    ROUND(SUM(f.profit_amount) / NULLIF(SUM(f.net_amount), 0) * 100, 2) AS profit_margin_pct
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY d.year, d.month, d.month_name, p.category
ORDER BY d.year, d.month, total_net_revenue DESC;

-- Query 2: Customer Sales Analysis by City & Segment across Historical Versions (SCD Type 2)
SELECT 
    c.customer_id,
    c.customer_name,
    c.customer_city,
    c.is_current,
    COUNT(DISTINCT f.order_id) AS total_orders,
    ROUND(SUM(f.net_amount), 2) AS total_spend,
    MIN(d.full_date) AS earliest_order,
    MAX(d.full_date) AS latest_order
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.customer_key
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY c.customer_id, c.customer_name, c.customer_city, c.is_current
ORDER BY c.customer_id, earliest_order;

-- Query 3: Regional Store Performance Drill-Down
SELECT 
    s.region,
    s.store_name,
    s.store_type,
    COUNT(DISTINCT f.order_id) AS total_orders,
    ROUND(SUM(f.net_amount), 2) AS store_revenue,
    ROUND(AVG(f.net_amount), 2) AS avg_line_item_value
FROM fact_sales f
JOIN dim_store s ON f.store_key = s.store_key
GROUP BY s.region, s.store_name, s.store_type
ORDER BY store_revenue DESC;
