"""Perspective processor - builds filter/scale expressions and applies them."""
import logging
from typing import Dict, List, Tuple, Optional, Any

import polars as pl

from ..models import Rule, Modifier, Perspective
from .rule_evaluator import RuleEvaluator

logger = logging.getLogger(__name__)


class PerspectiveProcessor:
    """Processes data through perspective rules and modifiers."""

    def __init__(
        self,
        perspectives: Dict[int, Perspective],
        modifiers: Dict[str, Dict[str, Any]],
        default_modifiers: Optional[List[str]] = None
    ):
        """
        Initialize the processor.

        Args:
            perspectives: Dict of perspective_id -> Perspective
            modifiers: Dict of modifier_name -> modifier definition dict
            default_modifiers: List of modifiers applied to all perspectives
        """
        self.perspectives = perspectives
        self.modifiers = modifiers
        self.default_modifiers = default_modifiers or []

        # Build modifier overrides map
        self.modifier_overrides: Dict[str, List[str]] = {}
        for name, mod_def in modifiers.items():
            if 'override_modifiers' in mod_def:
                self.modifier_overrides[name] = mod_def['override_modifiers']

    def build_perspective_plan(
        self,
        positions_lf: pl.LazyFrame,
        lookthroughs_lf: pl.LazyFrame,
        perspective_configs: Dict[str, Dict[str, List[str]]],
        position_weights: List[str],
        lookthrough_weights: List[str],
        precomputed_values: Optional[Dict] = None
    ) -> Tuple[pl.LazyFrame, Optional[pl.LazyFrame], Dict]:
        """
        Build execution plan for all perspectives.

        Args:
            positions_lf: Positions LazyFrame
            lookthroughs_lf: Lookthroughs LazyFrame
            perspective_configs: Dict of config_name -> {perspective_id: [modifiers]}
            position_weights: List of position weight columns
            lookthrough_weights: List of lookthrough weight columns
            precomputed_values: Precomputed values for nested criteria

        Returns:
            Tuple of (processed_positions, processed_lookthroughs, metadata_map)
        """
        precomputed_values = precomputed_values or {}

        # Initialize collections for expressions
        factor_expressions_pos = []
        factor_expressions_lt = []

        metadata_map = {}
        has_lookthroughs = bool(lookthroughs_lf.collect_schema().names())

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
        if factor_expressions_pos:
            positions_lf = positions_lf.with_columns(factor_expressions_pos)

        if has_lookthroughs and factor_expressions_lt:
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

        logger.info(f"Built plan for {sum(len(m) for m in metadata_map.values())} perspective configs")

        return positions_lf, lookthroughs_lf if has_lookthroughs else None, metadata_map

    def _build_keep_expression(
        self,
        perspective_id: int,
        modifier_names: List[str],
        mode: str,
        precomputed_values: Dict
    ) -> pl.Expr:
        """Build expression to determine if a row should be kept."""
        # Start with preprocessing modifiers (items matching are REMOVED)
        expr = pl.lit(True)
        for modifier_name in modifier_names:
            mod_def = self.modifiers.get(modifier_name)
            if mod_def and mod_def.get('type') == "PreProcessing":
                if self._is_applicable(mod_def.get('apply_to', 'both'), mode):
                    # Invert: matching items are removed, so we want NOT matching
                    criteria_expr = RuleEvaluator.evaluate(
                        mod_def.get('criteria'), perspective_id, precomputed_values
                    )
                    expr = expr & ~criteria_expr

        # Apply perspective rules
        rule_expr = self._build_rule_expression(perspective_id, mode, precomputed_values)
        expr = expr & rule_expr

        # Apply postprocessing modifiers (saviors)
        for modifier_name in modifier_names:
            mod_def = self.modifiers.get(modifier_name)
            if mod_def and mod_def.get('type') == "PostProcessing":
                if self._is_applicable(mod_def.get('apply_to', 'both'), mode):
                    savior_expr = RuleEvaluator.evaluate(
                        mod_def.get('criteria'), perspective_id, precomputed_values
                    )
                    if mod_def.get('rule_result_operator') == "or":
                        expr = expr | savior_expr
                    else:
                        expr = expr & savior_expr

        return expr

    def _build_rule_expression(
        self,
        perspective_id: int,
        mode: str,
        precomputed_values: Dict
    ) -> pl.Expr:
        """Build expression from perspective rules."""
        perspective = self.perspectives.get(perspective_id)
        if not perspective:
            return pl.lit(True)

        rules = perspective.rules
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

    def _build_scale_expression(
        self,
        perspective_id: int,
        mode: str,
        precomputed_values: Dict
    ) -> pl.Expr:
        """Build scaling factor expression."""
        scale_factor = pl.lit(1.0)

        perspective = self.perspectives.get(perspective_id)
        if not perspective:
            return scale_factor

        for rule in perspective.rules:
            if rule.is_scaling_rule and self._is_applicable(rule.apply_to, mode):
                criteria_expr = RuleEvaluator.evaluate(
                    rule.criteria, perspective_id, precomputed_values
                )
                scale_factor = pl.when(criteria_expr).then(
                    scale_factor * rule.scale_factor
                ).otherwise(scale_factor)

        return scale_factor

    def _synchronize_lookthroughs(
        self,
        lookthroughs_lf: pl.LazyFrame,
        positions_lf: pl.LazyFrame,
        factor_columns: List[str]
    ) -> pl.LazyFrame:
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

    def _apply_rescaling(
        self,
        positions_lf: pl.LazyFrame,
        lookthroughs_lf: Optional[pl.LazyFrame],
        perspective_configs: Dict,
        metadata_map: Dict,
        position_weights: List[str],
        lookthrough_weights: List[str],
        has_lookthroughs: bool
    ) -> Tuple[pl.LazyFrame, Optional[pl.LazyFrame]]:
        """Apply rescaling to normalize weights to 100%."""
        # Find perspectives that need rescaling
        rescale_needed = False
        for config_name, perspective_map in perspective_configs.items():
            for perspective_id, modifiers in perspective_map.items():
                filtered = self._filter_overridden_modifiers(modifiers or [])
                if 'scale_holdings_to_100_percent' in filtered or 'scale_lookthroughs_to_100_percent' in filtered:
                    rescale_needed = True
                    break

        if not rescale_needed:
            return positions_lf, lookthroughs_lf

        # For now, simplified rescaling - full implementation in POC
        logger.info("Rescaling applied (simplified)")
        return positions_lf, lookthroughs_lf

    def _filter_overridden_modifiers(self, modifiers: List[str]) -> List[str]:
        """Filter out overridden modifiers."""
        final_set = set(modifiers + self.default_modifiers)

        for modifier in list(final_set):
            if modifier in self.modifier_overrides:
                for override in self.modifier_overrides[modifier]:
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
