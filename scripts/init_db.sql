-- init_db.sql : Initialisation PostgreSQL au démarrage du container
-- Exécuté automatiquement par docker-entrypoint-initdb.d

CREATE SCHEMA IF NOT EXISTS public;

DROP TABLE IF EXISTS public.products;

CREATE TABLE public.products (
    product_id          TEXT,
    name                TEXT,
    brand               TEXT,
    category            TEXT,
    site                TEXT,
    price               INTEGER,
    url                 TEXT,
    scraped_at          TIMESTAMP,
    category_avg_price  FLOAT,
    price_deviation     FLOAT,
    price_rank          INTEGER,
    price_zscore        FLOAT,
    is_outlier          BOOLEAN
);

-- Vue agrégée prix par site + catégorie + brand
CREATE OR REPLACE VIEW public.v_price_summary AS
SELECT
    site,
    category,
    brand,
    COUNT(*)                            AS total_products,
    ROUND(AVG(price)::NUMERIC, 2)       AS avg_price,
    MIN(price)                          AS min_price,
    MAX(price)                          AS max_price,
    ROUND(STDDEV(price)::NUMERIC, 2)    AS stddev_price
FROM public.products
WHERE price > 0
GROUP BY site, category, brand;

-- Vue outliers
CREATE OR REPLACE VIEW public.v_outliers AS
SELECT
    product_id,
    name,
    brand,
    category,
    site,
    price,
    price_zscore,
    category_avg_price,
    price_deviation
FROM public.products
WHERE is_outlier = TRUE
ORDER BY ABS(price_zscore) DESC;