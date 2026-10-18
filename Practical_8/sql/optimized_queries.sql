-- ====================================================================
-- PRACTICAL 8: OPTIMIZED ANALYTICAL QUERIES
-- ====================================================================

-- Query 1 Optimized: Columnar Projection Pushdown & Index / Pre-aggregation
SELECT 
    region,
    device_type,
    event_type,
    COUNT(*) AS total_events,
    APPROX_COUNT_DISTINCT(user_id) AS unique_users,
    AVG(response_time_ms) AS avg_response_time,
    MAX(response_time_ms) AS max_response_time
FROM clickstream_indexed
WHERE response_time_ms > 100
GROUP BY region, device_type, event_type
ORDER BY total_events DESC;

-- Query 2 Optimized: Parquet Hive-Partition Pruning (Only scans relevant partition files)
SELECT 
    region,
    event_date,
    COUNT(*) as daily_events,
    AVG(response_time_ms) as avg_latency
FROM read_parquet('outputs/partitioned_clickstream/**/*.parquet', hive_partitioning=1)
WHERE event_date BETWEEN '2026-01-10' AND '2026-01-17'
GROUP BY region, event_date
ORDER BY region, event_date;

-- Query 3 Optimized: Supplementary Problem - Window Functions & CTEs (Single Table Pass)
WITH filtered_events AS (
    SELECT 
        user_id,
        page_url,
        device_type,
        response_time_ms,
        AVG(response_time_ms) OVER(PARTITION BY page_url) AS avg_page_latency,
        COUNT(*) OVER(PARTITION BY user_id) AS total_user_events
    FROM clickstream_indexed
    WHERE device_type = 'mobile' AND response_time_ms > 500
)
SELECT 
    user_id,
    page_url,
    device_type,
    response_time_ms,
    avg_page_latency,
    total_user_events
FROM filtered_events
ORDER BY response_time_ms DESC
LIMIT 50;
