SELECT
    category,
    COUNT(*)                        AS total_products,
    ROUND(AVG(price)::NUMERIC, 2)   AS avg_price,
    MIN(price)                      AS min_price,
    MAX(price)                      AS max_price,
    ROUND(STDDEV(price)::NUMERIC,2) AS stddev_price
FROM {{ ref('stg_products') }}
WHERE price IS NOT NULL
GROUP BY category
ORDER BY avg_price DESC