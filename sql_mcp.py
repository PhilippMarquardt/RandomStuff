# server.py
import os
import re
import pyodbc
from fastmcp import FastMCP

# Configuration via environment variables
SQL_SERVER   = os.getenv("SQL_SERVER", "localhost")
SQL_DATABASE = os.getenv("SQL_DATABASE", "your_database")
SQL_USERNAME = os.getenv("SQL_USERNAME", "your_username")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "your_password")
SQL_DRIVER   = os.getenv("SQL_DRIVER", "{ODBC Driver 17 for SQL Server}")

# ODBC connection string
CONN_STR = (
    f"DRIVER={SQL_DRIVER};"
    f"SERVER={SQL_SERVER};"
    f"DATABASE={SQL_DATABASE};"
    f"UID={SQL_USERNAME};"
    f"PWD={SQL_PASSWORD}"
)

# Regex for validating SELECT queries
SELECT_REGEX = re.compile(r"^\s*select\b[\s\S]+?\bfrom\b[\s\S]+$", re.IGNORECASE)

# Disallowed keywords in queries
DISALLOWED_KEYWORDS = [
    'insert', 'update', 'delete', 'create', 'drop', 'alter',
    'truncate', 'merge', 'declare', 'exec', 'execute', 'sp_',
]

# Disallowed patterns
DISALLOWED_PATTERNS = [
    '--',  # SQL single-line comments
    '/\*',  # SQL block comments
    ';',  # statement terminator
]

def get_conn():
    """Get a new database connection"""
    return pyodbc.connect(CONN_STR)

# Create the MCP server instance
mcp = FastMCP("SQLServerMCP 🚀")

@mcp.tool()
def list_schemas() -> list[str]:
    """List all schemas in the database"""
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sys.schemas;")
        return [row[0] for row in cursor.fetchall()]

@mcp.tool()
def list_tables(schema: str = "dbo") -> list[str]:
    """List all tables in a given schema"""
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = ?;",
            schema
        )
        return [row[0] for row in cursor.fetchall()]

@mcp.tool()
def list_stored_procedures(schema: str = "dbo") -> list[str]:
    """List stored procedures in a given schema"""
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES"
            " WHERE ROUTINE_TYPE='PROCEDURE' AND ROUTINE_SCHEMA=?;",
            schema
        )
        return [row[0] for row in cursor.fetchall()]

@mcp.tool()
def list_user_functions(schema: str = "dbo") -> list[str]:
    """List user-defined functions in a given schema"""
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES"
            " WHERE ROUTINE_TYPE='FUNCTION' AND ROUTINE_SCHEMA=?;",
            schema
        )
        return [row[0] for row in cursor.fetchall()]

@mcp.tool()
def get_procedure_definition(proc_name: str) -> str:
    """Get the definition of a stored procedure"""
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT OBJECT_DEFINITION(OBJECT_ID(?));",
            proc_name
        )
        result = cursor.fetchone()
        return result[0] if result else ""

@mcp.tool()
def get_function_definition(func_name: str) -> str:
    """Get the definition of a function"""
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT OBJECT_DEFINITION(OBJECT_ID(?));",
            func_name
        )
        result = cursor.fetchone()
        return result[0] if result else ""

@mcp.tool()
def execute_query(query: str, max_rows: int = 100) -> list[dict]:
    """
    Execute a safe, single-statement SELECT query and return results as a list of dicts.

    This tool will:
      - Accept exactly one SQL SELECT statement containing a FROM clause.
      - Reject any query with non-SELECT keywords (e.g., INSERT/UPDATE/DELETE),
        comments ("--", "/*"), semicolons, or multiple statements.
      - Return up to `max_rows` rows, where each row is a dictionary
        mapping column names to their values.

    Raises:
      ValueError: If the query is missing a FROM clause, contains disallowed
                  patterns/keywords, or includes multiple statements.
    """
    # Basic cleanup
    cleaned = query.strip()

    # Disallow dangerous patterns
    for pattern in DISALLOWED_PATTERNS:
        if pattern in cleaned.lower():
            raise ValueError(f"Disallowed pattern detected: {pattern}")

    # Disallow dangerous keywords
    low = cleaned.lower()
    for kw in DISALLOWED_KEYWORDS:
        if re.search(rf"\b{kw}\b", low):
            raise ValueError(f"Disallowed keyword detected: {kw}")

    # Ensure it's a single SELECT statement
    if not SELECT_REGEX.match(cleaned):
        raise ValueError("Only single SELECT queries with a FROM clause are allowed.")

    # Execute
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(cleaned)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchmany(max_rows)
        return [dict(zip(columns, row)) for row in rows]

if __name__ == "__main__":
    # Run as HTTP server on port 8000 at /mcp
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        path="/mcp"
    )
