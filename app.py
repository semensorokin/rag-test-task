"""
Streamlit application for RAG-based tabular data chat.

Provides a chat interface and statistics dashboard for querying
business data using natural language.
"""

import os

import pandas as pd
import streamlit as st

from src.chain import ask, get_pipeline_stats, pipeline
from src.config import LLM_MODEL, TABLE_FILES
from src.database import DB_PATH, get_engine, init_database

st.set_page_config(
    page_title="Tabular Data Chat",
    page_icon="📊",
    layout="wide",
)


@st.cache_resource
def setup():
    """Initialize database and pipeline on first load."""
    if not os.path.exists(DB_PATH):
        init_database()
    pipeline.initialize()
    return True


with st.spinner("Initializing..."):
    setup()

with st.sidebar:
    st.header("Example Questions")
    examples = [
        "List all clients with their industries.",
        "Which clients are based in the UK?",
        "List all invoices issued in March 2024 with their statuses.",
        "Which invoices are currently marked as 'Overdue'?",
        "For each service_name, how many line items are there?",
        "List all invoices for Acme Corp with their invoice IDs, dates, and statuses.",
        "For invoice I1001, list all line items with service name, quantity, unit price, tax rate, and line total.",
        "Which client has the highest total billed amount in 2024?",
    ]

    for example in examples:
        if st.button(example, key=example, width="stretch"):
            st.session_state.selected_example = example
            st.rerun()

tab_chat, tab_stats = st.tabs(["💬 Chat", "📈 Statistics"])

with tab_chat:
    st.title("📊 Chat with Your Business Data")
    st.markdown("Ask questions about clients, invoices, and line items.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    chat_container = st.container(height=600)

    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "sql" in message:
                    with st.expander("View SQL Query"):
                        st.code(message["sql"], language="sql")
                if "results" in message and message["results"]:
                    with st.expander(f"View Raw Data ({len(message['results'])} rows)"):
                        st.dataframe(message["results"], width="stretch")
                if "response_time" in message:
                    st.caption(f"⏱️ {message['response_time']:.2f}s")

    user_input = st.chat_input("Type your question here...")

    if "selected_example" in st.session_state:
        prompt = st.session_state.selected_example
        del st.session_state.selected_example
    elif user_input:
        prompt = user_input
    else:
        prompt = None

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.spinner("Thinking..."):
            result = ask(prompt)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "sql": result["sql_query"],
                "results": result.get("results", []),
                "response_time": result.get("response_time", 0),
            }
        )
        st.rerun()

with tab_stats:
    st.title("📈 Pipeline Statistics")

    stats = get_pipeline_stats()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Queries", stats["total_queries"])
    with col2:
        st.metric("Successful", stats["successful_queries"])
    with col3:
        st.metric("Failed", stats["failed_queries"])
    with col4:
        st.metric("Avg Response Time", f"{stats['avg_response_time']:.2f}s")

    st.divider()

    if stats.get("last_query"):
        st.markdown("### 🔍 Last Query Analysis")

        lq = stats["last_query"]
        analysis = lq.get("analysis", {})

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Response Time", f"{lq['response_time']:.2f}s")
        with col2:
            st.metric("Rows Returned", lq.get("row_count", 0))
        with col3:
            st.metric("Columns", lq.get("col_count", 0))
        with col4:
            st.metric("Query Type", analysis.get("query_type", "N/A"))

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Query Breakdown")
            breakdown_data = {
                "Metric": [
                    "Tables Used",
                    "Join Operations",
                    "Has Aggregation",
                    "Has GROUP BY",
                    "Has Filter (WHERE)",
                    "Has Ordering",
                    "Has Limit",
                ],
                "Value": [
                    ", ".join(analysis.get("tables_used", [])) or "N/A",
                    str(analysis.get("join_count", 0)),
                    "✅" if analysis.get("has_aggregation") else "❌",
                    "✅" if analysis.get("has_group_by") else "❌",
                    "✅" if analysis.get("has_filter") else "❌",
                    "✅" if analysis.get("has_order") else "❌",
                    "✅" if analysis.get("has_limit") else "❌",
                ],
            }
            st.dataframe(pd.DataFrame(breakdown_data), hide_index=True, width="stretch")

        with col2:
            st.markdown("#### Question")
            st.info(lq["question"])

            st.markdown("#### Final SQL")
            st.code(lq.get("sql_query", "N/A"), language="sql")

        if lq.get("intermediate"):
            st.markdown("#### 📊 Intermediate Results (Pre-Aggregation Data)")
            inter = lq["intermediate"]

            with st.expander(
                f"View data before aggregation ({inter['row_count']} rows, "
                f"{inter['col_count']} columns)",
                expanded=True,
            ):
                st.markdown("**Query used:**")
                st.code(inter["query"], language="sql")
                st.markdown("**Raw data that was aggregated:**")
                if inter["data"]:
                    st.dataframe(inter["data"], width="stretch", height=300)
                else:
                    st.info("No intermediate data")

        st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### System Status")
        status_data = {
            "Component": ["SQLite Database", "OpenAI LLM"],
            "Status": [
                "✅ Connected" if os.path.exists(DB_PATH) else "❌ Not Found",
                "✅ Configured" if os.getenv("OPENAI_API_KEY") else "❌ No API Key",
            ],
        }
        st.dataframe(pd.DataFrame(status_data), hide_index=True, width="stretch")

        st.markdown("### Data Overview")
        engine = get_engine()
        table_stats = []
        for table_name in TABLE_FILES.keys():
            df = pd.read_sql(f"SELECT COUNT(*) as count FROM {table_name}", engine)
            table_stats.append({"Table": table_name, "Rows": df["count"].iloc[0]})
        st.dataframe(pd.DataFrame(table_stats), hide_index=True, width="stretch")

        st.markdown("### Configuration")
        config_data = {
            "Setting": ["LLM Model", "Database"],
            "Value": [LLM_MODEL, "SQLite"],
        }
        st.dataframe(pd.DataFrame(config_data), hide_index=True, width="stretch")

    with col_right:
        st.markdown("### Query History")
        if stats["query_history"]:
            history_data = []
            for h in stats["query_history"]:
                history_data.append(
                    {
                        "Question": h["question"][:40] + "...",
                        "Time": f"{h['response_time']:.2f}s",
                        "Rows": h.get("row_count", 0),
                        "Tables": h.get("analysis", {}).get("table_count", 0),
                        "OK": "✅" if h["success"] else "❌",
                    }
                )
            st.dataframe(pd.DataFrame(history_data), hide_index=True, width="stretch")

            st.markdown("### Response Times")
            times = [h["response_time"] for h in stats["query_history"]]
            st.line_chart(times, use_container_width=True)
        else:
            st.info("No queries yet. Ask some questions in the Chat tab!")
