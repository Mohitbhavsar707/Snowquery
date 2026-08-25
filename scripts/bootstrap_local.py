from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
db = ROOT / "local.duckdb"
seed = ROOT / "dbt" / "seeds" / "raw_orders.csv"

with duckdb.connect(str(db)) as con:
    con.execute(
        """CREATE OR REPLACE TABLE raw_orders AS
        SELECT * FROM read_csv(?, header=true, delim=',', columns={
          'order_id':'VARCHAR', 'order_date':'DATE', 'customer_id':'VARCHAR',
          'customer_name':'VARCHAR', 'category':'VARCHAR', 'region':'VARCHAR',
          'quantity':'INTEGER', 'unit_price':'DECIMAL(12,2)'})""",
        [str(seed)],
    )
    con.execute("""
        CREATE OR REPLACE VIEW fct_orders AS
        SELECT order_id, CAST(order_date AS DATE) AS order_date, customer_id,
               customer_name, category, region, CAST(quantity AS INTEGER) AS quantity,
               CAST(quantity AS INTEGER) * CAST(unit_price AS DECIMAL(12,2)) AS revenue
        FROM raw_orders
    """)
    con.execute("""
        CREATE OR REPLACE VIEW mart_monthly_sales AS
        SELECT DATE_TRUNC('month', order_date) AS order_month,
               COUNT(DISTINCT order_id) AS order_count, SUM(quantity) AS units_sold,
               SUM(revenue) AS revenue FROM fct_orders GROUP BY 1
    """)
    con.execute("""
        CREATE OR REPLACE VIEW mart_category_sales AS
        SELECT category, COUNT(DISTINCT order_id) AS order_count,
               SUM(quantity) AS units_sold, SUM(revenue) AS revenue
        FROM fct_orders GROUP BY 1
    """)
print(f"Created {db} from {seed}")
