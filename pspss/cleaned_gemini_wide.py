"""
Perspective Engine - A rule-based data filtering and transformation system.

This module processes financial position and lookthrough data based on configurable
rules and modifiers, applying perspective-specific transformations.

Main Flow:
1. Load configuration (rules, modifiers, perspectives)
2. Ingest and prepare data from JSON input
3. Apply rules and modifiers to filter/transform data
4. Scale and normalize weights as needed
5. Output structured results per perspective
"""

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from pathlib import Path

import polars as pl
import polars.selectors as cs


# =============================================================================
# CONFIGURATION
# =============================================================================

# Sentinel values for null handling takenm from old implementation
INT_NULL = -2147483648 
FLOAT_NULL = -2147483648.49438


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class Rule:
    """Represents a single filtering or scaling rule."""
    name: str
    apply_to: str  # 'position', 'lookthrough', or 'both' TODO: Make enum..
    criteria: Optional[Dict[str, Any]] = None
    expr: Optional[pl.Expr] = None
    condition_for_next_rule: Optional[str] = None  # 'And' or 'Or' TODO: Make enum..
    is_scaling_rule: bool = False
    scale_factor: float = 1.0


@dataclass
class Modifier:
    """Represents a rule modifier that can adjust rule behavior."""
    name: str
    apply_to: str  # 'position', 'lookthrough', or 'both' TODO: Make enum..
    modifier_type: str  # 'PreProcessing', 'PostProcessing', or 'Scaling' TODO: Make enum..
    criteria: Optional[Dict[str, Any]] = None
    expr: Optional[pl.Expr] = None
    rule_result_operator: Optional[str] = None  # 'and' or 'or' TODO: Make enum..


# =============================================================================
# RULE EVALUATION ENGINE
# =============================================================================

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
                items = [item.strip() for item in value.strip("[]").split(",")]
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
        
        return value


# =============================================================================
# CONFIGURATION MANAGEMENT
# =============================================================================

class ConfigurationManager:
    """Manages rules, modifiers, and perspective configurations."""
    
    def __init__(self, rules_path: str = "rules.json"):
        self.perspectives: Dict[int, List[Rule]] = {}
        self.modifiers: Dict[str, Modifier] = {}
        self.default_modifiers: List[str] = []
        self.modifier_overrides: Dict[str, List[str]] = {}
        self.required_columns_by_perspective: Dict[int, Dict[str, List[str]]] = {}
        
        self._load_configuration(rules_path)
    
    def _load_configuration(self, rules_path: str):
        """Load configuration from JSON file."""
        try:
            with open(rules_path, "r") as f:
                config_data = json.load(f)
        except FileNotFoundError:
            print(f"Configuration file not found: {rules_path}")
            self._load_default_configuration()
            return
        
        self._parse_perspectives(config_data.get("perspectives", {}))
        self._parse_modifiers(config_data.get("modifiers", {}))
        self.default_modifiers = config_data.get("default_modifiers", [])
        self.modifier_overrides = config_data.get("modifier_overrides", {})
    
    def _parse_perspectives(self, perspectives_data: Dict):
        """Parse perspective configurations into Rule objects."""
        for perspective_id, perspective_def in self._iterate_perspectives(perspectives_data):
            if not perspective_def.get("is_active", True):
                continue

            rules = []
            required_columns = {}

            for idx, rule_def in enumerate(perspective_def.get("rules", [])):
                # Extract required columns
                criteria = self._parse_criteria(rule_def.get("criteria", {}))
                if 'required_columns' in criteria:
                    self._update_required_columns(required_columns, criteria['required_columns'])

                # Create rule
                rule = Rule(
                    name=f"rule_{idx}",
                    apply_to=rule_def.get("apply_to", "both"),
                    criteria=self._clean_criteria(criteria),
                    condition_for_next_rule=rule_def.get("condition_for_next_rule"),
                    is_scaling_rule=bool(rule_def.get("is_scaling_rule", False)),
                    scale_factor=rule_def.get("scale_factor", 100.0) / 100.0
                )
                rules.append(rule)

            self.perspectives[perspective_id] = rules
            if required_columns:
                self.required_columns_by_perspective[perspective_id] = required_columns
    
    def _parse_modifiers(self, modifiers_data: Dict):
        """Parse modifier configurations into Modifier objects."""
        for name, modifier_def in modifiers_data.items():
            modifier_type = self._determine_modifier_type(modifier_def.get("type", "PreProcessing"))
            rule_def = modifier_def.get("rule", {}) or {}
            criteria = self._parse_criteria(rule_def.get("criteria", {}))
            
            modifier = Modifier(
                name=name,
                apply_to=rule_def.get("apply_to", "both"),
                modifier_type=modifier_type,
                criteria=self._clean_criteria(criteria),
                rule_result_operator=modifier_def.get("rule_result_operator", "and")
            )
            self.modifiers[name] = modifier
    
    def _iterate_perspectives(self, perspectives_data):
        """Iterate through perspectives regardless of data structure."""
        if isinstance(perspectives_data, dict):
            for pid_str, p_def in perspectives_data.items():
                yield int(pid_str), p_def
        else:
            for p_def in perspectives_data:
                if p_def.get("id"):
                    yield int(p_def["id"]), p_def
    
    def _determine_modifier_type(self, type_str: str) -> str:
        """Determine the modifier type from string."""
        if any(x in type_str for x in ["PostProcessing", "TradeCash", "SimulatedCash"]):
            return "PostProcessing"
        elif "Scaling" in type_str:
            return "Scaling"
        else:
            return "PreProcessing"
    
    def _parse_criteria(self, criteria):
        """Parse criteria from string or dict."""
        if isinstance(criteria, str):
            return json.loads(criteria)
        return criteria
    
    def _clean_criteria(self, criteria):
        """Remove metadata from criteria."""
        if not isinstance(criteria, dict):
            return criteria
        return {k: v for k, v in criteria.items() if k != 'required_columns'}
    
    def _update_required_columns(self, required_columns: Dict, new_columns: Dict):
        """Update required columns dictionary."""
        for table, columns in new_columns.items():
            if table not in required_columns:
                required_columns[table] = []
            for col in columns:
                if col not in required_columns[table]:
                    required_columns[table].append(col)

    def _load_default_configuration(self):
        """Load a default configuration if file is not found."""
        self.perspectives = {}
        self.modifiers = {}
        self.default_modifiers = []
        self.modifier_overrides = {}


# =============================================================================
# DATA INGESTION
# =============================================================================

class DataIngestion:
    """Handles data loading and preparation from JSON input."""
    
    @staticmethod
    def build_dataframes(input_json: Dict, 
                        required_tables: Dict,
                        weight_labels: List[str],
                        database_loader) -> Tuple[pl.LazyFrame, pl.LazyFrame]:
        """
        Build position and lookthrough dataframes from input JSON.
        
        Args:
            input_json: Raw input data
            required_tables: Tables required for joins
            weight_labels: List of weight column names
            database_loader: Database loader for reference data
            
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
        lookthroughs_lf = DataIngestion._standardize_columns(lookthroughs_lf)
        
        # Fill nulls with sentinel values
        positions_lf = DataIngestion._fill_null_values(positions_lf, weight_labels)
        lookthroughs_lf = DataIngestion._fill_null_values(lookthroughs_lf, weight_labels)
        
        # Join reference data if needed
        if required_tables:
            effective_date = input_json.get('ed', '2024-01-01')
            positions_lf, lookthroughs_lf = DataIngestion._join_reference_data(
                positions_lf, lookthroughs_lf, required_tables, database_loader, effective_date
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
        
        standardizations = [
            # Rename instrument_identifier to instrument_id
            pl.col("instrument_identifier").alias("instrument_id"),
        ]
        
        # Add sub_portfolio_id if missing
        # TODO: Stupid for now as we will make it required
        if "sub_portfolio_id" in columns:
            standardizations.append(
                pl.col("sub_portfolio_id").fill_null("default").cast(pl.Utf8)
            )
        else:
            standardizations.append(
                pl.lit("default").alias("sub_portfolio_id")
            )
        
        # Add parent_instrument_id if missing
        #TODO: Can be removed
        if "parent_instrument_id" in columns:
            standardizations.append(
                pl.col("parent_instrument_id").cast(pl.Int64).fill_null(INT_NULL)
            )
        else:
            standardizations.append(
                pl.lit(INT_NULL).alias("parent_instrument_id")
            )
        
        return lf.with_columns(standardizations)
    
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
                            required_tables: Dict,
                            database_loader,
                            effective_date: str) -> Tuple[pl.LazyFrame, pl.LazyFrame]:
        """Join reference data from database."""
        # Get unique instrument IDs
        pos_ids = positions_lf.select('instrument_id')
        lt_ids = (lookthroughs_lf.select('instrument_id') 
                 if lookthroughs_lf.collect_schema().names() 
                 else pl.LazyFrame(schema={'instrument_id': pl.Int64}))
        
        unique_ids = pl.concat([pos_ids, lt_ids]).unique().collect().to_series().to_list()
        
        # Ensure required base columns are included
        tables_to_load = dict(required_tables)
        base_columns = ['liquidity_type_id', 'position_source_type_id']
        
        if 'INSTRUMENT_CATEGORIZATION' not in tables_to_load:
            tables_to_load['INSTRUMENT_CATEGORIZATION'] = base_columns
        else:
            tables_to_load['INSTRUMENT_CATEGORIZATION'] = list(
                set(tables_to_load['INSTRUMENT_CATEGORIZATION'] + base_columns)
            )
        
        # Join each required table
        for table_name, columns in tables_to_load.items():
            db_columns = [c for c in columns if c != 'instrument_id']
            
            # Load reference data
            if table_name == 'INSTRUMENT':
                ref_lf = database_loader.load_reference_table(
                    unique_ids, table_name, db_columns
                ).lazy()
            elif table_name == 'INSTRUMENT_CATEGORIZATION':
                ref_lf = database_loader.load_reference_table(
                    unique_ids, table_name, db_columns, ed=effective_date
                ).lazy()
            else:
                ref_lf = pl.LazyFrame()
            
            # Join to both dataframes
            if ref_lf.collect_schema().names():
                positions_lf = positions_lf.join(ref_lf, on='instrument_id', how='left')
                if lookthroughs_lf.collect_schema().names():
                    lookthroughs_lf = lookthroughs_lf.join(ref_lf, on='instrument_id', how='left')
        
        return positions_lf, lookthroughs_lf


# =============================================================================
# PERSPECTIVE PROCESSOR
# =============================================================================

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
                    expr &= RuleEvaluator.evaluate(
                        modifier.criteria, perspective_id, precomputed_values
                    )
                    #TODO: We need to invert here...
        
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


# =============================================================================
# OUTPUT FORMATTER
# =============================================================================

class OutputFormatter:
    """Formats the processed data into the final output structure."""
    
    @staticmethod
    def format_output(positions_df: pl.DataFrame,
                     lookthroughs_df: pl.DataFrame,
                     metadata_map: Dict,
                     position_weights: List[str],
                     lookthrough_weights: List[str],
                     verbose: bool) -> Dict:
        """
        Format processed dataframes into structured output.
        """
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
        
        # Process each perspective directly (no melt!)
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
    def _process_single_perspective(df: pl.DataFrame,
                                    mode: str,
                                    config_name: str,
                                    perspective_id: str,
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
            # Extract group values
            if isinstance(group_key, tuple):
                container = group_key[0]
                record_type = group_key[1] if len(group_key) > 1 else None
            else:
                container = group_key
                record_type = None
            
            # Build output dict using struct + zip (faster than iter_rows)
            formatted = OutputFormatter._df_to_id_dict(group_df, id_column, weights)
            
            # Store in results
            target = results[config_name][perspective_id].setdefault(container, {})
            
            if mode == "positions":
                target["positions"] = formatted
            else:
                target[record_type or "lookthrough"] = formatted
    
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
                    str(perspective_id),
                    col_name,
                    valid_weights,
                    results
                )
    
    @staticmethod
    def _process_removals_for_perspective(df: pl.DataFrame,
                                          mode: str,
                                          config_name: str,
                                          perspective_id: str,
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
                                   perspective_id: str,
                                   weights: List[str],
                                   results: Dict):
        """Process position removals."""
        group_cols = ["container"]
        partitions = df.partition_by(group_cols, as_dict=True, maintain_order=False)
        
        for container, group_df in partitions.items():
            if isinstance(container, tuple):
                container = container[0]
            
            formatted = OutputFormatter._df_to_id_dict(group_df, "identifier", weights)
            
            target = results[config_name][perspective_id].setdefault(container, {})
            target.setdefault("removed_positions_weight_summary", {})["positions"] = formatted
    
    @staticmethod
    def _process_lookthrough_removals(df: pl.DataFrame,
                                      config_name: str,
                                      perspective_id: str,
                                      weights: List[str],
                                      results: Dict):
        """Process lookthrough removals with aggregation by parent."""
        if "parent_instrument_id" not in df.columns:
            return
        
        # Aggregate by parent instrument
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
            container, record_type = group_key
            
            # Convert parent_instrument_id to string for output
            group_df = group_df.with_columns(
                pl.col("parent_instrument_id").cast(pl.Utf8)
            )
            
            formatted = OutputFormatter._df_to_id_dict(
                group_df, "parent_instrument_id", weights
            )
            
            target = results[config_name][perspective_id].setdefault(container, {})
            target.setdefault("removed_positions_weight_summary", {})[record_type] = formatted


# =============================================================================
# MAIN ENGINE
# =============================================================================

class PerspectiveEngine:
    """
    Main orchestrator for the perspective processing pipeline.
    
    This engine coordinates the entire flow:
    1. Configuration loading
    2. Data ingestion
    3. Rule processing
    4. Output formatting
    """
    
    def __init__(self, rules_path: str = "rules.json", database_loader=None):
        """
        Initialize the perspective engine.
        
        Args:
            rules_path: Path to the configuration JSON file
            database_loader: Database loader for reference data
        """
        # Use mock loader if none provided
        if database_loader is None:
            class MockDatabaseLoader:
                def load_reference_table(self, ids, table, columns, ed=None):
                    return pl.DataFrame({"instrument_id": ids})
            database_loader = MockDatabaseLoader()
        
        self.db_loader = database_loader
        self.config_manager = ConfigurationManager(rules_path)
        self.processor = PerspectiveProcessor(self.config_manager)
    
    @contextmanager
    def timer(self, label: str):
        """Context manager for timing operations."""
        start = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start
            print(f"[TIMING] {label}: {elapsed:.4f}s")
    
    def process(self, input_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data through all configured perspectives.
        
        Args:
            input_json: Input data containing positions, lookthroughs, and configurations
            
        Returns:
            Processed results organized by perspective configurations
        """
        with self.timer("Total Processing Time"):
            # 1. Extract configuration from input
            with self.timer("1. Configuration Setup"):
                perspective_configs = input_json.get("perspective_configurations", {})
                position_weights = input_json.get("position_weight_labels", ["weight"])
                lookthrough_weights = input_json.get("lookthrough_weight_labels", ["weight"])
                verbose_output = input_json.get("verbose_output", True)
                
                # Determine required database tables
                required_tables = self._determine_required_tables(perspective_configs)
            
            # 2. Build base dataframes
            with self.timer("2. Data Ingestion"):
                positions_lf, lookthroughs_lf = DataIngestion.build_dataframes(
                    input_json,
                    required_tables,
                    position_weights + lookthrough_weights,
                    self.db_loader
                )
            
            # 3. Precompute nested criteria values
            with self.timer("3. Precomputing Nested Criteria"):
                precomputed_values = self._precompute_nested_criteria(
                    positions_lf, perspective_configs
                )
            
            # 4. Build execution plan
            with self.timer("4. Building Execution Plan"):
                final_positions, final_lookthroughs, metadata_map = \
                    self.processor.build_perspective_plan(
                        positions_lf,
                        lookthroughs_lf,
                        perspective_configs,
                        position_weights,
                        lookthrough_weights,
                        precomputed_values
                    )
            
            # 5. Execute plan (materialize)
            with self.timer("5. Materializing Results"):
                if final_lookthroughs is not None:
                    positions_df, lookthroughs_df = pl.collect_all([
                        final_positions, final_lookthroughs
                    ])
                else:
                    positions_df = final_positions.collect()
                    lookthroughs_df = pl.DataFrame()
            
            # 6. Format output
            with self.timer("6. Formatting Output"):
                return OutputFormatter.format_output(
                    positions_df,
                    lookthroughs_df,
                    metadata_map,
                    position_weights,
                    lookthrough_weights,
                    verbose_output
                )
    
    def _determine_required_tables(self, perspective_configs: Dict) -> Dict[str, List[str]]:
        """Determine which database tables and columns are required."""
        requirements = {}
        all_perspective_ids = set()
        all_modifiers = set(self.config_manager.default_modifiers)
        
        # Collect all perspective IDs and modifiers
        for perspective_map in perspective_configs.values():
            for pid, modifiers in perspective_map.items():
                all_perspective_ids.add(int(pid))
                if modifiers:
                    all_modifiers.update(modifiers)
        
        # Get required columns from perspective definitions
        for perspective_id in all_perspective_ids:
            if perspective_id in self.config_manager.required_columns_by_perspective:
                for table, columns in self.config_manager.required_columns_by_perspective[perspective_id].items():
                    table = table.replace('InstrumentInput', 'position_data')
                    if table.lower() != 'position_data':
                        if table not in requirements:
                            requirements[table] = ['instrument_id']
                        for col in columns:
                            if col.lower() != 'instrument_id' and col not in requirements[table]:
                                requirements[table].append(col)
        
        # Extract table requirements from criteria
        def extract_from_criteria(criteria):
            if not criteria:
                return
            
            if "and" in criteria:
                for c in criteria["and"]:
                    extract_from_criteria(c)
            elif "or" in criteria:
                for c in criteria["or"]:
                    extract_from_criteria(c)
            elif "not" in criteria:
                extract_from_criteria(criteria["not"])
            else:
                table_name = criteria.get('table_name', 'position_data')
                column_name = criteria.get('column')
                
                if table_name != 'position_data':
                    if table_name not in requirements:
                        requirements[table_name] = ['instrument_id']
                    if column_name and column_name not in requirements[table_name]:
                        requirements[table_name].append(column_name)
                
                # Check for nested criteria
                if isinstance(criteria.get('value'), dict):
                    extract_from_criteria(criteria.get('value'))
        
        # Process all rules and modifiers
        for perspective_id in all_perspective_ids:
            for rule in self.config_manager.perspectives.get(perspective_id, []):
                extract_from_criteria(rule.criteria)
        
        for modifier_name in all_modifiers:
            if modifier_name in self.config_manager.modifiers:
                extract_from_criteria(self.config_manager.modifiers[modifier_name].criteria)
        
        return requirements
    
    def _precompute_nested_criteria(self, 
                                   lf: pl.LazyFrame, 
                                   perspective_configs: Dict) -> Dict[str, List[Any]]:
        """Precompute values for nested criteria (criteria within criteria)."""
        nested_queries = {}
        
        def find_nested_criteria(criteria):
            if not criteria:
                return
            
            if "and" in criteria:
                for c in criteria["and"]:
                    find_nested_criteria(c)
            elif "or" in criteria:
                for c in criteria["or"]:
                    find_nested_criteria(c)
            elif "not" in criteria:
                find_nested_criteria(criteria["not"])
            else:
                value = criteria.get("value")
                operator = criteria.get("operator_type")
                
                # Check for nested criteria in In/NotIn operators
                if operator in ["In", "NotIn"] and isinstance(value, dict):
                    key = json.dumps(value, sort_keys=True)
                    target_column = criteria.get("column")
                    
                    # Build query for nested criteria
                    inner_expr = RuleEvaluator.evaluate(value, None, None)
                    query = (
                        lf.filter(inner_expr)
                        .select(pl.col(target_column))
                        .drop_nulls()
                        .unique()
                    )
                    nested_queries[key] = query
        
        # Search all rules and modifiers for nested criteria
        for perspective_map in perspective_configs.values():
            for perspective_id in perspective_map.keys():
                # Check perspective rules
                for rule in self.config_manager.perspectives.get(int(perspective_id), []):
                    if rule.criteria:
                        find_nested_criteria(rule.criteria)
                
                # Check modifiers
                modifier_names = perspective_map[perspective_id] or []
                all_modifiers = list(set(modifier_names + self.config_manager.default_modifiers))
                for modifier_name in all_modifiers:
                    if modifier_name in self.config_manager.modifiers:
                        modifier = self.config_manager.modifiers[modifier_name]
                        if modifier.criteria:
                            find_nested_criteria(modifier.criteria)
        
        # Execute all nested queries
        if not nested_queries:
            return {}
        
        keys = list(nested_queries.keys())
        results = pl.collect_all(list(nested_queries.values()))
        
        return {
            key: result.to_series().to_list()
            for key, result in zip(keys, results)
        }


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """Main entry point for testing."""
    # Load test data
    test_file = Path("mock_input.json")
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return
    
    with open(test_file, "r") as f:
        input_data = json.load(f)
    
    # Create and run engine
    engine = PerspectiveEngine()
    result = engine.process(input_data)
    
    # Output results
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()


# Backward compatibility alias
FastPerspectiveEngine = PerspectiveEngine