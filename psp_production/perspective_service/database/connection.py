"""
Database connection management.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator

import pyodbc


class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass


@dataclass
class DatabaseConfig:
    """Database configuration."""
    server: str
    database: str
    driver: str = "ODBC Driver 17 for SQL Server"


@contextmanager
def get_connection(config: DatabaseConfig) -> Generator[pyodbc.Connection, None, None]:
    """
    Context manager for database connections.

    Args:
        config: Database configuration

    Yields:
        pyodbc.Connection

    Raises:
        DatabaseConnectionError: If connection fails
    """
    conn_str = (
        f"DRIVER={{{config.driver}}};"
        f"SERVER={config.server};"
        f"DATABASE={config.database};"
        f"Trusted_Connection=yes;"
    )

    try:
        conn = pyodbc.connect(conn_str)
    except pyodbc.Error as e:
        raise DatabaseConnectionError(f"Failed to connect to database: {e}")

    try:
        yield conn
    finally:
        conn.close()
