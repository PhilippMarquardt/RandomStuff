"""Data ingestion - extracts positions/lookthroughs from request JSON."""
import logging
from typing import Dict, List, Tuple, Any

import polars as pl
import polars.selectors as cs

from ..constants import INT_NULL, FLOAT_NULL

logger = logging.getLogger(__name__)


class DataIngestion:
    """Handles data loading and preparation from request JSON."""

    @staticmethod
    def build_dataframes(
        request_json: Dict[str, Any],
        weight_labels: List[str]
    ) -> Tuple[pl.LazyFrame, pl.LazyFrame]:
        """
        Build position and lookthrough dataframes from request JSON.

        Args:
            request_json: Request data containing containers with positions/lookthroughs
            weight_labels: List of weight column names to preserve nulls for

        Returns:
            Tuple of (positions_lf, lookthroughs_lf) as LazyFrames
        """
        # Extract position and lookthrough data
        positions_data, lookthroughs_data = DataIngestion._extract_data(request_json)

        if not positions_data:
            logger.warning("No position data found in request")
            return pl.LazyFrame(), pl.LazyFrame()

        # Create LazyFrames
        positions_lf = pl.LazyFrame(positions_data, infer_schema_length=None)
        lookthroughs_lf = DataIngestion._create_lookthrough_frame(lookthroughs_data)

        # Standardize columns
        positions_lf = DataIngestion._standardize_columns(positions_lf)
        lookthroughs_lf = DataIngestion._standardize_columns(lookthroughs_lf)

        # Fill nulls with sentinel values (except weight columns)
        positions_lf = DataIngestion._fill_null_values(positions_lf, weight_labels)
        lookthroughs_lf = DataIngestion._fill_null_values(lookthroughs_lf, weight_labels)

        logger.info(f"Built dataframes: positions={positions_lf.collect_schema().len()} cols, "
                    f"lookthroughs={lookthroughs_lf.collect_schema().len()} cols")

        return positions_lf, lookthroughs_lf

    @staticmethod
    def _extract_data(request_json: Dict) -> Tuple[List[Dict], List[Dict]]:
        """Extract position and lookthrough records from request JSON."""
        positions_data = []
        lookthroughs_data = []

        for container_name, container_data in request_json.items():
            # Skip non-container entries (like 'ed', 'perspective_configurations', etc.)
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

            # Extract lookthroughs (handles various lookthrough key names)
            for key, lookthrough_data in container_data.items():
                if "lookthrough" in key and isinstance(lookthrough_data, dict):
                    for lookthrough_id, lookthrough_attrs in lookthrough_data.items():
                        lookthroughs_data.append({
                            **lookthrough_attrs,
                            **container_info,
                            "identifier": lookthrough_id,
                            "record_type": key
                        })

        logger.info(f"Extracted {len(positions_data)} positions, {len(lookthroughs_data)} lookthroughs")
        return positions_data, lookthroughs_data

    @staticmethod
    def _create_lookthrough_frame(lookthrough_data: List[Dict]) -> pl.LazyFrame:
        """Create a LazyFrame for lookthrough data."""
        if lookthrough_data:
            return pl.LazyFrame(lookthrough_data, infer_schema_length=None)

        # Return empty frame with expected schema
        return pl.LazyFrame(schema={
            "instrument_identifier": pl.Int64,
            "parent_instrument_id": pl.Int64,
            "sub_portfolio_id": pl.Utf8,
            "instrument_id": pl.Int64
        })

    @staticmethod
    def _standardize_columns(lf: pl.LazyFrame) -> pl.LazyFrame:
        """Standardize column names and add missing columns."""
        columns = lf.collect_schema().names()

        if not columns:
            return lf

        standardizations = []

        # Rename instrument_identifier to instrument_id if present
        if "instrument_identifier" in columns:
            standardizations.append(
                pl.col("instrument_identifier").alias("instrument_id")
            )

        # Add sub_portfolio_id if missing
        if "sub_portfolio_id" in columns:
            standardizations.append(
                pl.col("sub_portfolio_id").fill_null("default").cast(pl.Utf8)
            )
        else:
            standardizations.append(
                pl.lit("default").alias("sub_portfolio_id")
            )

        # Add parent_instrument_id if missing
        if "parent_instrument_id" in columns:
            standardizations.append(
                pl.col("parent_instrument_id").cast(pl.Int64).fill_null(INT_NULL)
            )
        else:
            standardizations.append(
                pl.lit(INT_NULL).alias("parent_instrument_id")
            )

        if standardizations:
            lf = lf.with_columns(standardizations)

        return lf

    @staticmethod
    def _fill_null_values(lf: pl.LazyFrame, exclude_columns: List[str]) -> pl.LazyFrame:
        """Fill null values with sentinel values (except for weight columns)."""
        schema = lf.collect_schema()
        if not schema.names():
            return lf

        # Fill integer nulls (except excluded columns)
        lf = lf.with_columns(
            cs.numeric().exclude(exclude_columns).fill_null(INT_NULL)
        )

        # Fill float nulls specifically
        float_columns = [
            pl.col(col).fill_null(FLOAT_NULL)
            for col, dtype in schema.items()
            if col not in exclude_columns and dtype in [pl.Float32, pl.Float64]
        ]

        if float_columns:
            lf = lf.with_columns(float_columns)

        return lf

    @staticmethod
    def join_reference_data(
        positions_lf: pl.LazyFrame,
        lookthroughs_lf: pl.LazyFrame,
        reference_data: Dict[str, pl.DataFrame]
    ) -> Tuple[pl.LazyFrame, pl.LazyFrame]:
        """
        Join reference data to positions and lookthroughs.

        Args:
            positions_lf: Positions LazyFrame
            lookthroughs_lf: Lookthroughs LazyFrame
            reference_data: Dict of table_name -> DataFrame with reference data

        Returns:
            Tuple of (positions_lf, lookthroughs_lf) with reference data joined
        """
        has_lookthroughs = bool(lookthroughs_lf.collect_schema().names())

        for table_name, ref_df in reference_data.items():
            if ref_df.is_empty():
                continue

            ref_lf = ref_df.lazy()
            logger.info(f"Joining {table_name} ({len(ref_df)} rows)")

            # Join to positions
            positions_lf = positions_lf.join(ref_lf, on='instrument_id', how='left')

            # Join to lookthroughs if present
            if has_lookthroughs:
                lookthroughs_lf = lookthroughs_lf.join(ref_lf, on='instrument_id', how='left')

        return positions_lf, lookthroughs_lf
