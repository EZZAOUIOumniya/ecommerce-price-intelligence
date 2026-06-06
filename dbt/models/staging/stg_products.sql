SELECT
    product_id,
    site,
    brand,
    COALESCE(category, 'N/A')   AS category,
    name,
    NULLIF(price, 0)            AS price,   -- exclure les prix à 0
    url,
    scraped_at::timestamp       AS scraped_at,
    category_avg_price,
    price_deviation,
    price_rank,
    price_zscore,
    is_outlier
FROM {{ source('public', 'products') }}
WHERE site != 'unknown'