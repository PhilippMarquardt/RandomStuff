"""Reference data loader - loads INSTRUMENT, INSTRUMENT_CATEGORIZATION from DB."""
import logging
from typing import List, Dict, Optional

import polars as pl

from ..config import DatabaseConfig
from .connection import get_connection

logger = logging.getLogger(__name__)


class ReferenceLoader:
    """Loads reference tables from database."""

    def __init__(self, config: DatabaseConfig):
        """
        Initialize the loader with database configuration.

        Args:
            config: Database connection configuration.
        """
        self.config = config

    def load_reference_table(
        self,
        instrument_ids: List[int],
        table_name: str,
        columns: List[str],
        ed: Optional[str] = None,
        system_version_timestamp: Optional[str] = None
    ) -> pl.DataFrame:
        """
        Load reference data for given instrument IDs.

        Args:
            instrument_ids: List of instrument IDs to load data for
            table_name: Name of the table (INSTRUMENT, INSTRUMENT_CATEGORIZATION, etc.)
            columns: Columns to select
            ed: Effective date filter (filters on ed column). If None, takes latest.
            system_version_timestamp: If provided, uses FOR SYSTEM_TIME AS OF for temporal query

        Returns:
            DataFrame with instrument_id and requested columns
        """
        if not instrument_ids:
            return pl.DataFrame(schema={'instrument_id': pl.Int64})

        # Ensure instrument_id is in columns
        all_columns = ['instrument_id'] + [c for c in columns if c != 'instrument_id']

        # Build query based on table
        if table_name == 'INSTRUMENT':
            return self._load_instrument(instrument_ids, all_columns, system_version_timestamp)
        elif table_name == 'INSTRUMENT_CATEGORIZATION':
            return self._load_instrument_categorization(
                instrument_ids, all_columns, ed, system_version_timestamp
            )
        else:
            logger.warning(f"Unknown table: {table_name}")
            return pl.DataFrame(schema={'instrument_id': pl.Int64})

    def _load_instrument(
        self,
        instrument_ids: List[int],
        columns: List[str],
        system_version_timestamp: Optional[str] = None
    ) -> pl.DataFrame:
        """Load data from INSTRUMENT table."""
        ids_str = ','.join(str(id) for id in instrument_ids)
        cols_str = ', '.join(columns)

        # Build temporal clause if system_version_timestamp provided
        temporal_clause = ""
        if system_version_timestamp:
            temporal_clause = f"FOR SYSTEM_TIME AS OF '{system_version_timestamp}'"

        query = f"""
            SELECT {cols_str}
            FROM [dbo].[INSTRUMENT] {temporal_clause}
            WHERE instrument_id IN ({ids_str})
        """

        return self._execute_query(query)

    def _load_instrument_categorization(
        self,
        instrument_ids: List[int],
        columns: List[str],
        ed: Optional[str],
        system_version_timestamp: Optional[str] = None
    ) -> pl.DataFrame:
        """Load data from INSTRUMENT_CATEGORIZATION table."""
        ids_str = ','.join(str(id) for id in instrument_ids)
        cols_str = ', '.join(columns)

        # Build temporal clause if system_version_timestamp provided
        temporal_clause = ""
        if system_version_timestamp:
            temporal_clause = f"FOR SYSTEM_TIME AS OF '{system_version_timestamp}'"

        # Build ed filter - if no ed provided, take latest per instrument
        if ed:
            ed_filter = f"AND ed <= '{ed}'"
        else:
            # No ed filter means take all records (caller handles latest selection if needed)
            ed_filter = ""

        query = f"""
            SELECT {cols_str}
            FROM [dbo].[INSTRUMENT_CATEGORIZATION] {temporal_clause}
            WHERE instrument_id IN ({ids_str})
            {ed_filter}
        """

        return self._execute_query(query)

    def _execute_query(self, query: str) -> pl.DataFrame:
        """Execute a query and return results as DataFrame."""
        with get_connection(self.config) as conn:
            cursor = conn.cursor()
            cursor.execute(query)

            # Get column names from cursor description
            columns = [desc[0] for desc in cursor.description]

            # Fetch all rows
            rows = cursor.fetchall()

            if not rows:
                return pl.DataFrame(schema={col: pl.Int64 for col in columns})

            # Convert to DataFrame
            data = {col: [row[i] for row in rows] for i, col in enumerate(columns)}
            return pl.DataFrame(data)

    def load_multiple_tables(
        self,
        instrument_ids: List[int],
        required_tables: Dict[str, List[str]],
        ed: Optional[str] = None,
        system_version_timestamp: Optional[str] = None
    ) -> Dict[str, pl.DataFrame]:
        """
        Load multiple reference tables at once.

        Args:
            instrument_ids: List of instrument IDs
            required_tables: Dict of table_name -> columns to load
            ed: Effective date filter (filters on ed column). If None, takes latest.
            system_version_timestamp: If provided, uses FOR SYSTEM_TIME AS OF for temporal query

        Returns:
            Dict of table_name -> DataFrame
        """
        results = {}

        for table_name, columns in required_tables.items():
            logger.info(f"Loading {table_name} with columns: {columns}")
            results[table_name] = self.load_reference_table(
                instrument_ids,
                table_name,
                columns,
                ed,
                system_version_timestamp
            )

        return results
