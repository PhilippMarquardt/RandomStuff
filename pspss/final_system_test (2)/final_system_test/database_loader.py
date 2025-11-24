"""
Database Loader Interface for Perspective Service

Provides abstraction layer for loading reference data from database.
Allows easy swapping between mock data (testing) and real SQL database (production).

FUTURE WORK:
    The original service supports multiple instrument_identifier_types (ISIN, Bloomberg, SEDOL, etc.)
    and requires a lookup_instrument_ids() method to convert identifiers to database IDs.

    For now, we assume instrument_identifier IS instrument_id (no conversion needed).

    To add identifier lookup later:
    1. Add lookup_instrument_ids(identifiers: List[str], identifier_type: str) method
    2. Call it to convert identifiers → id_list
    3. Pass id_list to load_reference_table() - no signature changes needed!
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import polars as pl


class DatabaseLoader(ABC):
    """Abstract base class for loading reference data from database"""

    @abstractmethod
    def load_reference_table(
        self,
        id_list: List[int],
        table_name: str,
        columns_required: List[str],
        ed: Optional[str] = None,
        system_version_timestamp: Optional[str] = None
    ) -> pl.DataFrame:
        """
        Load reference table from database.

        Matches original stored proc signature:
        EXEC [dbo].[GET_DATA_FOR_PERSPECTIVE_SERVICE]
            'id1,id2,id3',           -- id_list (comma-separated string in original)
            'table_name',            -- table_name
            'col1,col2,col3'         -- columns_required (comma-separated, excludes instrument_id)

        Args:
            id_list: List of instrument IDs (integers)
                     In original: Comes from converting instrument_identifier → instrument_id
                     For now: We assume instrument_identifier IS instrument_id
            table_name: Table to load from
                - 'INSTRUMENT' - Basic instrument data (asset_class, sector, currency, etc.)
                - 'INSTRUMENT_CATEGORIZATION' - Market cap, liquidity type, etc. (requires ed)
                - 'PARENT_INSTRUMENT' - Uses 'INSTRUMENT' table internally
                - 'ASSET_ALLOCATION_ANALYTICS_CATEGORY_V' - Asset allocation data
            columns_required: Column names to load (instrument_id is added automatically by DB)
            ed: Effective date (YYYY-MM-DD format)
                Required for INSTRUMENT_CATEGORIZATION table
            system_version_timestamp: Optional temporal query parameter
                Format: 'YYYY-MM-DD HH:MM:SS'

        Returns:
            DataFrame with columns:
                - instrument_id (always included)
                - All columns from columns_required

        Raises:
            Exception: If table_name is unknown or required parameters missing
        """
        pass


class MockDatabaseLoader(DatabaseLoader):
    """
    Mock implementation with hardcoded test data.

    Provides realistic reference data for instruments used in test files.
    Easy to extend with more instruments/columns as needed.
    """

    # Mock data for INSTRUMENT table
    # Maps instrument_id → {asset_class, sector, currency, rating, ...}
    INSTRUMENT_DATA = {
        100: {
            'asset_class': 'Equity',
            'sector': 'Technology',
            'currency': 'USD',
            'rating': 'AAA',
            'country': 'United States'
        },
        200: {
            'asset_class': 'Equity',
            'sector': 'Communication Services',
            'currency': 'USD',
            'rating': 'AA',
            'country': 'United States'
        },
        300: {
            'asset_class': 'Equity',
            'sector': 'Technology',
            'currency': 'USD',
            'rating': 'AAA',
            'country': 'United States'
        },
        400: {
            'asset_class': 'Fixed Income',
            'sector': 'Government',
            'currency': 'USD',
            'rating': 'AAA',
            'country': 'United States'
        },
        500: {
            'asset_class': 'Equity',
            'sector': 'Consumer Discretionary',
            'currency': 'USD',
            'rating': 'A',
            'country': 'United States'
        },
        666: {
            'asset_class': 'Equity',
            'sector': 'Energy',
            'currency': 'USD',
            'rating': None,
            'country': 'United States'
        },
        777: {
            'asset_class': 'Equity',
            'sector': None,
            'currency': 'USD',
            'rating': None,
            'country': 'United States'
        },
        999: {
            'asset_class': 'Equity',
            'sector': 'Technology',
            'currency': 'USD',
            'rating': 'AAA',
            'country': 'United States'
        }
    }

    # Mock data for INSTRUMENT_CATEGORIZATION table
    # Maps instrument_id → {market_cap, liquidity_type_id, position_source_type_id, ...}
    INSTRUMENT_CATEGORIZATION_DATA = {
        100: {
            'market_cap': 3000000000000,  # $3T
            'liquidity_type_id': 1,       # Highly liquid
            'position_source_type_id': 1
        },
        200: {
            'market_cap': 2000000000000,  # $2T
            'liquidity_type_id': 1,
            'position_source_type_id': 1
        },
        300: {
            'market_cap': 2500000000000,  # $2.5T
            'liquidity_type_id': 1,
            'position_source_type_id': 1
        },
        400: {
            'market_cap': 0,  # Fixed income - no market cap
            'liquidity_type_id': 2,  # Moderately liquid
            'position_source_type_id': 1
        },
        500: {
            'market_cap': 1500000000000,  # $1.5T
            'liquidity_type_id': 1,
            'position_source_type_id': 1
        },
        666: {
            'market_cap': 0,
            'liquidity_type_id': 6,  # Cash liquidity type
            'position_source_type_id': 10  # Cash source type
        },
        777: {
            'market_cap': 0,
            'liquidity_type_id': 6,
            'position_source_type_id': 10
        },
        999: {
            'market_cap': 0,
            'liquidity_type_id': 6,
            'position_source_type_id': 10
        }
    }

    def load_reference_table(
        self,
        id_list: List[int],
        table_name: str,
        columns_required: List[str],
        ed: Optional[str] = None,
        system_version_timestamp: Optional[str] = None
    ) -> pl.DataFrame:
        """
        Load mock reference data.

        Returns DataFrame matching the structure of real database results.
        """

        # Determine which mock data to use
        if table_name == 'INSTRUMENT' or table_name == 'PARENT_INSTRUMENT':
            mock_data = self.INSTRUMENT_DATA
        elif table_name == 'INSTRUMENT_CATEGORIZATION':
            if ed is None:
                raise ValueError("INSTRUMENT_CATEGORIZATION requires 'ed' parameter")
            mock_data = self.INSTRUMENT_CATEGORIZATION_DATA
        else:
            raise ValueError(f"Unknown table_name: {table_name}. Supported: INSTRUMENT, INSTRUMENT_CATEGORIZATION, PARENT_INSTRUMENT")

        # Build result rows
        rows = []
        for instrument_id in id_list:
            # Get data for this instrument (or None if not found)
            instrument_data = mock_data.get(instrument_id)

            if instrument_data is None:
                # Instrument not found - return row with nulls
                # In real DB, the stored proc would not return a row for missing instruments
                # But for testing, we'll return null values
                row = {'instrument_id': instrument_id}
                for col in columns_required:
                    row[col] = None
            else:
                # Instrument found - extract requested columns
                row = {'instrument_id': instrument_id}
                for col in columns_required:
                    # Get column value, default to None if column doesn't exist
                    row[col] = instrument_data.get(col)

            rows.append(row)

        # Convert to Polars DataFrame
        if not rows:
            # No instruments requested - return empty DataFrame with correct schema
            schema = {'instrument_id': pl.Int64}
            for col in columns_required:
                schema[col] = pl.Utf8  # Default to string type
            return pl.DataFrame(schema=schema)

        return pl.DataFrame(rows)

    def add_mock_instrument(self, instrument_id: int, instrument_data: dict, categorization_data: dict = None):
        """
        Add a new mock instrument for testing.

        Args:
            instrument_id: Database instrument ID
            instrument_data: Dict with instrument fields (asset_class, sector, etc.)
            categorization_data: Optional dict with categorization fields (market_cap, liquidity_type_id, etc.)
        """
        self.INSTRUMENT_DATA[instrument_id] = instrument_data
        if categorization_data:
            self.INSTRUMENT_CATEGORIZATION_DATA[instrument_id] = categorization_data


# Example usage:
if __name__ == "__main__":
    # Create mock loader
    loader = MockDatabaseLoader()

    # Load INSTRUMENT table
    df = loader.load_reference_table(
        id_list=[100, 200, 300],
        table_name='INSTRUMENT',
        columns_required=['asset_class', 'sector', 'currency']
    )
    print("INSTRUMENT table:")
    print(df.shape)
    print(df.columns)
    print()

    # Load INSTRUMENT_CATEGORIZATION table
    df = loader.load_reference_table(
        id_list=[100, 200, 300],
        table_name='INSTRUMENT_CATEGORIZATION',
        columns_required=['market_cap', 'liquidity_type_id'],
        ed='2024-01-15'
    )
    print("INSTRUMENT_CATEGORIZATION table:")
    print(df.shape)
    print(df.columns)
