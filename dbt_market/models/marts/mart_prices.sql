with base as (
    select * from {{ ref('stg_prices') }}
),

-- Deduplication: Take only the latest snapshot per product/site
deduped as (
    select *
    from (
        select *,
               row_number() over (partition by name, site order by scraped_at desc) as rn
        from base
    )
    where rn = 1
),

final as (
    select
        product_id,
        site,
        brand,
        category,
        name,
        price,
        url,
        scraped_at,
        -- Ensure these window functions are here:
        avg(price) over (partition by category) as category_avg_price,
        price - avg(price) over (partition by category) as price_deviation,
        rank() over (partition by category order by price asc) as price_rank -- ADD THIS
    from deduped
)

select * from final
