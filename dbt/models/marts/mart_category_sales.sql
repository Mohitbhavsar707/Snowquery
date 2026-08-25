select
    category,
    count(distinct order_id) as order_count,
    sum(quantity) as units_sold,
    sum(revenue) as revenue
from {{ ref('fct_orders') }}
group by 1

