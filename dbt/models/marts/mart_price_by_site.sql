SELECT
    site,
    COUNT(*)                        AS total_products,
    ROUND(AVG(price)::NUMERIC, 2)   AS avg_price,
    MIN(price)                      AS min_price,
    MAX(price)                      AS max_price,
    COUNT(CASE WHEN is_outlier THEN 1 END) AS outlier_count
FROM {{ ref('stg_products') }}
WHERE price IS NOT NULL
GROUP BY site
ORDER BY total_products DESC