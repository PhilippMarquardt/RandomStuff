"""Database connection management."""
import logging
from contextlib import contextmanager
from typing import Generator

import pyodbc

from ..config import DatabaseConfig

logger = logging.getLogger(__name__)


@contextmanager
def get_connection(config: DatabaseConfig) -> Generator[pyodbc.Connection, None, None]:
    """
    Context manager for database connections.

    Opens a connection, yields it for use, and ensures it's closed afterward.

    Args:
        config: Database configuration with connection settings.

    Yields:
        Active pyodbc connection.

    Raises:
        pyodbc.Error: If connection fails.
    """
    conn_str = (
        f"DRIVER={{{config.driver}}};"
        f"SERVER={config.server};"
        f"DATABASE={config.database};"
        f"Trusted_Connection={'yes' if config.trusted_connection else 'no'};"
    )

    conn = None
    try:
        conn = pyodbc.connect(conn_str)
        yield conn
    except pyodbc.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise
    finally:
        if conn:
            conn.close()
