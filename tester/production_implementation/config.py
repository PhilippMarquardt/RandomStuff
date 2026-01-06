"""Configuration management for the Perspective Service."""
from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    server: str
    database: str
    driver: str = "ODBC Driver 17 for SQL Server"
    trusted_connection: bool = True


def load_config(env_path: Path = None) -> DatabaseConfig:
    """
    Load database configuration from environment variables.

    Args:
        env_path: Optional path to .env file. If not provided, searches in standard locations.

    Returns:
        DatabaseConfig with connection settings.
    """
    if env_path:
        load_dotenv(env_path)
    else:
        load_dotenv()

    return DatabaseConfig(
        server=os.getenv("DB_SERVER", ""),
        database=os.getenv("DB_DATABASE", ""),
        driver=os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server"),
        trusted_connection=os.getenv("DB_TRUSTED_CONNECTION", "true").lower() == "true"
    )
