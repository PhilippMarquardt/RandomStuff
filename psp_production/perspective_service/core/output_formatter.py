"""
Output Formatter - Formats the processed data into the final output structure.
"""

from typing import Dict, List

import polars as pl


class OutputFormatter:
    """Formats the processed data into the final output structure."""

    @staticmethod
    def format_output(positions_df: pl.DataFrame,
                      lookthroughs_df: pl.DataFrame,
                      metadata_map: Dict,
                      position_weights: List[str],
                      lookthrough_weights: List[str],
                      verbose: bool,
                      flatten_response: bool = False) -> Dict:
        """Format processed dataframes into structured output."""
        if not metadata_map:
            return {"perspective_configurations": {}}

        results = OutputFormatter._initialize_results(metadata_map)

        # Get factor columns once
        factor_columns = [
            col for pmap in metadata_map.values()
            for col in pmap.values()
        ]

        # Process positions
        if not positions_df.is_empty():
            OutputFormatter._process_dataframe_batch(
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
            OutputFormatter._process_dataframe_batch(
                lookthroughs_df,
                "lookthrough",
                metadata_map,
                factor_columns,
                lookthrough_weights,
                results,
                "identifier"
            )

        # Add removal summary and scale_factors if verbose
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
            OutputFormatter._add_scale_factors(
                positions_df,
                metadata_map,
                factor_columns,
                position_weights,
                results
            )

        # Flatten response if requested (converts row-based to columnar format)
        if flatten_response:
            OutputFormatter._flatten_results(results)

        return {"perspective_configurations": results}

    @staticmethod
    def _initialize_results(metadata_map: Dict) -> Dict:
        """Initialize the results structure."""
        return {
            config_name: {pid: {} for pid in perspective_map}
            for config_name, perspective_map in metadata_map.items()
            if perspective_map
        }

    @staticmethod
    def _process_dataframe_batch(df: pl.DataFrame,
                                 mode: str,
                                 metadata_map: Dict,
                                 factor_columns: List[str],
                                 weights: List[str],
                                 results: Dict,
                                 id_column: str):
        """Process a batch of data and update results."""
        valid_weights = [w for w in weights if w in df.columns]
        if not valid_weights:
            return

        available_factors = [c for c in factor_columns if c in df.columns]
        if not available_factors:
            return

        # Build column selection once
        base_cols = [id_column, "container"]
        if mode == "lookthrough":
            base_cols.append("record_type")

        # Pre-select only needed columns
        select_cols = base_cols + valid_weights + available_factors
        df_slim = df.select(select_cols)

        # Process each perspective directly
        for config_name, perspective_map in metadata_map.items():
            for perspective_id, col_name in perspective_map.items():
                if col_name not in df_slim.columns:
                    continue

                OutputFormatter._process_single_perspective(
                    df_slim,
                    mode,
                    config_name,
                    perspective_id,
                    col_name,
                    base_cols,
                    valid_weights,
                    id_column,
                    results
                )

    @staticmethod
    def _process_single_perspective(df: pl.DataFrame,
                                    mode: str,
                                    config_name: str,
                                    perspective_id: int,
                                    factor_col: str,
                                    base_cols: List[str],
                                    weights: List[str],
                                    id_column: str,
                                    results: Dict):
        """Process a single perspective's data."""
        # Filter to non-null factors
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
            # Extract group values - container is always first
            if isinstance(group_key, tuple):
                container = group_key[0]
                record_type = group_key[1] if len(group_key) > 1 else None
            else:
                container = group_key
                record_type = None

            # Build output dict
            formatted = OutputFormatter._df_to_id_dict(group_df, id_column, weights)

            # Ensure container dict exists at perspective level
            perspective_target = results[config_name][perspective_id]
            if container not in perspective_target:
                perspective_target[container] = {}
            target = perspective_target[container]

            if mode == "positions":
                if "positions" not in target:
                    target["positions"] = {}
                target["positions"].update(formatted)
            else:
                key = record_type or "lookthrough"
                if key not in target:
                    target[key] = {}
                target[key].update(formatted)

    @staticmethod
    def _df_to_id_dict(df: pl.DataFrame, id_column: str, value_columns: List[str]) -> Dict:
        """Convert dataframe to {id: {col: val, ...}} dict efficiently."""
        if df.is_empty():
            return {}

        ids = df[id_column].to_list()

        if len(value_columns) == 1:
            # Single column: avoid struct overhead
            col = value_columns[0]
            values = df[col].to_list()
            return {id_val: {col: val} for id_val, val in zip(ids, values)}

        # Multiple columns: use struct
        structs = df.select(pl.struct(value_columns).alias("_s"))["_s"].to_list()
        return dict(zip(ids, structs))

    @staticmethod
    def _add_removal_summary(positions_df: pl.DataFrame,
                             lookthroughs_df: pl.DataFrame,
                             metadata_map: Dict,
                             factor_columns: List[str],
                             position_weights: List[str],
                             lookthrough_weights: List[str],
                             results: Dict):
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
    def _process_removals(df: pl.DataFrame,
                          mode: str,
                          metadata_map: Dict,
                          factor_columns: List[str],
                          weights: List[str],
                          results: Dict):
        """Process removals for a single dataframe."""
        available_factors = [c for c in factor_columns if c in df.columns]
        if not available_factors:
            return

        valid_weights = [w for w in weights if w in df.columns]
        if not valid_weights:
            return

        # Quick check: any nulls at all?
        null_check = df.select([
            pl.any_horizontal([pl.col(c).is_null() for c in available_factors]).alias("has_null")
        ])
        if not null_check["has_null"].any():
            return  # Nothing removed

        # Process each perspective
        for config_name, perspective_map in metadata_map.items():
            for perspective_id, col_name in perspective_map.items():
                if col_name not in df.columns:
                    continue

                OutputFormatter._process_removals_for_perspective(
                    df,
                    mode,
                    config_name,
                    perspective_id,
                    col_name,
                    valid_weights,
                    results
                )

    @staticmethod
    def _process_removals_for_perspective(df: pl.DataFrame,
                                          mode: str,
                                          config_name: str,
                                          perspective_id: int,
                                          factor_col: str,
                                          weights: List[str],
                                          results: Dict):
        """Process removals for a single perspective."""
        # Filter to null factors (removed items)
        removed = df.filter(pl.col(factor_col).is_null())
        if removed.is_empty():
            return

        if mode == "positions":
            OutputFormatter._process_position_removals(
                removed, config_name, perspective_id, weights, results
            )
        else:
            OutputFormatter._process_lookthrough_removals(
                removed, config_name, perspective_id, weights, results
            )

    @staticmethod
    def _process_position_removals(df: pl.DataFrame,
                                   config_name: str,
                                   perspective_id: int,
                                   weights: List[str],
                                   results: Dict):
        """Process position removals per container."""
        # Partition by container
        partitions = df.partition_by("container", as_dict=True, maintain_order=False)

        for container, container_df in partitions.items():
            if isinstance(container, tuple):
                container = container[0]

            formatted = OutputFormatter._df_to_id_dict(container_df, "identifier", weights)

            # Store at container level
            perspective_target = results[config_name][perspective_id]
            if container not in perspective_target:
                perspective_target[container] = {}
            target = perspective_target[container]

            if "removed_positions_weight_summary" not in target:
                target["removed_positions_weight_summary"] = {}
            if "positions" not in target["removed_positions_weight_summary"]:
                target["removed_positions_weight_summary"]["positions"] = {}
            target["removed_positions_weight_summary"]["positions"].update(formatted)

    @staticmethod
    def _process_lookthrough_removals(df: pl.DataFrame,
                                      config_name: str,
                                      perspective_id: int,
                                      weights: List[str],
                                      results: Dict):
        """Process lookthrough removals with aggregation by parent, per container."""
        if "parent_instrument_id" not in df.columns:
            return

        # Aggregate by container, record_type and parent instrument
        group_cols = ["container", "record_type", "parent_instrument_id"]
        agg_exprs = [pl.col(w).sum().alias(w) for w in weights]

        aggregated = df.group_by(group_cols).agg(agg_exprs)

        if aggregated.is_empty():
            return

        # Partition by container and record_type
        partitions = aggregated.partition_by(
            ["container", "record_type"],
            as_dict=True,
            maintain_order=False
        )

        for group_key, group_df in partitions.items():
            if isinstance(group_key, tuple):
                container = group_key[0]
                record_type = group_key[1] if len(group_key) > 1 else None
            else:
                container = group_key
                record_type = None

            # Convert parent_instrument_id to string for output
            group_df = group_df.with_columns(
                pl.col("parent_instrument_id").cast(pl.Utf8)
            )

            formatted = OutputFormatter._df_to_id_dict(
                group_df, "parent_instrument_id", weights
            )

            # Store at container level
            perspective_target = results[config_name][perspective_id]
            if container not in perspective_target:
                perspective_target[container] = {}
            target = perspective_target[container]

            if "removed_positions_weight_summary" not in target:
                target["removed_positions_weight_summary"] = {}
            if record_type not in target["removed_positions_weight_summary"]:
                target["removed_positions_weight_summary"][record_type] = {}
            target["removed_positions_weight_summary"][record_type].update(formatted)

    @staticmethod
    def _add_scale_factors(positions_df: pl.DataFrame,
                           metadata_map: Dict,
                           factor_columns: List[str],
                           position_weights: List[str],
                           results: Dict):
        """
        Add scale_factors to output - sum of KEPT weights per weight label PER CONTAINER.

        This matches the original core_perspective_service behavior where
        scale_factors = sum of weights of positions that were NOT removed.
        Only added for containers that have at least one removed position.
        """
        if positions_df.is_empty():
            return

        available_factors = [c for c in factor_columns if c in positions_df.columns]
        if not available_factors:
            return

        valid_weights = [w for w in position_weights if w in positions_df.columns]
        if not valid_weights:
            return

        # Process each perspective
        for config_name, perspective_map in metadata_map.items():
            for perspective_id, col_name in perspective_map.items():
                if col_name not in positions_df.columns:
                    continue

                # Find containers that have at least one removed position
                containers_with_removals = (
                    positions_df
                    .filter(pl.col(col_name).is_null())
                    .select("container")
                    .unique()
                    .to_series()
                    .to_list()
                )

                if not containers_with_removals:
                    continue

                # Filter to KEPT positions (factor is NOT null) in containers with removals
                kept = positions_df.filter(
                    (pl.col(col_name).is_not_null()) &
                    (pl.col("container").is_in(containers_with_removals))
                )

                if kept.is_empty():
                    # All positions were removed in these containers
                    continue

                # Group by container and SUM weights of KEPT positions
                agg_exprs = [pl.col(w).sum().alias(w) for w in valid_weights]
                aggregated = kept.group_by("container").agg(agg_exprs)

                # Add scale_factors per container
                for row in aggregated.iter_rows(named=True):
                    container = row["container"]
                    scale_factors = {w: row[w] for w in valid_weights if row[w] is not None}

                    if scale_factors:
                        # Ensure container exists
                        perspective_target = results[config_name][perspective_id]
                        if container not in perspective_target:
                            perspective_target[container] = {}
                        perspective_target[container]["scale_factors"] = scale_factors

    @staticmethod
    def _flatten_results(results: Dict) -> None:
        """
        Flatten positions and lookthroughs from row-based to columnar format.

        Converts from:
            {"positions": {"123": {"weight": 0.5}, "456": {"weight": 0.2}}}
        To:
            {"positions": {"identifier": [123, 456], "weight": [0.5, 0.2]}}
        """
        for config_name, perspectives in results.items():
            for perspective_id, containers in perspectives.items():
                for container_name, container_data in containers.items():
                    # Flatten positions
                    if "positions" in container_data:
                        container_data["positions"] = OutputFormatter._flatten_entries(
                            container_data["positions"]
                        )

                    # Flatten all lookthrough types
                    for key in list(container_data.keys()):
                        if "lookthrough" in key:
                            container_data[key] = OutputFormatter._flatten_entries(
                                container_data[key]
                            )

    @staticmethod
    def _flatten_entries(entries: Dict) -> Dict:
        """
        Convert row-based dict to columnar format.

        Input:  {"123": {"weight": 0.5, "exposure": 0.3}, "456": {"weight": 0.2, "exposure": 0.1}}
        Output: {"identifier": [123, 456], "weight": [0.5, 0.2], "exposure": [0.3, 0.1]}
        """
        if not entries:
            return {"identifier": []}

        processed = {"identifier": []}

        for entry_id, entry_data in entries.items():
            # Try to convert identifier to int, otherwise keep as string
            try:
                processed["identifier"].append(int(entry_id))
            except (ValueError, TypeError):
                processed["identifier"].append(entry_id)

            # Add each property value to its column
            for key, value in entry_data.items():
                if key not in processed:
                    processed[key] = []
                # Round floats to 13 decimal places (matching original)
                if isinstance(value, float):
                    value = round(value, 13)
                processed[key].append(value)

        return processed
