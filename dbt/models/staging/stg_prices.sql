WITH raw AS (
    SELECT
        row_key,
        SPLIT(row_key, '#')[SAFE_OFFSET(0)]             AS site,
        SPLIT(row_key, '#')[SAFE_OFFSET(1)]             AS product_slug,
        price_cf_site                                   AS raw_site,
        price_cf_name                                   AS raw_name,
        SAFE_CAST(price_cf_price AS INT64)              AS price_raw,
        price_cf_brand                                  AS brand,
        price_cf_category                               AS category,
        price_cf_url                                    AS url,
        SAFE.PARSE_TIMESTAMP(
            '%Y-%m-%dT%H:%M:%SZ',
            price_cf_scraped_at
        )                                               AS scraped_at,
        price_cf_scraped_at                             AS scraped_at_raw
    FROM {{ source('bigtable_export', 'price_history_raw') }}
)

SELECT
    row_key,
    COALESCE(raw_site, site)                            AS site,
    product_slug,
    raw_name                                            AS name,
    price_raw,
    UPPER(TRIM(brand))                                  AS brand,
    LOWER(TRIM(category))                               AS category,
    LOWER(url)                                          AS url,
    scraped_at,
    scraped_at_raw
FROM raw
