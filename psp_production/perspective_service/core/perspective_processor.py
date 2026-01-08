"""
Perspective Processor - Processes data through perspective rules and modifiers.
"""

from typing import Dict, List, Tuple, Optional

import polars as pl

from perspective_service.core.configuration_manager import ConfigurationManager
from perspective_service.core.rule_evaluator import RuleEvaluator


class PerspectiveProcessor:
    """Processes data through perspective rules and modifiers."""

    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager

    def build_perspective_plan(self,
                               positions_lf: pl.LazyFrame,
                               lookthroughs_lf: pl.LazyFrame,
                               perspective_configs: Dict,
                               position_weights: List[str],
                               lookthrough_weights: List[str],
                               precomputed_values: Dict) -> Tuple[pl.LazyFrame, Optional[pl.LazyFrame], Dict]:
        """
        Build execution plan for all perspectives.

        Returns:
            Tuple of (processed_positions, processed_lookthroughs, metadata_map)
        """
        # Initialize collections for expressions
        factor_expressions_pos = []
        factor_expressions_lt = []

        metadata_map = {}
        has_lookthroughs = lookthroughs_lf is not None

        # Process each perspective configuration
        for config_name, perspective_map in perspective_configs.items():
            metadata_map[config_name] = {}
            perspective_ids = sorted([int(k) for k in perspective_map.keys()])

            for perspective_id in perspective_ids:
                # Create unique column name for this perspective
                column_name = f"f_{config_name}_{perspective_id}"
                metadata_map[config_name][perspective_id] = column_name

                # Get modifiers for this perspective
                modifier_names = perspective_map.get(str(perspective_id)) or []
                active_modifiers = self._filter_overridden_modifiers(modifier_names)

                # Build expressions for positions
                keep_expr = self._build_keep_expression(
                    perspective_id, active_modifiers, "position", precomputed_values
                )
                scale_expr = self._build_scale_expression(
                    perspective_id, "position", precomputed_values
                )
                factor_expressions_pos.append(
                    pl.when(keep_expr)
                    .then(scale_expr)
                    .otherwise(pl.lit(None))
                    .alias(column_name)
                )

                # Build expressions for lookthroughs if present
                if has_lookthroughs:
                    keep_expr_lt = self._build_keep_expression(
                        perspective_id, active_modifiers, "lookthrough", precomputed_values
                    )
                    scale_expr_lt = self._build_scale_expression(
                        perspective_id, "lookthrough", precomputed_values
                    )
                    factor_expressions_lt.append(
                        pl.when(keep_expr_lt)
                        .then(scale_expr_lt)
                        .otherwise(pl.lit(None))
                        .alias(column_name)
                    )

        # Apply factor expressions
        positions_lf = positions_lf.with_columns(factor_expressions_pos)
        if has_lookthroughs:
            lookthroughs_lf = lookthroughs_lf.with_columns(factor_expressions_lt)

            # Synchronize lookthroughs with parent positions
            all_columns = [c for m in metadata_map.values() for c in m.values()]
            lookthroughs_lf = self._synchronize_lookthroughs(
                lookthroughs_lf, positions_lf, all_columns
            )

        # Handle rescaling if needed
        positions_lf, lookthroughs_lf = self._apply_rescaling(
            positions_lf,
            lookthroughs_lf,
            perspective_configs,
            metadata_map,
            position_weights,
            lookthrough_weights,
            has_lookthroughs
        )

        return positions_lf, lookthroughs_lf if has_lookthroughs else None, metadata_map

    def _build_keep_expression(self,
                               perspective_id: int,
                               modifier_names: List[str],
                               mode: str,
                               precomputed_values: Dict) -> pl.Expr:
        """Build expression to determine if a row should be kept."""
        # Start with preprocessing modifiers
        expr = pl.lit(True)
        for modifier_name in modifier_names:
            modifier = self.config.modifiers.get(modifier_name)
            if modifier and modifier.modifier_type == "PreProcessing":
                if self._is_applicable(modifier.apply_to, mode):
                    # BUG FIX: PreProcessing modifiers EXCLUDE matching rows
                    # So we INVERT the criteria (keep rows that DON'T match)
                    expr &= ~RuleEvaluator.evaluate(
                        modifier.criteria, perspective_id, precomputed_values
                    )

        # Apply perspective rules
        rule_expr = self._build_rule_expression(perspective_id, mode, precomputed_values)

        # Apply postprocessing modifiers
        for modifier_name in modifier_names:
            modifier = self.config.modifiers.get(modifier_name)
            if modifier and modifier.modifier_type == "PostProcessing":
                if self._is_applicable(modifier.apply_to, mode):
                    savior_expr = RuleEvaluator.evaluate(
                        modifier.criteria, perspective_id, precomputed_values
                    )
                    if modifier.rule_result_operator == "or":
                        rule_expr = rule_expr | savior_expr
                    else:
                        rule_expr = rule_expr & savior_expr

        return expr & rule_expr

    def _build_rule_expression(self,
                               perspective_id: int,
                               mode: str,
                               precomputed_values: Dict) -> pl.Expr:
        """Build expression from perspective rules."""
        rules = self.config.perspectives.get(perspective_id, [])
        rule_expr = None

        for idx, rule in enumerate(rules):
            if rule.is_scaling_rule:
                continue
            if not self._is_applicable(rule.apply_to, mode):
                continue

            current_expr = RuleEvaluator.evaluate(
                rule.criteria, perspective_id, precomputed_values
            )

            if rule_expr is None:
                rule_expr = current_expr
            else:
                previous_rule = rules[idx - 1]
                if previous_rule.condition_for_next_rule == "Or":
                    rule_expr = rule_expr | current_expr
                else:
                    rule_expr = rule_expr & current_expr

        return rule_expr if rule_expr is not None else pl.lit(True)

    def _build_scale_expression(self,
                                perspective_id: int,
                                mode: str,
                                precomputed_values: Dict) -> pl.Expr:
        """Build scaling factor expression."""
        scale_factor = pl.lit(1.0)

        for rule in self.config.perspectives.get(perspective_id, []):
            if rule.is_scaling_rule and self._is_applicable(rule.apply_to, mode):
                criteria_expr = RuleEvaluator.evaluate(
                    rule.criteria, perspective_id, precomputed_values
                )
                scale_factor = pl.when(criteria_expr).then(
                    scale_factor * rule.scale_factor
                ).otherwise(scale_factor)

        return scale_factor

    def _synchronize_lookthroughs(self,
                                  lookthroughs_lf: pl.LazyFrame,
                                  positions_lf: pl.LazyFrame,
                                  factor_columns: List[str]) -> pl.LazyFrame:
        """Synchronize lookthrough factors with parent position factors."""
        # Get parent factors
        parent_factors = positions_lf.select(
            ["instrument_id", "sub_portfolio_id"] + factor_columns
        ).unique(subset=["instrument_id", "sub_portfolio_id"])

        # Rename columns for joining
        rename_map = {col: f"parent_{col}" for col in factor_columns}
        parent_factors = parent_factors.rename(rename_map)

        # Join with lookthroughs
        synchronized = lookthroughs_lf.join(
            parent_factors,
            left_on=["parent_instrument_id", "sub_portfolio_id"],
            right_on=["instrument_id", "sub_portfolio_id"],
            how="left"
        )

        # Apply parent factor nullification
        final_expressions = [
            pl.when(pl.col(f"parent_{col}").is_null())
            .then(pl.lit(None))
            .otherwise(pl.col(col))
            .alias(col)
            for col in factor_columns
        ]

        return synchronized.with_columns(final_expressions)

    def _apply_rescaling(self,
                         positions_lf: pl.LazyFrame,
                         lookthroughs_lf: Optional[pl.LazyFrame],
                         perspective_configs: Dict,
                         metadata_map: Dict,
                         position_weights: List[str],
                         lookthrough_weights: List[str],
                         has_lookthroughs: bool) -> Tuple[pl.LazyFrame, Optional[pl.LazyFrame]]:
        """Apply rescaling to normalize weights to 100%."""
        rescale_aggs_pos = []
        rescale_aggs_lt = []
        final_scale_exprs_pos = []
        final_scale_exprs_lt = []
        required_lt_sums = set()

        for config_name, perspective_map in perspective_configs.items():
            # Find perspectives that need rescaling
            rescale_positions = self._get_rescale_perspectives(
                perspective_map, "scale_holdings_to_100_percent"
            )
            rescale_lookthroughs = self._get_rescale_perspectives(
                perspective_map, "scale_lookthroughs_to_100_percent"
            )

            # Process position rescaling
            for perspective_id in rescale_positions:
                column_name = metadata_map[config_name][perspective_id]

                # Create aggregation expressions
                for weight in position_weights:
                    agg_name = f"sum_{weight}_{column_name}_pos"
                    rescale_aggs_pos.append(
                        (pl.col(weight) * pl.col(column_name)).sum().alias(agg_name)
                    )
                    required_lt_sums.add(f"sum_{weight}_{column_name}_lt")

                # Create rescaling expression
                primary_weight = position_weights[0]
                denominator = (
                    pl.col(f"sum_{primary_weight}_{column_name}_pos").fill_null(0) +
                    pl.col(f"sum_{primary_weight}_{column_name}_lt").fill_null(0)
                )
                final_scale_exprs_pos.append(
                    pl.when(denominator != 0)
                    .then(pl.col(column_name) / denominator)
                    .otherwise(pl.col(column_name))
                    .alias(column_name)
                )

            # Process lookthrough rescaling
            if has_lookthroughs and lookthroughs_lf is not None:
                for perspective_id in rescale_lookthroughs:
                    column_name = metadata_map[config_name][perspective_id]

                    # Create aggregation expressions
                    for weight in lookthrough_weights:
                        agg_name = f"sum_{weight}_{column_name}_lt"
                        rescale_aggs_lt.append(
                            (pl.col(weight) * pl.col(column_name)).sum().alias(agg_name)
                        )

                    # Create rescaling expression
                    primary_weight = lookthrough_weights[0]
                    total = (pl.col(primary_weight) * pl.col(column_name)).sum().over([
                        "container", "parent_instrument_id", "sub_portfolio_id", "record_type"
                    ])
                    final_scale_exprs_lt.append(
                        pl.when(total != 0)
                        .then(pl.col(column_name) / total)
                        .otherwise(pl.col(column_name))
                        .alias(column_name)
                    )

        # Apply rescaling if needed
        if rescale_aggs_pos:
            # Calculate sums
            pos_sums = positions_lf.group_by(["container", "sub_portfolio_id"]).agg(rescale_aggs_pos)

            if has_lookthroughs and lookthroughs_lf is not None and rescale_aggs_lt:
                lt_sums = (lookthroughs_lf
                           .filter(pl.col("record_type") == "essential_lookthroughs")
                           .group_by(["container", "sub_portfolio_id"])
                           .agg(rescale_aggs_lt))
            else:
                lt_sums = pos_sums.select(["container", "sub_portfolio_id"])

            # Add missing columns to lookthrough sums
            existing_cols = set(lt_sums.collect_schema().names())
            missing_zeros = [
                pl.lit(0.0).alias(name)
                for name in required_lt_sums
                if name not in existing_cols
            ]
            if missing_zeros:
                lt_sums = lt_sums.with_columns(missing_zeros)

            # Join and apply scaling
            positions_lf = (positions_lf
                            .join(pos_sums, on=["container", "sub_portfolio_id"], how="left")
                            .join(lt_sums, on=["container", "sub_portfolio_id"], how="left")
                            .with_columns(final_scale_exprs_pos))

        if has_lookthroughs and lookthroughs_lf is not None and final_scale_exprs_lt:
            lookthroughs_lf = lookthroughs_lf.with_columns(final_scale_exprs_lt)

        return positions_lf, lookthroughs_lf

    def _get_rescale_perspectives(self, perspective_map: Dict, modifier_key: str) -> List[int]:
        """Get perspective IDs that have a specific modifier."""
        result = []
        for perspective_id, modifiers in perspective_map.items():
            filtered_modifiers = self._filter_overridden_modifiers(modifiers or [])
            if modifier_key in filtered_modifiers:
                result.append(int(perspective_id))
        return result

    def _filter_overridden_modifiers(self, modifiers: List[str]) -> List[str]:
        """Filter out overridden modifiers."""
        final_set = set(modifiers + self.config.default_modifiers)

        for modifier in list(final_set):
            if modifier in self.config.modifier_overrides:
                for override in self.config.modifier_overrides[modifier]:
                    final_set.discard(override)

        return list(final_set)

    def _is_applicable(self, apply_to: str, mode: str) -> bool:
        """Check if a rule/modifier applies to the current mode."""
        apply_to = apply_to.lower()

        if apply_to == "both":
            return True
        if apply_to == "holding" and mode == "position":
            return True
        if apply_to in ["lookthrough", "reference"] and mode == "lookthrough":
            return True

        return False
