"""
text2sql_engine.py — Text-to-SQL Engine (Student Version with TODOs)
=====================================================================
Converts natural language questions into SQL queries using Google Gemini,
then executes them safely against a SQLite database.

Students will complete the TODO sections to build the full pipeline.

Usage:
    from text2sql_engine import Text2SQLEngine
    engine = Text2SQLEngine(conn, api_key='YOUR_KEY')
    result = engine.ask('What is the average salary by department?')
"""

# text2sql_engine.py - Correggi gli import
import os
from dotenv import load_dotenv
import sqlite3
from google import genai
import pandas as pd
import re
from db_utils import get_foreign_keys

# Carica variabili d'ambiente se necessario
load_dotenv()


# ============================================================
# PART A: Schema Context Builder
# ============================================================

def get_schema_for_prompt(conn):
    tables = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", conn
    )

    cursor = conn.cursor()
    schema_parts = []

    for table_name in tables['name']:
        # --- Get schema ---
        cursor.execute(f'PRAGMA table_info("{table_name}")')
        columns = cursor.fetchall()

        # TODO 1: CREATE TABLE statement
        cols_formatted = []
        for col in columns:
            col_name = col[1]
            col_type = col[2] or "TEXT"
            cols_formatted.append(f"  {col_name} {col_type}")

        create_stmt = f"CREATE TABLE {table_name} (\n"
        create_stmt += ",\n".join(cols_formatted)
        create_stmt += "\n);"

        schema_parts.append(create_stmt)

        # TODO 2: Sample data
        cursor.execute(f'SELECT * FROM "{table_name}" LIMIT 3')
        rows = cursor.fetchall()

        sample_str = f"-- Sample data for {table_name}:"
        if rows:
            for row in rows:
                sample_str += f"\n-- {row}"
        else:
            sample_str += "\n-- (no sample data)"

        schema_parts.append(sample_str)

    # TODO 3: Relationships
    fk_df = get_foreign_keys(conn)

    rel_str = "\n-- Table Relationships:"
    for _, row in fk_df.iterrows():
        rel_str += (
            f"\n-- {row['from_table']}.{row['from_column']} "
            f"-> {row['to_table']}.{row['to_column']}"
        )

    schema_parts.append(rel_str)

    return "\n\n".join(schema_parts)

# ============================================================
# PART B: SQL Safety Validator
# ============================================================

def validate_sql(sql):
    """
    Validate that AI-generated SQL is safe to execute.

    This is a CRITICAL security function. AI models can sometimes generate
    dangerous queries (DROP TABLE, DELETE, etc.) that could destroy data.

    Parameters
    ----------
    sql : str
        SQL query to validate.

    Returns
    -------
    tuple (bool, str)
        (is_safe, message) — True if safe, False with reason if not.

    Rules
    -----
    1. Query must start with SELECT or WITH (for CTEs)
    2. Must not contain: DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE
    3. Must not contain multiple statements (no semicolons mid-query)
    """
    sql_clean = sql.strip()

    if not sql_clean:
        return False, "Empty query."

    sql_upper = sql_clean.upper()

    # TODO 4: Check that the query starts with SELECT or WITH
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False, "Query must start with SELECT or WITH."

    # TODO 5: Check for dangerous keywords using regex word boundaries
    dangerous_keywords = r'\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE)\b'
    if re.search(dangerous_keywords, sql_upper):
        return False, "Query contains dangerous keywords."

    # TODO 6: Check for multiple statements (stacked query injection)
    if ';' in sql_upper[:-1]:
        return False, "Query contains multiple statements."

    return True, "Query is safe."


# ============================================================
# PART C: Response Parser
# ============================================================

def extract_sql_from_response(response_text):
    """
    Extract a SQL query from an AI model's response.

    The AI might return SQL in several formats:
    - Wrapped in ```sql ... ``` code blocks
    - With explanations before/after
    - As plain text

    Parameters
    ----------
    response_text : str
        Raw text response from the AI model.

    Returns
    -------
    str
        Extracted SQL query, cleaned up.
    """
    # TODO 7: Try to extract SQL from markdown code blocks first
    # Look for ```sql ... ``` or ``` ... ``` patterns
    code_block = re.search(
        r'```(?:sql|sqlite|sqlite3|postgresql|mysql)?\s*\n?(.*?)\n?```',
        response_text,
        re.DOTALL | re.IGNORECASE
    )
    if code_block:
        return code_block.group(1).strip()

    # TODO 8: Try to find a SELECT or WITH statement in the text
    # Handle both with and without a trailing semicolon
    sql_match = re.search(r'(SELECT|WITH)\b.*?;', response_text, re.IGNORECASE | re.DOTALL)
    if sql_match:
        return sql_match.group(0).strip()

    # Last resort: return the full text stripped
    return response_text.strip()


# ============================================================
# PART D: SQL Generator (Core AI Integration)
# ============================================================

def generate_sql(question, client, schema_info, model='gemini-3-flash-preview'):
    """
    Use Gemini to convert a natural language question into a SQL query.

    Parameters
    ----------
    question : str
        Natural language question about the data.
    client : genai.Client
        Configured Google Generative AI client.
    schema_info : str
        Database schema description (from get_schema_for_prompt).
    model : str
        Gemini model to use.

    Returns
    -------
    str
        Generated SQL query.
    """

    prompt = f"""You are a helpful assistant that converts natural language questions into SQL queries.

        Database Schema:
        {schema_info}

        Rules:
        - Only generate SELECT or WITH statements
        - Use SQLite syntax
        - Use column aliases where appropriate
        - Round numeric values to 2 decimal places
        - Just generate the SQL query and nothing else
        - Do not include any explanations or additional text

        Question: {question}
        SQL Query:
    """

    # TODO 10: Call the Gemini API and extract the SQL from the response
    # Handle API errors gracefully with try/except
    try:
        resp = client.models.generate_content(model=model, contents=prompt)
        generated_sql = resp.text.strip()
        return extract_sql_from_response(generated_sql)
    except Exception as e:
        return f"-- Error generating SQL: {str(e)}"


# ============================================================
# PART E: Safe Query Executor
# ============================================================

def execute_generated_sql(sql, conn):
    """
    Validate and execute AI-generated SQL.

    Parameters
    ----------
    sql : str
        SQL query to execute.
    conn : sqlite3.Connection

    Returns
    -------
    tuple (bool, pd.DataFrame or str)
        (success, result_dataframe) or (False, error_message)
    """
    # TODO 11: First validate the SQL using validate_sql()
    # If not valid, return a tuple indicating failure with the reason
    is_safe, message = validate_sql(sql)
    if not is_safe:
        return False, message

    # Execute safely
    try:
        df = pd.read_sql_query(sql, conn)
        return True, df
    except Exception as e:
        return False, f"SQL execution error: {e}"


# ============================================================
# PART F: Visualization Code Generator
# ============================================================

def generate_visualization_code(question, sql, df, client, model='gemini-3-flash-preview'):
    """
    Generate robust visualization code with fallback + validation.
    """

    import re

    # --- Clean structured inputs ---
    columns = list(df.columns)
    preview = df.head().to_string(index=False)

    prompt = f"""You are a Python data visualization expert.

Create matplotlib/seaborn code to visualize the data.

Question: {question}

SQL:
{sql}

Columns:
{columns}

Data Preview:
{preview}

Rules:
- Use seaborn or matplotlib
- ALWAYS use: data=df when using seaborn
- Use ONLY column names from the Columns list
- Choose an appropriate chart (bar for categorical)
- Include title and axis labels
- Use plt.tight_layout()
- Store figure in variable `fig`
- Do NOT call plt.show()
- Return ONLY Python code
"""

    # --- Try generating code ---
    generated_code = ""

    try:
        resp = client.models.generate_content(model=model, contents=prompt)
        generated_code = (resp.text or "").strip()
    except Exception:
        generated_code = ""

    # --- Extract python code ---
    code = extract_python_from_response(generated_code)

    # --- VALIDATION + PATCHING ---
    if code:
        # Ensure seaborn uses data=df
        def fix_barplot(match):
            args = match.group(1)
            if "data=" not in args:
                return f"sns.barplot(data=df, {args})"
            return match.group(0)

        code = re.sub(r"sns\.barplot\((.*?)\)", fix_barplot, code)

        # Optional: fix lineplot too
        def fix_lineplot(match):
            args = match.group(1)
            if "data=" not in args:
                return f"sns.lineplot(data=df, {args})"
            return match.group(0)

        code = re.sub(r"sns\.lineplot\((.*?)\)", fix_lineplot, code)

        return code

    # --- 🔥 FALLBACK (guaranteed to work) ---
    return f"""
import matplotlib.pyplot as plt

fig, ax = plt.subplots()

ax.bar(df.iloc[:, 0], df.iloc[:, 1])

ax.set_title("Auto-generated chart")
ax.set_xlabel("{columns[0]}")
ax.set_ylabel("{columns[1] if len(columns) > 1 else 'Value'}")

plt.tight_layout()
"""
def extract_python_from_response(response_text):
    """Extract Python code from an AI response (similar to SQL extraction)."""
    # TODO 15: Extract Python code from markdown code blocks
    code_block = re.search(r'```(?:python)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
    if code_block:
        return code_block.group(1).strip()

    return response_text.strip()


# ============================================================
# PART G: The Complete Text2SQL Engine (ties everything together)
# ============================================================

class Text2SQLEngine:
    """
    Complete Text-to-SQL pipeline: Question → SQL → Results → Visualization.

    Parameters
    ----------
    conn : sqlite3.Connection
        Active database connection.
    api_key : str
        Google Gemini API key.
    model : str
        Gemini model name (default: 'gemini-3-flash-preview').
    """

    def __init__(self, conn, api_key, model='gemini-3-flash-preview'):
        self.conn = conn
        self.model = model
        self.history = []
        

        # TODO 16: Build the schema context and initialize the Gemini client
        # Store the schema, create the genai client, and test the connection.
        self.schema_info = get_schema_for_prompt(conn)
        self.client = genai.Client(api_key=api_key)

    def ask(self, question, show_sql=True, interpret=True, visualize=False):
        """
        Ask a natural language question and get SQL + results + interpretation.

        Parameters
        ----------
        question : str
            Natural language question about the data.
        show_sql : bool
            Whether to print the generated SQL.
        interpret : bool
            Whether to generate an AI interpretation.
        visualize : bool
            Whether to generate visualization code.

        Returns
        -------
        dict with keys: question, sql, data, interpretation, viz_code, success
        """
        result = {
            'question': question,
            'sql': None,
            'data': None,
            'interpretation': None,
            'viz_code': None,
            'success': False
        }

        if not hasattr(self, 'client') or self.client is None:
            print("Error: Gemini API not configured.")
            return result

        if question is not None:# Generate SQL
            result['sql'] = generate_sql(question, self.client, self.schema_info, self.model)

            if show_sql:
                print(f"SQL Generated: {result['sql']}")

            # ✅ EXECUTE SQL (THIS WAS MISSING / WRONG)
            success, data = execute_generated_sql(result['sql'], self.conn)

            if not success:
                print("SQL ERROR:", data)  # 🔥 ADD THIS

                result['data'] = data  # error message
                result['success'] = False
                return result

            # ✅ NOW THIS IS A DATAFRAME
            result['data'] = data
            result['success'] = True

            if interpret and isinstance(result['data'], pd.DataFrame) and not result['data'].empty:
                result["interpretation"] = self._interpret_results(question, result['data'])

            if isinstance(result['data'], pd.DataFrame):
                print("empty:", result['data'].empty)
            print("--------------\n")
            if visualize and isinstance(result['data'], pd.DataFrame) and not result['data'].empty:
                viz_code = generate_visualization_code(
                    question, result['sql'], result['data'], self.client, self.model
                )

            result["viz_code"] = viz_code

            try:
                exec(viz_code, {"df": result['data']})
                import matplotlib.pyplot as plt
                plt.show()
            except Exception as e:
                print(f"Viz error: {e}")

            self.history.append(result)
            return result

    def _interpret_results(self, question, data):
        """Generate a business-friendly interpretation of query results."""
        data_str = data.to_string(index=False) if not isinstance(data, str) else data
        prompt = f"""You are a data analyst at a technology company. A user asked: "{question}"

            Here are the query results:
            {data_str}

            Provide a brief (3-4 sentence) business interpretation. Include:
            - One key insight from the data
            - One actionable recommendation
            - Reference specific numbers from the results."""

        try:
            response = self.client.models.generate_content(
                model=self.model, contents=prompt
            )
            return response.text
        except Exception as e:
            return f"(Could not generate interpretation: {e})"

    def get_sql_only(self, question):
        """Generate SQL without executing it. Useful for learning."""
        if not hasattr(self, 'client') or self.client is None:
            return "-- Error: Gemini API not configured"
        return generate_sql(question, self.client, self.schema_info, self.model)

    def execute_custom_sql(self, sql):
        """Execute a manually written SQL query safely."""
        success, result = execute_generated_sql(sql, self.conn)
        if success:
            return result
        else:
            print(result)
            return pd.DataFrame()

    def show_schema(self):
        """Print the database schema."""
        print(self.schema_info)

    def show_history(self):
        """Show all questions asked in this session."""
        if not self.history:
            print("No questions asked yet.")
            return

        print(f"\nQuestion History ({len(self.history)} questions)")
        print("=" * 60)
        for i, item in enumerate(self.history, 1):
            status = "✓" if item['success'] else "✗"
            print(f"{i}. [{status}] {item['question']}")
            if item['sql']:
                sql_preview = item['sql'].replace('\n', ' ')[:80]
                print(f"   SQL: {sql_preview}...")
