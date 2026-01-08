"""
Data Ingestion - Handles data loading and preparation from JSON input.
"""

from typing import Dict, List, Tuple, Optional

import polars as pl
import polars.selectors as cs

from perspective_service.utils.constants import INT_NULL, FLOAT_NULL
from perspective_service.database.loaders.reference_loader import ReferenceLoader


class DataIngestion:
    """Handles data loading and preparation from JSON input."""

    @staticmethod
    def build_dataframes(input_json: Dict,
                         required_tables: Dict[str, List[str]],
                         weight_labels: List[str],
                         reference_loader: Optional[ReferenceLoader] = None,
                         db_connection=None) -> Tuple[pl.LazyFrame, pl.LazyFrame]:
        """
        Build position and lookthrough dataframes from input JSON.

        Args:
            input_json: Raw input data
            required_tables: Tables required for joins {table_name: [columns]}
            weight_labels: List of weight column names
            reference_loader: ReferenceLoader instance for DB data
            db_connection: Database connection for reference data

        Returns:
            Tuple of (positions_df, lookthroughs_df) as LazyFrames
        """
        # Extract position and lookthrough data
        positions_data, lookthroughs_data = DataIngestion._extract_data(input_json)

        if not positions_data:
            return pl.LazyFrame(), pl.LazyFrame()

        # Create LazyFrames
        positions_lf = pl.LazyFrame(positions_data, infer_schema_length=None)
        lookthroughs_lf = DataIngestion._create_lookthrough_frame(lookthroughs_data)

        # Standardize columns
        positions_lf = DataIngestion._standardize_columns(positions_lf)
        if lookthroughs_lf is not None:
            lookthroughs_lf = DataIngestion._standardize_columns(lookthroughs_lf)

        # Fill nulls with sentinel values
        positions_lf = DataIngestion._fill_null_values(positions_lf, weight_labels)
        if lookthroughs_lf is not None:
            lookthroughs_lf = DataIngestion._fill_null_values(lookthroughs_lf, weight_labels)

        # Join reference data if needed
        if required_tables and reference_loader and db_connection:
            effective_date = input_json.get('ed', '2024-01-01')
            system_version_timestamp = input_json.get('system_version_timestamp')
            positions_lf, lookthroughs_lf = DataIngestion._join_reference_data(
                positions_lf, lookthroughs_lf, required_tables,
                reference_loader, db_connection,
                system_version_timestamp, effective_date
            )

        return positions_lf, lookthroughs_lf

    @staticmethod
    def _extract_data(input_json: Dict) -> Tuple[List[Dict], List[Dict]]:
        """Extract position and lookthrough records from input JSON."""
        positions_data = []
        lookthroughs_data = []

        for container_name, container_data in input_json.items():
            if not isinstance(container_data, dict) or "position_type" not in container_data:
                continue

            container_info = {
                "container": container_name,
                "position_type": container_data["position_type"]
            }

            # Extract positions
            if "positions" in container_data:
                for position_id, position_attrs in container_data["positions"].items():
                    positions_data.append({
                        **position_attrs,
                        **container_info,
                        "identifier": position_id,
                        "record_type": "position"
                    })

            # Extract lookthroughs
            for key, lookthrough_data in container_data.items():
                if "lookthrough" in key and isinstance(lookthrough_data, dict):
                    for lookthrough_id, lookthrough_attrs in lookthrough_data.items():
                        lookthroughs_data.append({
                            **lookthrough_attrs,
                            **container_info,
                            "identifier": lookthrough_id,
                            "record_type": key
                        })

        return positions_data, lookthroughs_data

    @staticmethod
    def _create_lookthrough_frame(lookthrough_data: List[Dict]) -> Optional[pl.LazyFrame]:
        """Create a LazyFrame for lookthrough data, or None if no data."""
        if lookthrough_data:
            return pl.LazyFrame(lookthrough_data, infer_schema_length=None)
        return None

    @staticmethod
    def _standardize_columns(lf: pl.LazyFrame) -> pl.LazyFrame:
        """Standardize column names. Only applies safe transformations."""
        columns = lf.collect_schema().names()

        standardizations = []

        # Rename instrument_identifier to instrument_id if exists
        if "instrument_identifier" in columns:
            standardizations.append(
                pl.col("instrument_identifier").alias("instrument_id")
            )

        # Default sub_portfolio_id to "default" if missing (common case for simple inputs)
        if "sub_portfolio_id" in columns:
            standardizations.append(
                pl.col("sub_portfolio_id").fill_null("default").cast(pl.Utf8)
            )
        else:
            standardizations.append(
                pl.lit("default").alias("sub_portfolio_id")
            )

        # Add perspective_id with INT_NULL if missing
        # Required by exclude_perspective_level_simulated_cash modifier
        # Regular positions have NULL, only "perspective-level simulated cash" has actual value
        # The actual perspective ID gets substituted in the VALUE at evaluation time (RuleEvaluator line 77-78)
        if "perspective_id" not in columns:
            standardizations.append(
                pl.lit(INT_NULL).alias("perspective_id")
            )

        if standardizations:
            return lf.with_columns(standardizations)
        return lf

    @staticmethod
    def _fill_null_values(lf: pl.LazyFrame, exclude_columns: List[str]) -> pl.LazyFrame:
        """Fill null values with sentinel values."""
        if not lf.collect_schema().names():
            return lf

        # Fill integer nulls
        lf = lf.with_columns(
            cs.numeric().exclude(exclude_columns).fill_null(INT_NULL)
        )

        # Fill float nulls
        float_columns = [
            pl.col(col).fill_null(FLOAT_NULL)
            for col, dtype in lf.collect_schema().items()
            if col not in exclude_columns and dtype in [pl.Float32, pl.Float64]
        ]

        if float_columns:
            lf = lf.with_columns(float_columns)

        return lf

    @staticmethod
    def _join_reference_data(positions_lf: pl.LazyFrame,
                             lookthroughs_lf: pl.LazyFrame,
                             required_tables: Dict[str, List[str]],
                             reference_loader: ReferenceLoader,
                             db_connection,
                             system_version_timestamp: Optional[str],
                             effective_date: str) -> Tuple[pl.LazyFrame, pl.LazyFrame]:
        """Join reference data from database."""
        # Get unique instrument IDs
        pos_ids = positions_lf.select('instrument_id')
        lt_ids = (lookthroughs_lf.select('instrument_id')
                  if lookthroughs_lf.collect_schema().names()
                  else pl.LazyFrame(schema={'instrument_id': pl.Int64}))

        unique_ids = pl.concat([pos_ids, lt_ids]).unique().collect().to_series().to_list()

        # Get unique parent_instrument_ids for PARENT_INSTRUMENT lookup (only if column exists)
        pos_columns = positions_lf.collect_schema().names()
        if 'parent_instrument_id' in pos_columns:
            parent_ids = positions_lf.select('parent_instrument_id').unique().collect().to_series().to_list()
        else:
            parent_ids = []

        # Ensure required base columns are included
        tables_to_load = dict(required_tables)
        base_columns = ['liquidity_type_id', 'position_source_type_id']

        if 'INSTRUMENT_CATEGORIZATION' not in tables_to_load:
            tables_to_load['INSTRUMENT_CATEGORIZATION'] = base_columns
        else:
            tables_to_load['INSTRUMENT_CATEGORIZATION'] = list(
                set(tables_to_load['INSTRUMENT_CATEGORIZATION'] + base_columns)
            )

        # Load reference data
        ref_data = reference_loader.load(
            db_connection,
            unique_ids,
            parent_ids,
            tables_to_load,
            system_version_timestamp,
            effective_date
        )

        # Join each table
        for table_name, ref_df in ref_data.items():
            if ref_df.is_empty():
                continue

            ref_lf = ref_df.lazy()

            if table_name == 'PARENT_INSTRUMENT':
                # Join on parent_instrument_id (only if column exists)
                if 'parent_instrument_id' in positions_lf.collect_schema().names():
                    positions_lf = positions_lf.join(
                        ref_lf,
                        left_on='parent_instrument_id',
                        right_on='parent_instrument_id',
                        how='left'
                    )
                    if lookthroughs_lf.collect_schema().names() and 'parent_instrument_id' in lookthroughs_lf.collect_schema().names():
                        lookthroughs_lf = lookthroughs_lf.join(
                            ref_lf,
                            left_on='parent_instrument_id',
                            right_on='parent_instrument_id',
                            how='left'
                        )
            else:
                # Join on instrument_id
                positions_lf = positions_lf.join(ref_lf, on='instrument_id', how='left')
                if lookthroughs_lf.collect_schema().names():
                    lookthroughs_lf = lookthroughs_lf.join(ref_lf, on='instrument_id', how='left')

        return positions_lf, lookthroughs_lf
