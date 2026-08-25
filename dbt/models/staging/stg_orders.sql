select
    order_id,
    to_date(order_date) as order_date,
    customer_id,
    customer_name,
    category,
    region,
    quantity::integer as quantity,
    unit_price::number(12, 2) as unit_price
from {{ ref('raw_orders') }}

