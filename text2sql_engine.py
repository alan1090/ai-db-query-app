import os
import sqlite3
import pandas as pd
import re
from dotenv import load_dotenv

load_dotenv()

class Text2SQLEngine:
    def __init__(self, db_path="hr_database.db"):
        self.db_path = db_path
        self.conn = None
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

def get_schema_for_prompt():
    engine = Text2SQLEngine()
    schema = engine.get_schema()
    engine.close()
    return schema

def generate_sql(question, schema_info):
    engine = Text2SQLEngine()
    sql = engine.generate_sql(question, schema_info)
    engine.close()
    return sql
