import os

import streamlit as st

from src.assistant import GroundedAssistant


st.set_page_config(page_title="SnowQuery", page_icon="❄️", layout="wide")
st.title("❄️ SnowQuery")
st.caption("Schema RAG → constrained SQL → warehouse result → cited answer")

backend = os.getenv("WAREHOUSE_BACKEND", "duckdb")
st.sidebar.metric("Warehouse", backend.upper())
st.sidebar.write("Every answer below is generated from executed query results.")

assistant = GroundedAssistant(backend=backend)
examples = [
    "What was total revenue by category?",
    "Which region had the most orders?",
    "Show monthly revenue trend",
    "Who are the top 5 customers by revenue?",
]
question = st.selectbox("Try an example", [""] + examples)
question = st.text_input("Or ask a question", value=question)

if question:
    try:
        response = assistant.ask(question)
        st.subheader("Answer")
        st.write(response.answer)
        with st.expander("Retrieved schema context", expanded=True):
            for item in response.context:
                st.code(item)
        st.subheader("Evidence")
        st.dataframe(response.rows, use_container_width=True)
        with st.expander("SQL citation"):
            st.code(response.sql, language="sql")
    except ValueError as exc:
        st.warning(str(exc))
    except Exception as exc:
        st.error(f"Query failed: {exc}")
