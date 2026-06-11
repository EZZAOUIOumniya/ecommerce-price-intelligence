WITH cleaned AS (
    SELECT * FROM {{ ref('cleaned_prices') }}
),

site_prices AS (
    SELECT
        product_slug,
        name,
        brand,
        category,
        site,
        ROUND(AVG(price), 0)                            AS avg_price,
        MIN(price)                                      AS min_price,
        MAX(price)                                      AS max_price,
        COUNT(*)                                        AS observations,
        MIN(scraped_date)                               AS first_seen,
        MAX(scraped_date)                               AS last_seen
    FROM cleaned
    GROUP BY product_slug, name, brand, category, site
),

best_price AS (
    SELECT
        product_slug,
        MIN(avg_price)                                  AS best_avg_price
    FROM site_prices
    GROUP BY product_slug
)

SELECT
    sp.product_slug,
    sp.name,
    sp.brand,
    sp.category,
    sp.site,
    sp.avg_price,
    sp.min_price,
    sp.max_price,
    sp.observations,
    sp.first_seen,
    sp.last_seen,
    bp.best_avg_price,
    ROUND(
        SAFE_DIVIDE(sp.avg_price - bp.best_avg_price, bp.best_avg_price) * 100,
        2
    )                                                   AS price_premium_pct,
    (sp.avg_price = bp.best_avg_price)                 AS is_cheapest_site
FROM site_prices sp
JOIN best_price bp USING (product_slug)
ORDER BY sp.product_slug, sp.avg_price ASC
