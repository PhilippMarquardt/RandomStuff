"""
Database Loader - Single class for all database operations.
Uses Polars read_database with arrow-odbc for efficient Arrow-native queries.
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import polars as pl


class DatabaseLoadError(Exception):
    """Raised when database loading fails."""
    pass


class DatabaseLoader:
    """
    Single class for all database operations.
    Uses pl.read_database() with ODBC connection string (arrow-odbc under the hood).
    """

    def __init__(self, connection_string: str):
        self._connection_string = connection_string

    def _execute_query(self, query: str) -> pl.DataFrame:
        """Execute query and return Polars DataFrame."""
        return pl.read_database(
            query,
            self._connection_string,
            execute_options={"max_text_size": 999999}
        )

    # ==================== PERSPECTIVES ====================

    def load_perspectives(self, system_version_timestamp: Optional[str] = None) -> Dict[int, Dict]:
        """Load perspectives from FN_GET_SUBSETTING_SERVICE_PERSPECTIVES."""
        try:
            query = f"SELECT [dbo].[FN_GET_SUBSETTING_SERVICE_PERSPECTIVES]({system_version_timestamp!r})"
            df = self._execute_query(query)

            if df.is_empty():
                raise DatabaseLoadError("No perspectives found in database")

            json_str = df.item(0, 0)
            json_data = json.loads(json_str)
            raw_perspectives = json_data.get('perspectives', [])

            # Group by perspective ID
            grouped = {}
            for p in raw_perspectives:
                pid = p.get('id')
                if pid not in grouped:
                    grouped[pid] = {
                        'id': pid,
                        'name': p.get('name'),
                        'is_active': p.get('is_active', True),
                        'is_supported': p.get('is_compatible_with_sub_setting_service', True),
                        'rules': []
                    }
                grouped[pid]['is_active'] &= p.get('is_active', True)
                grouped[pid]['is_supported'] &= bool(p.get('is_compatible_with_sub_setting_service', True))
                grouped[pid]['rules'].extend(p.get('rules', []))

            print(f"Loaded {len(grouped)} perspectives from database")
            return grouped

        except json.JSONDecodeError as e:
            raise DatabaseLoadError(f"Failed to parse perspective JSON: {e}")
        except Exception as e:
            raise DatabaseLoadError(f"Database error loading perspectives: {e}")

    # ==================== REFERENCE DATA ====================

    def load_reference_data(self,
                            instrument_ids: List[int],
                            parent_instrument_ids: List[int],
                            asset_allocation_ids: List[int],
                            tables_needed: Dict[str, List[str]],
                            system_version_timestamp: Optional[str],
                            ed: Optional[str]) -> Dict[str, pl.DataFrame]:
        """Load reference data for specified tables in PARALLEL."""
        # Build list of (table_name, query) tasks
        tasks = []
        for table_name, columns in tables_needed.items():
            if table_name == 'position_data':
                continue

            query = self._build_reference_query(
                table_name, columns, instrument_ids,
                parent_instrument_ids, asset_allocation_ids,
                system_version_timestamp, ed
            )
            if query:
                tasks.append((table_name, query))

        if not tasks:
            return {}

        # Execute ALL queries in parallel (each pl.read_database creates own connection)
        results = {}
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {
                executor.submit(self._execute_query, query): table_name
                for table_name, query in tasks
            }
            for future in as_completed(futures):
                table_name = futures[future]
                try:
                    results[table_name] = future.result()
                except Exception as e:
                    raise DatabaseLoadError(f"Failed to load {table_name}: {e}")

        # Post-process PARENT_INSTRUMENT
        if 'PARENT_INSTRUMENT' in results and not results['PARENT_INSTRUMENT'].is_empty():
            df = results['PARENT_INSTRUMENT']
            rename_map = {'instrument_id': 'parent_instrument_id'}
            for c in df.columns:
                if c != 'instrument_id':
                    rename_map[c] = f'parent_{c}'
            results['PARENT_INSTRUMENT'] = df.rename(rename_map)

        return results

    def _build_reference_query(self, table_name: str, columns: List[str],
                               instrument_ids: List[int],
                               parent_instrument_ids: List[int],
                               asset_allocation_ids: List[int],
                               system_version_timestamp: Optional[str],
                               ed: Optional[str]) -> Optional[str]:
        """Build query string for a reference table."""
        if table_name == 'INSTRUMENT':
            return self._instrument_query(instrument_ids, columns)
        elif table_name == 'PARENT_INSTRUMENT':
            return self._parent_instrument_query(parent_instrument_ids, columns)
        elif table_name == 'INSTRUMENT_CATEGORIZATION':
            return self._instrument_categorization_query(instrument_ids, columns, system_version_timestamp, ed)
        elif table_name == 'ASSET_ALLOCATION_ANALYTICS_CATEGORY_V':
            return self._asset_allocation_query(asset_allocation_ids, columns)
        else:
            return self._generic_table_query(instrument_ids, table_name, columns)

    def _instrument_query(self, ids: List[int], columns: List[str]) -> Optional[str]:
        """Build query for INSTRUMENT table."""
        if not ids:
            return None
        columns_to_select = [c for c in columns if c != 'instrument_id']
        if not columns_to_select:
            columns_str = "instrument_id"
        else:
            columns_str = "instrument_id, " + ", ".join(columns_to_select)
        ids_str = ",".join(map(str, ids))
        return f"SELECT {columns_str} FROM INSTRUMENT WITH (NOLOCK) WHERE instrument_id IN ({ids_str})"

    def _parent_instrument_query(self, ids: List[int], columns: List[str]) -> Optional[str]:
        """Build query for PARENT_INSTRUMENT (queries INSTRUMENT table)."""
        valid_ids = [i for i in ids if i is not None and i != -2147483648]
        if not valid_ids:
            return None
        columns_to_select = [c for c in columns if c != 'instrument_id']
        if not columns_to_select:
            columns_str = "instrument_id"
        else:
            columns_str = "instrument_id, " + ", ".join(columns_to_select)
        ids_str = ",".join(map(str, valid_ids))
        return f"SELECT {columns_str} FROM INSTRUMENT WITH (NOLOCK) WHERE instrument_id IN ({ids_str})"

    def _instrument_categorization_query(self, ids: List[int], columns: List[str],
                                          system_version_timestamp: Optional[str],
                                          ed: Optional[str]) -> Optional[str]:
        """Build query for INSTRUMENT_CATEGORIZATION table."""
        if not ids:
            return None
        columns_to_select = [c for c in columns if c != 'instrument_id']
        if not columns_to_select:
            columns_str = "instrument_id"
        else:
            columns_str = "instrument_id, " + ", ".join(columns_to_select)
        ids_str = ",".join(map(str, ids))

        if system_version_timestamp:
            query = (
                f"SELECT {columns_str} FROM INSTRUMENT_CATEGORIZATION "
                f"FOR SYSTEM_TIME AS OF '{system_version_timestamp}' "
                f"WHERE instrument_id IN ({ids_str})"
            )
        else:
            query = (
                f"SELECT {columns_str} FROM INSTRUMENT_CATEGORIZATION WITH (NOLOCK) "
                f"WHERE instrument_id IN ({ids_str})"
            )

        if ed:
            query += f" AND ED = '{ed}'"

        return query

    def _asset_allocation_query(self, ids: List[int], columns: List[str]) -> Optional[str]:
        """Build query for ASSET_ALLOCATION_ANALYTICS_CATEGORY_V view."""
        valid_ids = [i for i in ids if i is not None and i != -2147483648]
        if not valid_ids:
            return None
        # Ensure analytics_category_id is included for joining
        if 'analytics_category_id' not in columns:
            columns = ['analytics_category_id'] + list(columns)
        columns_str = ", ".join(columns)
        ids_str = ",".join(map(str, valid_ids))
        return (
            f"SELECT {columns_str} FROM ASSET_ALLOCATION_ANALYTICS_CATEGORY_V WITH (NOLOCK) "
            f"WHERE analytics_category_id IN ({ids_str})"
        )

    def _generic_table_query(self, ids: List[int], table_name: str, columns: List[str]) -> Optional[str]:
        """Build query for any other table (fallback)."""
        valid_ids = [i for i in ids if i is not None and i != -2147483648]
        if not valid_ids:
            return None
        # Ensure instrument_id is included for joining
        if 'instrument_id' not in columns:
            columns = ['instrument_id'] + list(columns)
        columns_str = ", ".join(columns)
        ids_str = ",".join(map(str, valid_ids))
        return (
            f"SELECT {columns_str} FROM {table_name} WITH (NOLOCK) "
            f"WHERE instrument_id IN ({ids_str})"
        )
