"""Output formatter - formats results to final structure."""
import logging
from typing import Dict, List

import polars as pl

logger = logging.getLogger(__name__)


class OutputFormatter:
    """Formats the processed data into the final output structure."""

    @staticmethod
    def format_output(
        positions_df: pl.DataFrame,
        lookthroughs_df: pl.DataFrame,
        metadata_map: Dict[str, Dict[int, str]],
        position_weights: List[str],
        lookthrough_weights: List[str],
        verbose: bool = True
    ) -> Dict:
        """
        Format processed dataframes into structured output.

        Args:
            positions_df: Processed positions DataFrame
            lookthroughs_df: Processed lookthroughs DataFrame
            metadata_map: Mapping of config_name -> {perspective_id: column_name}
            position_weights: List of position weight columns
            lookthrough_weights: List of lookthrough weight columns
            verbose: Whether to include removal summaries

        Returns:
            Formatted output dictionary
        """
        if not metadata_map:
            return {"perspective_configurations": {}}

        results = OutputFormatter._initialize_results(metadata_map)

        # Get factor columns
        factor_columns = [
            col for pmap in metadata_map.values()
            for col in pmap.values()
        ]

        # Process positions
        if not positions_df.is_empty():
            OutputFormatter._process_dataframe(
                positions_df,
                "positions",
                metadata_map,
                factor_columns,
                position_weights,
                results,
                "identifier"
            )

        # Process lookthroughs
        if not lookthroughs_df.is_empty():
            OutputFormatter._process_dataframe(
                lookthroughs_df,
                "lookthrough",
                metadata_map,
                factor_columns,
                lookthrough_weights,
                results,
                "identifier"
            )

        # Add removal summary if verbose
        if verbose:
            OutputFormatter._add_removal_summary(
                positions_df,
                lookthroughs_df,
                metadata_map,
                factor_columns,
                position_weights,
                lookthrough_weights,
                results
            )

        logger.info(f"Formatted output with {len(results)} configurations")
        return {"perspective_configurations": results}

    @staticmethod
    def _initialize_results(metadata_map: Dict) -> Dict:
        """Initialize the results structure."""
        return {
            config_name: {str(pid): {} for pid in perspective_map}
            for config_name, perspective_map in metadata_map.items()
            if perspective_map
        }

    @staticmethod
    def _process_dataframe(
        df: pl.DataFrame,
        mode: str,
        metadata_map: Dict,
        factor_columns: List[str],
        weights: List[str],
        results: Dict,
        id_column: str
    ):
        """Process a batch of data and update results."""
        valid_weights = [w for w in weights if w in df.columns]
        if not valid_weights:
            return

        available_factors = [c for c in factor_columns if c in df.columns]
        if not available_factors:
            return

        # Build column selection
        base_cols = [id_column, "container"]
        if mode == "lookthrough":
            base_cols.append("record_type")

        # Pre-select only needed columns
        select_cols = base_cols + valid_weights + available_factors
        select_cols = [c for c in select_cols if c in df.columns]
        df_slim = df.select(select_cols)

        # Process each perspective
        for config_name, perspective_map in metadata_map.items():
            for perspective_id, col_name in perspective_map.items():
                if col_name not in df_slim.columns:
                    continue

                OutputFormatter._process_single_perspective(
                    df_slim,
                    mode,
                    config_name,
                    str(perspective_id),
                    col_name,
                    base_cols,
                    valid_weights,
                    id_column,
                    results
                )

    @staticmethod
    def _process_single_perspective(
        df: pl.DataFrame,
        mode: str,
        config_name: str,
        perspective_id: str,
        factor_col: str,
        base_cols: List[str],
        weights: List[str],
        id_column: str,
        results: Dict
    ):
        """Process a single perspective's data."""
        # Filter to non-null factors (kept items)
        filtered = df.filter(pl.col(factor_col).is_not_null())
        if filtered.is_empty():
            return

        # Compute weighted values
        weight_exprs = [
            (pl.col(w) * pl.col(factor_col)).alias(w)
            for w in weights
        ]
        weighted = filtered.select(base_cols + weight_exprs)

        # Partition by container (and record_type for lookthroughs)
        group_cols = ["container"]
        if mode == "lookthrough":
            group_cols.append("record_type")

        partitions = weighted.partition_by(group_cols, as_dict=True, maintain_order=False)

        for group_key, group_df in partitions.items():
            # Extract group values
            if isinstance(group_key, tuple):
                container = group_key[0]
                record_type = group_key[1] if len(group_key) > 1 else None
            else:
                container = group_key
                record_type = None

            # Build output dict
            formatted = OutputFormatter._df_to_id_dict(group_df, id_column, weights)

            # Store in results
            target = results[config_name][perspective_id].setdefault(container, {})

            if mode == "positions":
                target["positions"] = formatted
            else:
                target[record_type or "lookthrough"] = formatted

    @staticmethod
    def _df_to_id_dict(
        df: pl.DataFrame,
        id_column: str,
        value_columns: List[str]
    ) -> Dict:
        """Convert dataframe to {id: {col: val, ...}} dict."""
        if df.is_empty():
            return {}

        ids = df[id_column].to_list()

        if len(value_columns) == 1:
            col = value_columns[0]
            values = df[col].to_list()
            return {id_val: {col: val} for id_val, val in zip(ids, values)}

        # Multiple columns
        structs = df.select(pl.struct(value_columns).alias("_s"))["_s"].to_list()
        return dict(zip(ids, structs))

    @staticmethod
    def _add_removal_summary(
        positions_df: pl.DataFrame,
        lookthroughs_df: pl.DataFrame,
        metadata_map: Dict,
        factor_columns: List[str],
        position_weights: List[str],
        lookthrough_weights: List[str],
        results: Dict
    ):
        """Add summary of removed positions/lookthroughs."""
        # Process positions
        if not positions_df.is_empty():
            OutputFormatter._process_removals(
                positions_df,
                "positions",
                metadata_map,
                factor_columns,
                position_weights,
                results
            )

        # Process lookthroughs
        if not lookthroughs_df.is_empty():
            OutputFormatter._process_removals(
                lookthroughs_df,
                "lookthrough",
                metadata_map,
                factor_columns,
                lookthrough_weights,
                results
            )

    @staticmethod
    def _process_removals(
        df: pl.DataFrame,
        mode: str,
        metadata_map: Dict,
        factor_columns: List[str],
        weights: List[str],
        results: Dict
    ):
        """Process removals for a single dataframe."""
        available_factors = [c for c in factor_columns if c in df.columns]
        if not available_factors:
            return

        valid_weights = [w for w in weights if w in df.columns]
        if not valid_weights:
            return

        # Process each perspective
        for config_name, perspective_map in metadata_map.items():
            for perspective_id, col_name in perspective_map.items():
                if col_name not in df.columns:
                    continue

                # Filter to null factors (removed items)
                removed = df.filter(pl.col(col_name).is_null())
                if removed.is_empty():
                    continue

                # Group by container
                partitions = removed.partition_by(["container"], as_dict=True)

                for container, group_df in partitions.items():
                    if isinstance(container, tuple):
                        container = container[0]

                    formatted = OutputFormatter._df_to_id_dict(
                        group_df, "identifier", valid_weights
                    )

                    target = results[config_name][str(perspective_id)].setdefault(container, {})
                    summary_key = "removed_positions_weight_summary"

                    if mode == "positions":
                        target.setdefault(summary_key, {})["positions"] = formatted
                    else:
                        record_type = group_df["record_type"][0] if "record_type" in group_df.columns else "lookthrough"
                        target.setdefault(summary_key, {})[record_type] = formatted
