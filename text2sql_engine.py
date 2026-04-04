import sqlite3
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai


load_dotenv()

class Text2SQLEngine:
    def __init__(self, api_key=None, conn=None, db_path="hr_database.db"):
        self.api_key = api_key
        self.conn = conn
        
        # ✅ Add this — create the actual client
        if api_key:
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel("gemini-pro")
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
    """
    Generate matplotlib visualization code based on the query results.
    Returns a string of Python code that creates a fig variable.
    """
    if df is None or df.empty or len(df.columns) < 2:
        return None

    # Pick the first numeric column as the value axis
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(exclude="number").columns.tolist()

    if not numeric_cols:
        return None

    x_col = text_cols[0] if text_cols else df.columns[0]
    y_col = numeric_cols[0]

    code = f"""
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.bar(df['{x_col}'].astype(str), df['{y_col}'])
            ax.set_xlabel('{x_col}')
            ax.set_ylabel('{y_col}')
            ax.set_title('{question[:60]}')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
        """
    return code

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
    engine = Text2SQLEngine()
    sql = engine.generate_sql(question, schema_info)
    return sql
