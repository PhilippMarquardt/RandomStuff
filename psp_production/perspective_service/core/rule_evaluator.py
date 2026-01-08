"""
Rule Evaluator - Converts rule criteria into Polars expressions for data filtering.
"""

import json
from typing import Dict, List, Any, Optional

import polars as pl


class RuleEvaluator:
    """Converts rule criteria into Polars expressions for data filtering."""

    @classmethod
    def evaluate(cls,
                 criteria: Dict[str, Any],
                 perspective_id: Optional[int] = None,
                 precomputed_values: Dict[str, List[Any]] = None) -> pl.Expr:
        """
        Convert rule criteria into a Polars expression.

        Args:
            criteria: Dictionary defining the filter criteria
            perspective_id: ID of the current perspective (for variable substitution)
            precomputed_values: Pre-computed values for nested criteria

        Returns:
            Polars expression representing the criteria
        """
        if not criteria:
            return pl.lit(True)

        # Handle logical operators
        if "and" in criteria:
            return cls._evaluate_and(criteria["and"], perspective_id, precomputed_values)
        if "or" in criteria:
            return cls._evaluate_or(criteria["or"], perspective_id, precomputed_values)
        if "not" in criteria:
            return ~cls.evaluate(criteria["not"], perspective_id, precomputed_values)

        # Handle simple criteria
        return cls._evaluate_simple_criteria(criteria, perspective_id, precomputed_values)

    @classmethod
    def _evaluate_and(cls, subcriteria: List[Dict], perspective_id: int, precomputed_values: Dict) -> pl.Expr:
        """Combine multiple criteria with AND logic."""
        if not subcriteria:
            return pl.lit(True)

        expr = cls.evaluate(subcriteria[0], perspective_id, precomputed_values)
        for crit in subcriteria[1:]:
            expr = expr & cls.evaluate(crit, perspective_id, precomputed_values)
        return expr

    @classmethod
    def _evaluate_or(cls, subcriteria: List[Dict], perspective_id: int, precomputed_values: Dict) -> pl.Expr:
        """Combine multiple criteria with OR logic."""
        if not subcriteria:
            return pl.lit(False)

        expr = cls.evaluate(subcriteria[0], perspective_id, precomputed_values)
        for crit in subcriteria[1:]:
            expr = expr | cls.evaluate(crit, perspective_id, precomputed_values)
        return expr

    @classmethod
    def _evaluate_simple_criteria(cls, criteria: Dict, perspective_id: int, precomputed_values: Dict) -> pl.Expr:
        """Evaluate a simple column-operator-value criteria."""
        column = criteria.get("column")
        operator = criteria.get("operator_type")
        value = criteria.get("value")

        if not column or not operator:
            return pl.lit(True)

        # Substitute perspective_id in value if needed
        if perspective_id and isinstance(value, str) and 'perspective_id' in value:
            value = value.replace('perspective_id', str(perspective_id))

        # Handle precomputed nested criteria
        if operator in ["In", "NotIn"] and isinstance(value, dict):
            if precomputed_values:
                criteria_key = json.dumps(value, sort_keys=True)
                matching_values = precomputed_values.get(criteria_key, [])
                if operator == "In":
                    return pl.col(column).is_in(matching_values)
                return ~pl.col(column).is_in(matching_values)
            return pl.lit(True)

        # Parse and apply the operator
        parsed_value = cls._parse_value(value, operator)
        return cls._apply_operator(operator, column, parsed_value)

    @classmethod
    def _apply_operator(cls, operator: str, column: str, value: Any) -> pl.Expr:
        """Apply a comparison operator to create a Polars expression."""
        operators = {
            "=": lambda c, v: pl.col(c) == v,
            "==": lambda c, v: pl.col(c) == v,
            "!=": lambda c, v: pl.col(c) != v,
            ">": lambda c, v: pl.col(c) > v,
            "<": lambda c, v: pl.col(c) < v,
            ">=": lambda c, v: pl.col(c) >= v,
            "<=": lambda c, v: pl.col(c) <= v,
            "In": lambda c, v: pl.col(c).is_in(v),
            "NotIn": lambda c, v: ~pl.col(c).is_in(v),
            "IsNull": lambda c, v: pl.col(c).is_null(),
            "IsNotNull": lambda c, v: pl.col(c).is_not_null(),
            "Between": lambda c, v: (pl.col(c) >= v[0]) & (pl.col(c) <= v[1]),
            "NotBetween": lambda c, v: (pl.col(c) < v[0]) | (pl.col(c) > v[1]),
            "Like": lambda c, v: cls._build_like_expr(c, v, False),
            "NotLike": lambda c, v: cls._build_like_expr(c, v, True),
        }

        return operators.get(operator, lambda c, v: pl.lit(True))(column, value)

    @classmethod
    def _build_like_expr(cls, column: str, pattern: str, negate: bool) -> pl.Expr:
        """Build a LIKE expression for pattern matching."""
        pattern_lower = pattern.lower()
        expr = pl.col(column).str.to_lowercase()

        if pattern.startswith("%") and pattern.endswith("%"):
            expr = expr.str.contains(pattern_lower[1:-1])
        elif pattern.endswith("%"):
            expr = expr.str.starts_with(pattern_lower[:-1])
        elif pattern.startswith("%"):
            expr = expr.str.ends_with(pattern_lower[1:])
        else:
            expr = expr == pattern_lower

        return ~expr if negate else expr

    @staticmethod
    def _parse_value(value: Any, operator: str) -> Any:
        """Parse value based on operator requirements."""
        if operator in ["IsNull", "IsNotNull"]:
            return None

        if operator in ["In", "NotIn"]:
            if isinstance(value, str):
                # Strip brackets, parentheses, and quotes to handle formats like "('USD','EUR')" or "[4,8,9]"
                items = [item.strip().strip("'\"") for item in value.strip("[]()").split(",")]
                return [int(x) if x.lstrip('-').isdigit() else x for x in items]
            return value if isinstance(value, list) else [value]

        if operator in ["Between", "NotBetween"]:
            if isinstance(value, str) and 'fncriteria:' in value:
                try:
                    parts = value.replace('fncriteria:', '').split(':')
                    return [float(p) if p.replace('.', '', 1).isdigit() else p for p in parts]
                except ValueError:
                    return [0, 0]
            return value if isinstance(value, list) and len(value) == 2 else [0, 0]

        # Strip embedded quotes from string values (DB stores values like 'USD')
        if isinstance(value, str):
            return value.strip("'\"")
        return value
