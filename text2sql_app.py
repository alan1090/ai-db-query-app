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

api_key=os.getenv("GOOGLE_API_KEY")

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
            st.info("No tables found in the database. Please check if CSV files were loaded correctly.")
        else:
            for table_name in tables:
                with st.expander(f"📊 {table_name}"):
                    # Conta le righe
                    try:
                        count_query = f'SELECT COUNT(*) FROM "{table_name}"'
                        row_count = conn.execute(count_query).fetchone()[0]
                        st.metric("Row Count", f"{row_count:,}")
                    except Exception as e:
                        st.error(f"Error counting rows: {e}")
                    
                    try:
                        schema_query = f'PRAGMA table_info("{table_name}")'
                        schema_info = conn.execute(schema_query).fetchall()
                        
                        if schema_info:
                            st.write("**Columns:**")
                            schema_df = pd.DataFrame(schema_info, 
                                                    columns=["cid", "name", "type", "notnull", "dflt_value", "pk"])
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

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    elif msg["role"] == "assistant":
        st.markdown(f"**AI:** {msg['content']}")
        if "sql" in msg:
            st.code(msg["sql"], language="sql")
        if "data" in msg:
            st.dataframe(msg["data"])
        if "visualization" in msg and msg["visualization"]:
            if isinstance(msg["visualization"], str):
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

user_input = st.text_input("Ask a question about the data:")
if user_input and api_key:
    st.session_state.messages.append({"role": "user", "content": user_input})

    engine = st.session_state.engine
    sql_query = generate_sql(user_input, engine.client, get_schema_for_prompt(conn))

    success, query_results = execute_generated_sql(sql_query, conn)

    if success:
        visualization_code = generate_visualization_code(
            user_input,
            sql_query,
            query_results,
            engine.client
        )

    assistant_response = {
        "role": "assistant",
        "content": "Here's what I found:",
        "sql": sql_query,
        "data": query_results,
        "visualization": visualization_code,
    }

    st.session_state.messages.append(assistant_response)


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
