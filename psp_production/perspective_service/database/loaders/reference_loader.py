"""
Reference data loader - loads INSTRUMENT, INSTRUMENT_CATEGORIZATION, and PARENT_INSTRUMENT data.
Uses Polars read_database_uri with connectorx for efficient data loading.
"""

from typing import Dict, List, Optional

import polars as pl


class ReferenceLoadError(Exception):
    """Raised when reference data loading fails."""
    pass


class ReferenceLoader:
    """Loads reference data from database using Polars/connectorx."""

    def load(self,
             connection_uri: str,
             instrument_ids: List[int],
             parent_instrument_ids: List[int],
             tables_needed: Dict[str, List[str]],
             system_version_timestamp: Optional[str],
             ed: Optional[str]) -> Dict[str, pl.DataFrame]:
        """
        Load reference data for the specified tables.

        Args:
            connection_uri: Database connection URI for connectorx (mssql://...)
            instrument_ids: List of instrument IDs to load
            parent_instrument_ids: List of parent instrument IDs (for PARENT_INSTRUMENT)
            tables_needed: Dict of {table_name: [column_names]}
            system_version_timestamp: Timestamp for sysversion queries
            ed: Effective date for INSTRUMENT_CATEGORIZATION

        Returns:
            Dict of {table_name: DataFrame}
        """
        results = {}

        for table_name, columns in tables_needed.items():
            if table_name == 'position_data':
                # Skip - this comes from input JSON
                continue

            if table_name == 'PARENT_INSTRUMENT':
                df = self._load_parent_instrument(connection_uri, parent_instrument_ids, columns)
                results[table_name] = df

            elif table_name == 'INSTRUMENT':
                df = self._load_instrument(connection_uri, instrument_ids, columns)
                results[table_name] = df

            elif table_name == 'INSTRUMENT_CATEGORIZATION':
                df = self._load_instrument_categorization(
                    connection_uri, instrument_ids, columns, system_version_timestamp, ed
                )
                results[table_name] = df

        return results

    def _load_instrument(self,
                         connection_uri: str,
                         instrument_ids: List[int],
                         columns: List[str]) -> pl.DataFrame:
        """Load data from INSTRUMENT table using Polars/connectorx."""
        if not instrument_ids:
            return pl.DataFrame({"instrument_id": []})

        columns_str = ", ".join([c for c in columns if c != 'instrument_id'])
        ids_str = ",".join(map(str, instrument_ids))

        query = f"""
            SELECT instrument_id, {columns_str}
            FROM INSTRUMENT WITH (NOLOCK)
            WHERE instrument_id IN ({ids_str})
        """

        try:
            return pl.read_database_uri(query=query, uri=connection_uri)
        except Exception as e:
            raise ReferenceLoadError(f"Failed to load INSTRUMENT data: {e}")

    def _load_parent_instrument(self,
                                connection_uri: str,
                                parent_instrument_ids: List[int],
                                columns: List[str]) -> pl.DataFrame:
        """
        Load PARENT_INSTRUMENT data using Polars/connectorx.

        Queries the INSTRUMENT table using parent_instrument_ids,
        then prefixes all columns with 'parent_'.
        """
        prefixed = ['parent_instrument_id'] + [f'parent_{c}' for c in columns if c != 'instrument_id']

        if not parent_instrument_ids:
            return pl.DataFrame({c: [] for c in prefixed})

        # Filter out null sentinel values
        valid_ids = [i for i in parent_instrument_ids if i is not None and i != -2147483648]
        if not valid_ids:
            return pl.DataFrame({c: [] for c in prefixed})

        columns_str = ", ".join([c for c in columns if c != 'instrument_id'])
        ids_str = ",".join(map(str, valid_ids))

        query = f"""
            SELECT instrument_id, {columns_str}
            FROM INSTRUMENT WITH (NOLOCK)
            WHERE instrument_id IN ({ids_str})
        """

        try:
            df = pl.read_database_uri(query=query, uri=connection_uri)

            if df.is_empty():
                return pl.DataFrame({c: [] for c in prefixed})

            # Rename columns with parent_ prefix
            rename_map = {'instrument_id': 'parent_instrument_id'}
            for c in columns:
                if c != 'instrument_id':
                    rename_map[c] = f'parent_{c}'

            return df.rename(rename_map)

        except Exception as e:
            raise ReferenceLoadError(f"Failed to load PARENT_INSTRUMENT data: {e}")

    def _load_instrument_categorization(self,
                                        connection_uri: str,
                                        instrument_ids: List[int],
                                        columns: List[str],
                                        system_version_timestamp: Optional[str],
                                        ed: Optional[str]) -> pl.DataFrame:
        """Load data from INSTRUMENT_CATEGORIZATION table using Polars/connectorx."""
        if not instrument_ids:
            return pl.DataFrame({"instrument_id": []})

        columns_str = ", ".join([c for c in columns if c != 'instrument_id'])
        ids_str = ",".join(map(str, instrument_ids))

        # Build query with sysversion if provided
        if system_version_timestamp:
            query = f"""
                SELECT instrument_id, {columns_str}
                FROM INSTRUMENT_CATEGORIZATION
                FOR SYSTEM_TIME AS OF '{system_version_timestamp}'
                WHERE instrument_id IN ({ids_str})
            """
            if ed:
                query = query.rstrip() + f" AND ED = '{ed}'"
        else:
            query = f"""
                SELECT instrument_id, {columns_str}
                FROM INSTRUMENT_CATEGORIZATION WITH (NOLOCK)
                WHERE instrument_id IN ({ids_str})
            """
            if ed:
                query = query.rstrip() + f" AND ED = '{ed}'"

        try:
            return pl.read_database_uri(query=query, uri=connection_uri)
        except Exception as e:
            raise ReferenceLoadError(f"Failed to load INSTRUMENT_CATEGORIZATION data: {e}")
