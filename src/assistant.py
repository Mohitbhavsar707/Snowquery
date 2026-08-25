from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_DOCUMENTS = {
    "fct_orders": (
        "fct_orders: one row per order. Columns: order_id, order_date, customer_id, "
        "customer_name, category, region, quantity, revenue. Use for order counts, "
        "sales, revenue, category, region, customer, and time analysis."
    ),
    "mart_monthly_sales": (
        "mart_monthly_sales: monthly aggregate. Columns: order_month, order_count, "
        "units_sold, revenue. Use for monthly trends and month-over-month sales."
    ),
    "mart_category_sales": (
        "mart_category_sales: category aggregate. Columns: category, order_count, "
        "units_sold, revenue. Use for category performance and product category sales."
    ),
}


@dataclass
class AssistantResponse:
    answer: str
    sql: str
    rows: pd.DataFrame
    context: list[str]
    retrieved_models: list[str]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def retrieve_schema(question: str, k: int = 2) -> list[tuple[str, str]]:
    query = _tokens(question)
    synonyms = {
        "sales": {"revenue", "sales"},
        "orders": {"order", "orders", "order_count"},
        "monthly": {"month", "monthly", "order_month", "trend"},
    }
    expanded = set(query)
    for token in query:
        expanded |= synonyms.get(token, set())
    scored = []
    for model, document in SCHEMA_DOCUMENTS.items():
        overlap = len(expanded & _tokens(document))
        if model == "fct_orders" and query & {"customer", "customers", "region", "total"}:
            overlap += 4
        if model == "mart_monthly_sales" and query & {"month", "monthly", "trend"}:
            overlap += 4
        if model == "mart_category_sales" and "category" in query:
            overlap += 4
        scored.append((overlap, model, document))
    return [(model, doc) for _, model, doc in sorted(scored, reverse=True)[:k]]


def plan_sql(question: str) -> tuple[str, str]:
    q = question.lower()
    if "category" in q:
        return (
            "mart_category_sales",
            "SELECT category, order_count, units_sold, ROUND(revenue, 2) AS revenue "
            "FROM mart_category_sales ORDER BY revenue DESC",
        )
    if "month" in q or "trend" in q:
        return (
            "mart_monthly_sales",
            "SELECT order_month, order_count, units_sold, ROUND(revenue, 2) AS revenue "
            "FROM mart_monthly_sales ORDER BY order_month",
        )
    if "region" in q:
        return (
            "fct_orders",
            "SELECT region, COUNT(DISTINCT order_id) AS order_count, "
            "ROUND(SUM(revenue), 2) AS revenue FROM fct_orders "
            "GROUP BY region ORDER BY order_count DESC",
        )
    if "customer" in q or "customers" in q:
        limit_match = re.search(r"top\s+(\d+)", q)
        limit = min(int(limit_match.group(1)), 20) if limit_match else 5
        return (
            "fct_orders",
            "SELECT customer_name, COUNT(DISTINCT order_id) AS order_count, "
            "ROUND(SUM(revenue), 2) AS revenue FROM fct_orders "
            f"GROUP BY customer_name ORDER BY revenue DESC LIMIT {limit}",
        )
    if "total" in q and ("revenue" in q or "sales" in q):
        return "fct_orders", "SELECT ROUND(SUM(revenue), 2) AS total_revenue FROM fct_orders"
    raise ValueError(
        "I can currently answer questions about revenue, categories, regions, customers, "
        "and monthly trends. This narrow scope keeps the demo safe and measurable."
    )


class GroundedAssistant:
    def __init__(self, backend: str = "duckdb"):
        self.backend = backend

    def _execute(self, sql: str) -> pd.DataFrame:
        if not re.match(r"^\s*select\b", sql, re.IGNORECASE):
            raise ValueError("Only SELECT statements are allowed")
        if ";" in sql.rstrip(";"):
            raise ValueError("Multiple SQL statements are not allowed")
        if self.backend == "snowflake":
            import snowflake.connector

            connection = snowflake.connector.connect(
                account=os.environ["SNOWFLAKE_ACCOUNT"],
                user=os.environ["SNOWFLAKE_USER"],
                password=os.environ["SNOWFLAKE_PASSWORD"],
                role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
                warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "RAG_WH"),
                database=os.getenv("SNOWFLAKE_DATABASE", "RAG_DEMO"),
                schema=os.getenv("SNOWFLAKE_SCHEMA", "ANALYTICS"),
            )
            try:
                return pd.read_sql(sql, connection)
            finally:
                connection.close()
        import duckdb

        db_path = ROOT / "local.duckdb"
        if not db_path.exists():
            raise RuntimeError("Run `python scripts/bootstrap_local.py` first")
        with duckdb.connect(str(db_path), read_only=True) as connection:
            return connection.execute(sql).fetchdf()

    def ask(self, question: str) -> AssistantResponse:
        retrieved = retrieve_schema(question)
        expected_model, sql = plan_sql(question)
        rows = self._execute(sql)
        if rows.empty:
            answer = "The query returned no matching rows."
        elif len(rows) == 1 and len(rows.columns) == 1:
            answer = f"The result is **{rows.iloc[0, 0]}**."
        else:
            leader = rows.iloc[0]
            answer = (
                f"The query returned **{len(rows)} row(s)**. The leading result is "
                f"**{leader.iloc[0]}**, with {leader.index[-1]} = **{leader.iloc[-1]}**."
            )
        return AssistantResponse(
            answer=answer,
            sql=sql,
            rows=rows,
            context=[doc for _, doc in retrieved],
            retrieved_models=[model for model, _ in retrieved],
        )
