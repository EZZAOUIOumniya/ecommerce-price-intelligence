WITH cleaned AS (
    SELECT * FROM {{ ref('cleaned_prices') }}
)

SELECT
    scraped_date,
    site,
    category,
    brand,
    name,
    product_slug,
    MIN(price)                                          AS price_min,
    MAX(price)                                          AS price_max,
    AVG(price)                                          AS price_avg,
    APPROX_QUANTILES(price, 2)[OFFSET(1)]              AS price_median,
    STDDEV(price)                                       AS price_stddev,
    MAX(price) - MIN(price)                             AS price_range,
    COUNT(*)                                            AS scrape_count,
    ARRAY_AGG(price ORDER BY scraped_at ASC  LIMIT 1)[OFFSET(0)] AS price_open,
    ARRAY_AGG(price ORDER BY scraped_at DESC LIMIT 1)[OFFSET(0)] AS price_close,
    ARRAY_AGG(price ORDER BY scraped_at DESC LIMIT 1)[OFFSET(0)]
    - ARRAY_AGG(price ORDER BY scraped_at ASC LIMIT 1)[OFFSET(0)] AS price_change_day
FROM cleaned
GROUP BY
    scraped_date, site, category, brand, name, product_slug
