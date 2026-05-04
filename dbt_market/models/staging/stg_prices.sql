with source as (
    select * from read_json_auto('/tmp/raw_data.json')
),

normalized as (
    select
        *,
        -- Standardize: Uppercase, remove technical specs in (), trim whitespace
        upper(trim(regexp_replace(name, '\(.*\)', '', 'g'))) as normalized_name
    from source
),

cleaned as (
    select
        product_id,
        site,
        normalized_name as name,
        brand,
        category,
        url,
        cast(price as bigint) as price,
        cast(scraped_at as timestamp) as scraped_at
    from normalized
    where normalized_name is not null 
      and normalized_name != ''
      and site is not null
      and price > 10 
      and price < 200000
)

select * from cleaned
