import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import os
import sys

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import load_csv_to_db, get_schema_info, list_tables

from text2sql_engine import (
    Text2SQLEngine,
    get_schema_for_prompt,
    generate_sql,
    execute_generated_sql,
    generate_visualization_code,
)

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="TechCorp HR Analytics",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CUSTOM CSS — chat bubbles, constrained width
# ============================================================
st.markdown("""
<style>
    /* Constrain main content width */
    .main .block-container {
        max-width: 860px;
        margin: 0 auto;
        padding-top: 2rem;
    }

    /* User bubble — right aligned */
    .user-bubble {
        display: flex;
        justify-content: flex-end;
        margin: 8px 0;
    }
    .user-bubble .bubble {
        background-color: #4A90D9;
        color: white;
        padding: 10px 16px;
        border-radius: 18px 18px 4px 18px;
        max-width: 70%;
        font-size: 0.95rem;
        line-height: 1.4;
    }

    /* AI bubble — left aligned */
    .ai-bubble {
        display: flex;
        justify-content: flex-start;
        margin: 8px 0;
    }
    .ai-bubble .bubble {
        background-color: #F0F2F6;
        color: #1a1a1a;
        padding: 10px 16px;
        border-radius: 18px 18px 18px 4px;
        max-width: 70%;
        font-size: 0.95rem;
        line-height: 1.4;
    }

    /* Avatar labels */
    .avatar {
        font-size: 0.75rem;
        color: #888;
        margin-bottom: 2px;
    }
    .avatar-right { text-align: right; }
    .avatar-left  { text-align: left; }
</style>
""", unsafe_allow_html=True)

api_key = os.getenv("GOOGLE_API_KEY")

st.title("🏢 TechCorp HR Analytics")
st.caption("Ask questions about your company data in plain English")

# ============================================================
# SIDEBAR: Configuration & Schema Explorer
# ============================================================
with st.sidebar:
    data_path = os.path.join(SCRIPT_DIR, "data")
    conn = load_csv_to_db(data_path)

    st.header("📋 Database Schema")
    st.caption("Reference these tables when asking questions")

    try:
        tables_query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        tables_result = conn.execute(tables_query).fetchall()
        tables = [t[0] for t in tables_result]

        if not tables:
            st.info("No tables found. Please check if CSV files were loaded correctly.")
        else:
            for table_name in tables:
                with st.expander(f"📊 {table_name}"):
                    try:
                        row_count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
                        st.metric("Row Count", f"{row_count:,}")
                    except Exception as e:
                        st.error(f"Error counting rows: {e}")

                    try:
                        schema_info = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
                        if schema_info:
                            st.write("**Columns:**")
                            schema_df = pd.DataFrame(
                                schema_info,
                                columns=["cid", "name", "type", "notnull", "dflt_value", "pk"]
                            )
                            display_df = schema_df[["name", "type"]].copy()
                            display_df["PK"] = schema_df["pk"].apply(lambda x: "✓" if x else "")
                            st.dataframe(display_df, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error getting schema: {e}")

    except Exception as e:
        st.error(f"Error loading tables: {e}")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if api_key and "engine" not in st.session_state:
        st.session_state.engine = Text2SQLEngine(api_key=api_key, conn=conn)

# ============================================================
# CHAT HISTORY DISPLAY
# ============================================================
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"""
        <div class="avatar avatar-right">You</div>
        <div class="user-bubble"><div class="bubble">{msg["content"]}</div></div>
        """, unsafe_allow_html=True)

    elif msg["role"] == "assistant":
        st.markdown(f"""
        <div class="avatar avatar-left">🤖 AI</div>
        <div class="ai-bubble"><div class="bubble">{msg["content"]}</div></div>
        """, unsafe_allow_html=True)

        if "sql" in msg and msg["sql"]:
            st.code(msg["sql"], language="sql")

        if "data" in msg and msg["data"] is not None and not msg["data"].empty:
            st.dataframe(msg["data"], use_container_width=True)

        if "visualization" in msg and msg["visualization"]:
            local_vars = {"df": msg["data"]}
            try:
                exec(msg["visualization"], local_vars)
                fig = local_vars.get("fig")
                if fig:
                    st.pyplot(fig)
                else:
                    st.warning("No figure generated.")
            except Exception as e:
                st.error(f"Visualization error: {e}")

        st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

# ============================================================
# CHAT INPUT
# ============================================================
user_input = st.chat_input("Ask a question about the data...")

if user_input and api_key:
    # Show user bubble immediately
    st.markdown(f"""
    <div class="avatar avatar-right">You</div>
    <div class="user-bubble"><div class="bubble">{user_input}</div></div>
    """, unsafe_allow_html=True)

    st.session_state.messages.append({"role": "user", "content": user_input})

    # Process and show AI response
    with st.spinner("Thinking..."):
        engine = st.session_state.engine
        sql_query = generate_sql(user_input, engine.client, get_schema_for_prompt(conn))
        success, query_results = execute_generated_sql(sql_query, conn)

        visualization_code = None
        if success:
            visualization_code = generate_visualization_code(
                user_input, sql_query, query_results, engine.client
            )

    st.markdown(f"""
    <div class="avatar avatar-left">🤖 AI</div>
    <div class="ai-bubble"><div class="bubble">Here's what I found:</div></div>
    """, unsafe_allow_html=True)

    st.code(sql_query, language="sql")

    if success and query_results is not None and not query_results.empty:
        st.dataframe(query_results, use_container_width=True)
        if visualization_code:
            local_vars = {"df": query_results}
            try:
                exec(visualization_code, local_vars)
                fig = local_vars.get("fig")
                if fig:
                    st.pyplot(fig)
            except Exception as e:
                st.error(f"Visualization error: {e}")
    elif not success:
        st.error("Query failed. Check the SQL above for errors.")

    st.session_state.messages.append({
        "role": "assistant",
        "content": "Here's what I found:",
        "sql": sql_query,
        "data": query_results,
        "visualization": visualization_code,
    })

elif user_input and not api_key:
    st.error("⚠️ No API key found. Please set GOOGLE_API_KEY in your environment.")


# ============================================================
# OPTIONAL EXTENSIONS (for additional practice)
# ============================================================

# OPTIONAL TODO A: Add a "Show SQL History" sidebar section
# Display previously executed queries in the sidebar.

# OPTIONAL TODO B: Add a "Custom SQL" tab
# Let users type and execute their own SQL queries with validation.

# OPTIONAL TODO C: Add conversation memory
# Include previous Q&A pairs in the prompt for contextual follow-up questions.

# OPTIONAL TODO D: Add a data export button
# Let users download query results as CSV.

# OPTIONAL TODO E: Add a "Suggested Questions" section
# Show clickable starter questions to help users get started.