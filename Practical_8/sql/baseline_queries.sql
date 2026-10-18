-- ====================================================================
-- PRACTICAL 8: BASELINE UNOPTIMIZED ANALYTICAL QUERIES
-- ====================================================================

-- Query 1: Unoptimized Multi-Stage Aggregation (Full table scan with all columns)
SELECT 
    region,
    device_type,
    event_type,
    COUNT(*) AS total_events,
    COUNT(DISTINCT user_id) AS unique_users,
    AVG(response_time_ms) AS avg_response_time,
    MAX(response_time_ms) AS max_response_time
FROM raw_clickstream
WHERE response_time_ms > 100
GROUP BY region, device_type, event_type
ORDER BY total_events DESC;

-- Query 2: Date-Range Regional Filter on Unpartitioned Table (Full table scan)
SELECT 
    region,
    event_date,
    COUNT(*) as daily_events,
    AVG(response_time_ms) as avg_latency
FROM raw_clickstream
WHERE event_date BETWEEN '2026-01-10' AND '2026-01-17'
GROUP BY region, event_date
ORDER BY region, event_date;

-- Query 3: Supplementary Problem - Correlated Nested Subqueries
SELECT 
    m.user_id,
    m.page_url,
    m.device_type,
    m.response_time_ms,
    (SELECT AVG(s.response_time_ms) FROM raw_clickstream s WHERE s.page_url = m.page_url) AS avg_page_latency,
    (SELECT COUNT(*) FROM raw_clickstream s2 WHERE s2.user_id = m.user_id) AS total_user_events
FROM raw_clickstream m
WHERE m.device_type = 'mobile' AND m.response_time_ms > 500
ORDER BY m.response_time_ms DESC
LIMIT 50;
