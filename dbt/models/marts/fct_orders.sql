select
    order_id, order_date, customer_id, customer_name, category, region, quantity,
    quantity * unit_price as revenue
from {{ ref('stg_orders') }}

