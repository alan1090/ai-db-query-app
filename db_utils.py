"""
db_utils.py — Database Utility Functions for the Text-to-SQL Project
=====================================================================
Helper module for loading CSV data into SQLite and inspecting schemas.

This module is PROVIDED — you do not need to modify it.

Usage:
    from db_utils import load_csv_to_db, get_schema_info, execute_query
"""

import sqlite3
import pandas as pd
import os


def load_csv_to_db(csv_dir, db_path=':memory:'):
    """
    Load all CSV files from a directory into a SQLite database.

    Each CSV file becomes a table (filename without .csv = table name).
    Returns the database connection.
    """
    conn = sqlite3.connect(db_path)
    csv_files = sorted([f for f in os.listdir(csv_dir) if f.endswith('.csv')])

    if not csv_files:
        print(f"Warning: No CSV files found in '{csv_dir}'")
        return conn

    print(f"Loading {len(csv_files)} CSV files into database...")

    for csv_file in csv_files:
        table_name = csv_file.replace('.csv', '')
        file_path = os.path.join(csv_dir, csv_file)
        df = pd.read_csv(file_path)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"  ✓ {table_name}: {len(df)} rows, {len(df.columns)} columns")

    conn.execute("PRAGMA foreign_keys = ON")
    print(f"\nDatabase ready! {len(csv_files)} tables loaded.")
    return conn


def get_schema_info(conn):
    """
    Get a formatted string describing all tables and their columns.
    Useful for displaying schema to users and for AI prompt context.
    """
    tables = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", conn
    )

    schema_parts = ["DATABASE SCHEMA", "=" * 50]

    for table_name in tables['name']:
        cols = pd.read_sql_query(f"PRAGMA table_info({table_name})", conn)
        row_count = pd.read_sql_query(
            f"SELECT COUNT(*) as cnt FROM {table_name}", conn
        )['cnt'][0]

        schema_parts.append(f"\nTable: {table_name} ({row_count} rows)")
        schema_parts.append("-" * 40)

        for _, col in cols.iterrows():
            pk = " [PRIMARY KEY]" if col['pk'] else ""
            nullable = "" if col['notnull'] else " (nullable)"
            schema_parts.append(
                f"  {col['name']:25s} {col['type'] or 'TEXT':10s}{pk}{nullable}"
            )

    schema_parts.append("\n" + "=" * 50)
    schema_parts.append("SAMPLE DATA (first 3 rows per table)")
    schema_parts.append("=" * 50)

    for table_name in tables['name']:
        sample = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 3", conn)
        schema_parts.append(f"\n{table_name}:")
        schema_parts.append(sample.to_string(index=False))

    return "\n".join(schema_parts)


def get_table_info(table_name, conn):
    """Get detailed information about a specific table."""
    cols = pd.read_sql_query(f"PRAGMA table_info({table_name})", conn)
    row_count = pd.read_sql_query(
        f"SELECT COUNT(*) as cnt FROM {table_name}", conn
    )['cnt'][0]

    print(f"Table: {table_name} ({row_count} rows)")
    print("-" * 40)

    result = cols[['name', 'type', 'notnull', 'pk']].copy()
    result.columns = ['Column', 'Type', 'Not Null', 'Primary Key']
    result['Not Null'] = result['Not Null'].map({1: 'Yes', 0: 'No'})
    result['Primary Key'] = result['Primary Key'].map({1: 'Yes', 0: 'No'})
    return result


def execute_query(sql, conn, params=None):
    """
    Execute a SQL query and return results as a DataFrame.
    A safe wrapper around pd.read_sql_query with error handling.
    """
    try:
        if params:
            return pd.read_sql_query(sql, conn, params=params)
        return pd.read_sql_query(sql, conn)
    except Exception as e:
        print(f"Query Error: {e}")
        print(f"SQL: {sql}")
        return pd.DataFrame()


def list_tables(conn):
    """List all tables in the database with row counts."""
    tables = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", conn
    )

    results = []
    for table_name in tables['name']:
        count = pd.read_sql_query(
            f"SELECT COUNT(*) as rows FROM {table_name}", conn
        )['rows'][0]
        results.append({'table': table_name, 'rows': count})

    return pd.DataFrame(results)


def get_foreign_keys(conn):
    """
    Discover and display all foreign key relationships in the database.
    Useful for understanding how tables connect.
    """
    tables = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", conn
    )

    relationships = []
    for table_name in tables['name']:
        fks = pd.read_sql_query(f"PRAGMA foreign_key_list({table_name})", conn)
        if not fks.empty:
            for _, fk in fks.iterrows():
                relationships.append({
                    'from_table': table_name,
                    'from_column': fk['from'],
                    'to_table': fk['table'],
                    'to_column': fk['to']
                })

    if relationships:
        return pd.DataFrame(relationships)
    else:
        print("No formal foreign keys defined (relationships exist by naming convention).")
        # Show implied relationships
        implied = [
            ("employees", "dept_id", "departments", "dept_id"),
            ("employees", "title_id", "job_titles", "title_id"),
            ("employees", "manager_id", "employees", "emp_id"),
            ("projects", "dept_id", "departments", "dept_id"),
            ("project_assignments", "project_id", "projects", "project_id"),
            ("project_assignments", "emp_id", "employees", "emp_id"),
            ("salary_history", "emp_id", "employees", "emp_id"),
            ("performance_reviews", "emp_id", "employees", "emp_id"),
            ("training_records", "emp_id", "employees", "emp_id"),
        ]
        return pd.DataFrame(implied, columns=['from_table', 'from_column', 'to_table', 'to_column'])
