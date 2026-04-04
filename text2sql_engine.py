import sqlite3
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
import textwrap

load_dotenv()

class Text2SQLEngine:
    def __init__(self, api_key=None, conn=None, db_path="hr_database.db"):
        self.api_key = api_key
        self.conn = conn
        
        # ✅ Add this — create the actual client
        if api_key:
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.client = None

        if self.conn is None:
            self.db_path = db_path
            self.connect()
    
    def connect(self):
        """Create database connection"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False
    
    def get_schema(self):
        """Get database schema"""
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()
        
        schema_parts = []
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            schema_parts.append(f"\n-- Table: {table_name}")
            for col in columns:
                schema_parts.append(f"  {col[1]} ({col[2]})")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            schema_parts.append(f"  -- Total rows: {count}\n")
        
        return "\n".join(schema_parts)
    
    def generate_sql(self, question, schema_info):
        """Simple rule-based SQL generation (no API needed)"""
        question_lower = question.lower()
        
        # Basic keyword matching
        if "average salary" in question_lower or "avg salary" in question_lower:
            if "department" in question_lower:
                return """
                    SELECT department, AVG(salary) as avg_salary 
                    FROM employees 
                    GROUP BY department 
                    ORDER BY avg_salary DESC
                """
        
        if "min salary" in question_lower or "minimum salary" in question_lower:
            return """
                SELECT department, MIN(salary) as min_salary 
                FROM employees 
                GROUP BY department
            """
        
        if "max salary" in question_lower or "maximum salary" in question_lower:
            return """
                SELECT department, MAX(salary) as max_salary 
                FROM employees 
                GROUP BY department
            """
        
        if "employees" in question_lower and "count" in question_lower:
            return """
                SELECT department, COUNT(*) as employee_count 
                FROM employees 
                GROUP BY department
            """
        
        # Default query
        return "SELECT * FROM employees LIMIT 10"
    
    def execute_query(self, sql):
        """Execute SQL and return results"""
        if not self.conn:
            self.connect()
        
        try:
            return pd.read_sql(sql, self.conn)
        except Exception as e:
            return pd.DataFrame({"Error": [str(e)]})
    
    def close(self):
        if self.conn:
            self.conn.close()
def execute_generated_sql(sql, conn):
    """Execute SQL query and return (success, DataFrame)"""
    try:
        df = pd.read_sql_query(sql, conn)
        return True, df
    except Exception as e:
        return False, pd.DataFrame({"Error": [str(e)]})


def generate_visualization_code(question, sql, df, client=None):
    """Use Gemini to generate appropriate matplotlib visualization code"""

    if df is None or df.empty or len(df.columns) < 2 or client is None:
        return None

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        return None

    prompt = f"""You are a Python data visualization expert using matplotlib.

Given this dataframe `df` with columns: {list(df.columns)}
Sample data:
{df.head(3).to_string()}

The user asked: "{question}"
The SQL used was: {sql}

Write Python code to create the most appropriate matplotlib visualization.
RULES:
- Use ONLY matplotlib (already imported as plt)
- The dataframe is already available as `df`
- Store the figure in a variable called `fig`
- No explanations, no markdown, no code fences
- No import statements needed
- Keep it simple and readable

CODE:"""

    try:
        response = client.generate_content(prompt)
        code = response.text.strip()
        code = code.replace("```python", "").replace("```", "").strip()
        return code
    except Exception as e:
        return None
    
def get_schema_for_prompt(conn):
    """Get schema string from an existing connection"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = cursor.fetchall()

    schema_parts = []
    for (table_name,) in tables:
        cursor.execute(f'PRAGMA table_info("{table_name}")')
        columns = cursor.fetchall()
        schema_parts.append(f"\n-- Table: {table_name}")
        for col in columns:
            schema_parts.append(f"  {col[1]} ({col[2]})")
        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        count = cursor.fetchone()[0]
        schema_parts.append(f"  -- Total rows: {count}\n")

    return "\n".join(schema_parts)

def generate_sql(question, client, schema_info):
    """Use Gemini to generate SQL from natural language"""
    
    if client is None:
        return "SELECT * FROM employees LIMIT 10"

    prompt = f"""You are an expert SQL assistant. Given the following database schema, write a valid SQLite SQL query to answer the user's question.

DATABASE SCHEMA:
{schema_info}

RULES:
- Return ONLY the raw SQL query, no explanations, no markdown, no code fences
- Use only tables and columns that exist in the schema above
- Use proper SQLite syntax
- Always use double quotes around table and column names that might conflict with reserved words
- Limit results to 50 rows unless the question asks for all data

USER QUESTION: {question}

SQL QUERY:"""

    try:
        response = client.generate_content(prompt)
        sql = response.text.strip()
        
        # Strip markdown code fences if Gemini adds them anyway
        sql = sql.replace("```sql", "").replace("```", "").strip()
        
        return sql
    except Exception as e:
        return f"-- Error generating SQL: {e}\nSELECT * FROM employees LIMIT 10"
