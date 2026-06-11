WITH staged AS (
    SELECT * FROM {{ ref('stg_prices') }}
),

deduped AS (
    SELECT *
    FROM staged
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY row_key
        ORDER BY scraped_at DESC NULLS LAST
    ) = 1
),

cleaned AS (
    SELECT
        row_key,
        site,
        product_slug,
        name,
        price_raw                                       AS price,
        brand,
        category,
        url,
        scraped_at,
        DATE(scraped_at)                                AS scraped_date,
        EXTRACT(HOUR FROM scraped_at)                   AS scraped_hour,
        EXTRACT(DAYOFWEEK FROM scraped_at)              AS day_of_week
    FROM deduped
    WHERE
        price_raw >= 100
        AND price_raw <= 200000
        AND scraped_at IS NOT NULL
        AND name IS NOT NULL
        AND TRIM(name) != ''
)

SELECT * FROM cleaned
