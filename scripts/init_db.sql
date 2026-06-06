-- Créé automatiquement au démarrage de PostgreSQL
CREATE SCHEMA IF NOT EXISTS public;

CREATE TABLE IF NOT EXISTS public.products (
    product_id      TEXT,
    site            TEXT,
    brand           TEXT,
    category        TEXT,
    name            TEXT,
    price           INTEGER,
    url             TEXT,
    scraped_at      TIMESTAMP,
    category_avg_price FLOAT,
    price_deviation FLOAT,
    price_rank      INTEGER,
    price_zscore    FLOAT,
    is_outlier      BOOLEAN
);

-- Vue utile pour le data analyst
CREATE OR REPLACE VIEW public.v_price_summary AS
SELECT
    site,
    category,
    brand,
    COUNT(*)                    AS total_products,
    ROUND(AVG(price)::NUMERIC, 2) AS avg_price,
    MIN(price)                  AS min_price,
    MAX(price)                  AS max_price,
    ROUND(STDDEV(price)::NUMERIC, 2) AS stddev_price
FROM public.products
WHERE price > 0
GROUP BY site, category, brand;