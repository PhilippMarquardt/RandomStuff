"""
EXTREME PERFORMANCE VERSION - polars_recreationfast_final_v6.py

Architecture: SPLIT DATAFRAMES + VECTORIZED LONG FORMAT
- Pure Lazy Execution (Fixed .is_empty() crashes).
- Separates Positions and Lookthroughs.
- Dynamic Lookthrough Type handling.
- Auto-detects Table Requirements.
"""

import polars as pl
import polars.selectors as cs
import json
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass

# Constants
INT_NULL = -2147483648
FLOAT_NULL = -2147483648.49438

# -----------------------------------------------------------------------------
# 1. Data Structures & Rule Engine
# -----------------------------------------------------------------------------

@dataclass
class CompiledRule:
    expr: Optional[pl.Expr]
    apply_to: str
    name: str
    condition_for_next_rule: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    is_scaling_rule: bool = False
    scale_factor: float = 1.0

@dataclass
class CompiledModifier:
    expr: Optional[pl.Expr]
    apply_to: str
    name: str
    modifier_type: str
    rule_result_operator: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None

@dataclass
class NestedCriteria:
    criteria: Dict[str, Any]

class RuleEvaluator:
    OPERATORS = {
        "=": lambda col, val: pl.col(col) == val,
        "==": lambda col, val: pl.col(col) == val,
        "!=": lambda col, val: pl.col(col) != val,
        ">": lambda col, val: pl.col(col) > val,
        "<": lambda col, val: pl.col(col) < val,
        ">=": lambda col, val: pl.col(col) >= val,
        "<=": lambda col, val: pl.col(col) <= val,
        "In": lambda col, val: pl.col(col).is_in(val),
        "NotIn": lambda col, val: ~pl.col(col).is_in(val),
        "Between": lambda col, val: (pl.col(col) >= val[0]) & (pl.col(col) <= val[1]),
        "NotBetween": lambda col, val: (pl.col(col) < val[0]) | (pl.col(col) > val[1]),
        "Like": lambda col, val: RuleEvaluator._build_like_expr(col, val, False),
        "NotLike": lambda col, val: RuleEvaluator._build_like_expr(col, val, True),
        "IsNull": lambda col, val: pl.col(col).is_null(),
        "IsNotNull": lambda col, val: pl.col(col).is_not_null(),
    }

    @classmethod
    def evaluate_criteria(cls, criteria: Dict[str, Any], perspective_id: Optional[int] = None, lf: Optional[pl.LazyFrame] = None) -> pl.Expr:
        if "and" in criteria:
            sub = criteria["and"]
            if not sub: return pl.lit(True)
            expr = cls.evaluate_criteria(sub[0], perspective_id, lf)
            for crit in sub[1:]: expr = expr & cls.evaluate_criteria(crit, perspective_id, lf)
            return expr

        if "or" in criteria:
            sub = criteria["or"]
            if not sub: return pl.lit(False)
            expr = cls.evaluate_criteria(sub[0], perspective_id, lf)
            for crit in sub[1:]: expr = expr | cls.evaluate_criteria(crit, perspective_id, lf)
            return expr

        if "not" in criteria:
            return ~cls.evaluate_criteria(criteria["not"], perspective_id, lf)

        column = criteria.get("column")
        operator_type = criteria.get("operator_type")
        value = criteria.get("value")

        if not column or not operator_type: return pl.lit(True)

        if perspective_id is not None and isinstance(value, str) and 'perspective_id' in value:
            value = value.replace('perspective_id', str(perspective_id))

        parsed_value = cls._parse_value(value, operator_type)

        if operator_type in ["In", "NotIn"] and isinstance(parsed_value, NestedCriteria):
            if lf is None: return pl.lit(True)
            try:
                matching_values = (
                    lf.filter(cls.evaluate_criteria(parsed_value.criteria, perspective_id, lf))
                    .select(column)
                    .filter(pl.col(column).is_not_null())
                    .collect().to_series().unique().to_list()
                )
                if operator_type == "In": return pl.col(column).is_in(matching_values) if matching_values else pl.lit(False)
                else: return ~pl.col(column).is_in(matching_values) if matching_values else pl.lit(True)
            except Exception: return pl.lit(True)

        op_func = cls.OPERATORS.get(operator_type)
        return op_func(column, parsed_value) if op_func else pl.lit(True)

    @staticmethod
    def _parse_value(value: Any, operator_type: str) -> Any:
        if operator_type in ["IsNull", "IsNotNull"]: return None
        if operator_type in ["In", "NotIn"]:
            if isinstance(value, dict): return NestedCriteria(criteria=value)
            if isinstance(value, str):
                items = [item.strip() for item in value.strip("[]").split(",")]
                return [int(x) if x.lstrip('-').isdigit() else x for x in items]
            return value if isinstance(value, list) else [value]
        if operator_type in ["Between", "NotBetween"]:
            if isinstance(value, str) and 'fncriteria:' in value:
                try:
                    parts = value.replace('fncriteria:', '').split(':')
                    return [eval(p) if isinstance(p, str) else p for p in parts]
                except: return [0, 0]
            return value if isinstance(value, list) and len(value) == 2 else [0, 0]
        return value

    @staticmethod
    def _build_like_expr(col: str, val: str, negate: bool) -> pl.Expr:
        val_lower = val.lower()
        if val.startswith("%") and val.endswith("%"): expr = pl.col(col).str.to_lowercase().str.contains(val_lower[1:-1])
        elif val.endswith("%"): expr = pl.col(col).str.to_lowercase().str.starts_with(val_lower[:-1])
        elif val.startswith("%"): expr = pl.col(col).str.to_lowercase().str.ends_with(val_lower[1:])
        else: expr = pl.col(col).str.to_lowercase() == val_lower
        return ~expr if negate else expr


# -----------------------------------------------------------------------------
# 2. Fast Perspective Engine
# -----------------------------------------------------------------------------

class FastPerspectiveEngine:
    def __init__(self, rules_path: str = "rules.json", database_loader=None):
        self.compiled_modifiers: Dict[str, CompiledModifier] = {}
        self.perspectives: Dict[int, List[CompiledRule]] = {}
        self.default_modifiers: List[str] = []
        self.modifier_overrides: Dict[str, List[str]] = {}
        
        if database_loader is None:
            from database_loader import MockDatabaseLoader
            database_loader = MockDatabaseLoader()
        self.database_loader = database_loader
        
        self._load_rules_from_json(rules_path)

    def _load_rules_from_json(self, rules_path: str):
        try:
            with open(rules_path, "r") as f: rules_data = json.load(f)
        except FileNotFoundError:
            self._load_mock_configurations()
            return

        # Store required_columns per perspective for table determination
        self.perspective_required_columns = {}

        # Handle both formats: dict (old test format) and list (live system format)
        perspectives_data = rules_data.get("perspectives", {})
        if isinstance(perspectives_data, list):
            # Live system format: list of perspective objects
            for p_def in perspectives_data:
                pid = p_def.get("id")
                if pid is None or not p_def.get("is_active", True):
                    continue
                rules = []
                raw_rules = p_def.get("rules", [])
                perspective_required_cols = {}

                for i, r_def in enumerate(raw_rules):
                    # Parse criteria if it's a JSON string
                    criteria_raw = r_def.get("criteria", {})
                    if isinstance(criteria_raw, str):
                        parsed_criteria = json.loads(criteria_raw)
                    else:
                        parsed_criteria = criteria_raw

                    # Extract required_columns if present (live format)
                    if 'required_columns' in parsed_criteria:
                        req_cols = parsed_criteria['required_columns']
                        if isinstance(req_cols, dict):
                            for table, cols in req_cols.items():
                                if table not in perspective_required_cols:
                                    perspective_required_cols[table] = []
                                for col in cols:
                                    if col not in perspective_required_cols[table]:
                                        perspective_required_cols[table].append(col)

                    # Extract the actual criteria (without required_columns)
                    criteria = {k: v for k, v in parsed_criteria.items() if k != 'required_columns'}

                    rules.append(CompiledRule(
                        expr=None, apply_to=r_def.get("apply_to", "both"), name=f"rule_{i}",
                        condition_for_next_rule=r_def.get("condition_for_next_rule", "And" if i < len(raw_rules)-1 else None),
                        criteria=criteria, is_scaling_rule=bool(r_def.get("is_scaling_rule", False)),
                        scale_factor=r_def.get("scale_factor", 1.0)
                    ))

                self.perspectives[int(pid)] = rules
                if perspective_required_cols:
                    self.perspective_required_columns[int(pid)] = perspective_required_cols
        else:
            # Old test format: dict with perspective IDs as keys
            for pid_str, p_def in perspectives_data.items():
                rules = []
                raw_rules = p_def.get("rules", [])
                perspective_required_cols = {}

                for i, r_def in enumerate(raw_rules):
                    # Parse criteria if it's a JSON string
                    criteria_raw = r_def.get("criteria", {})
                    if isinstance(criteria_raw, str):
                        parsed_criteria = json.loads(criteria_raw)
                    else:
                        parsed_criteria = criteria_raw

                    # Extract required_columns if present (live format)
                    if 'required_columns' in parsed_criteria:
                        req_cols = parsed_criteria['required_columns']
                        if isinstance(req_cols, dict):
                            for table, cols in req_cols.items():
                                if table not in perspective_required_cols:
                                    perspective_required_cols[table] = []
                                for col in cols:
                                    if col not in perspective_required_cols[table]:
                                        perspective_required_cols[table].append(col)

                    # Extract the actual criteria (without required_columns)
                    criteria = {k: v for k, v in parsed_criteria.items() if k != 'required_columns'}

                    rules.append(CompiledRule(
                        expr=None, apply_to=r_def.get("apply_to", "both"), name=f"rule_{i}",
                        condition_for_next_rule=r_def.get("condition_for_next_rule", "And" if i < len(raw_rules)-1 else None),
                        criteria=criteria, is_scaling_rule=r_def.get("is_scaling_rule", False),
                        scale_factor=r_def.get("scale_factor", 1.0)
                    ))

                self.perspectives[int(pid_str)] = rules
                if perspective_required_cols:
                    self.perspective_required_columns[int(pid_str)] = perspective_required_cols

        for name, m_def in rules_data.get("modifiers", {}).items():
            m_type_full = m_def.get("type", "PreProcessing")
            m_type = "PostProcessing" if any(x in m_type_full for x in ["PostProcessing", "TradeCash", "SimulatedCash"]) else "Scaling" if "Scaling" in m_type_full else "PreProcessing"

            rule_def = m_def.get("rule", {})
            if rule_def is None:
                rule_def = {}

            # Parse modifier criteria if it's a JSON string
            criteria_raw = rule_def.get("criteria", {})
            parsed_criteria = json.loads(criteria_raw) if isinstance(criteria_raw, str) else criteria_raw

            self.compiled_modifiers[name] = CompiledModifier(
                expr=None, apply_to=rule_def.get("apply_to", "both"), name=name, modifier_type=m_type,
                rule_result_operator=m_def.get("rule_result_operator", "and") if m_type == "PostProcessing" else None,
                criteria=parsed_criteria
            )

        self.default_modifiers = rules_data.get("default_modifiers", [])
        self.modifier_overrides = rules_data.get("modifier_overrides", {})

    def _load_mock_configurations(self):
        # Mock Config with CORRECT Table Metadata for Auto-Detector
        self.perspective_required_columns = {}
        self.compiled_modifiers = {
            "exclude_simulated_trades": CompiledModifier(expr=pl.col("position_source_type_id")!=10, apply_to="both", name="x_sim", modifier_type="PreProcessing", criteria={"column": "position_source_type_id", "operator_type": "!=", "value": 10, "table_name": "INSTRUMENT_CATEGORIZATION"}),
            "exclude_trade_cash": CompiledModifier(expr=pl.col("liquidity_type_id")!=6, apply_to="both", name="x_cash", modifier_type="PreProcessing", criteria={"column": "liquidity_type_id", "operator_type": "!=", "value": 6, "table_name": "INSTRUMENT_CATEGORIZATION"}),
            "exclude_perspective_level_simulated_cash": CompiledModifier(
                expr=~((pl.col("position_source_type_id")==10)&(pl.col("liquidity_type_id")==5)),
                apply_to="both", name="x_p_sim_cash", modifier_type="PostProcessing", rule_result_operator="or",
                criteria={"or": [{"column": "position_source_type_id", "operator_type": "!=", "value": 10, "table_name": "INSTRUMENT_CATEGORIZATION"}, {"column": "liquidity_type_id", "operator_type": "!=", "value": 5, "table_name": "INSTRUMENT_CATEGORIZATION"}]}
            ),
            "exclude_other_net_assets": CompiledModifier(expr=pl.col("liquidity_type_id")!=2, apply_to="both", name="x_ona", modifier_type="PreProcessing", criteria={"column": "liquidity_type_id", "operator_type": "!=", "value": 2, "table_name": "INSTRUMENT_CATEGORIZATION"}),
            "exclude_class_positions": CompiledModifier(expr=pl.col("is_class_position")!=True, apply_to="both", name="x_class", modifier_type="PreProcessing", criteria={"column": "is_class_position", "operator_type": "!=", "value": True, "table_name": "position_data"}),
            "exclude_blocked_positions": CompiledModifier(expr=pl.col("position_blocking_type_id").is_null(), apply_to="both", name="x_blocked", modifier_type="PreProcessing", criteria={"column": "position_blocking_type_id", "operator_type": "IsNull", "table_name": "position_data"}),
            "exclude_simulated_cash": CompiledModifier(
                expr=~((pl.col("position_source_type_id")==10)&(pl.col("liquidity_type_id")==5)),
                apply_to="both", name="x_sim_cash", modifier_type="PreProcessing",
                criteria={"and": [{"column": "position_source_type_id", "operator_type": "!=", "value": 10, "table_name": "INSTRUMENT_CATEGORIZATION"}, {"column": "liquidity_type_id", "operator_type": "!=", "value": 5, "table_name": "INSTRUMENT_CATEGORIZATION"}]}
            ),
            "include_trade_cash_within_perspective": CompiledModifier(
                expr=(pl.col("position_source_type_id")==10)&(pl.col("liquidity_type_id")==6), apply_to="both", name="inc_trade_cash", modifier_type="PostProcessing", rule_result_operator="or",
                criteria={"and": [{"column": "position_source_type_id", "operator_type": "=", "value": 10, "table_name": "INSTRUMENT_CATEGORIZATION"}, {"column": "liquidity_type_id", "operator_type": "=", "value": 6, "table_name": "INSTRUMENT_CATEGORIZATION"}]}
            ),
            "include_all_trade_cash": CompiledModifier(
                expr=(pl.col("position_source_type_id")==10)&(pl.col("liquidity_type_id")==6), apply_to="both", name="inc_all_trade_cash", modifier_type="PostProcessing", rule_result_operator="or",
                criteria={"and": [{"column": "position_source_type_id", "operator_type": "=", "value": 10, "table_name": "INSTRUMENT_CATEGORIZATION"}, {"column": "liquidity_type_id", "operator_type": "=", "value": 6, "table_name": "INSTRUMENT_CATEGORIZATION"}]}
            ),
            "include_simulated_cash": CompiledModifier(
                expr=(pl.col("position_source_type_id")==10)&(pl.col("liquidity_type_id")==5), apply_to="both", name="inc_sim_cash", modifier_type="PostProcessing", rule_result_operator="or",
                criteria={"and": [{"column": "position_source_type_id", "operator_type": "=", "value": 10, "table_name": "INSTRUMENT_CATEGORIZATION"}, {"column": "liquidity_type_id", "operator_type": "=", "value": 5, "table_name": "INSTRUMENT_CATEGORIZATION"}]}
            ),
            "scale_holdings_to_100_percent": CompiledModifier(expr=None, apply_to="holding", name="scale_h", modifier_type="Scaling", criteria={}),
            "scale_lookthroughs_to_100_percent": CompiledModifier(expr=None, apply_to="lookthrough", name="scale_l", modifier_type="Scaling", criteria={})
        }
        self.perspectives = {
            123: [
                CompiledRule(expr=pl.col("asset_class")!="Cash", apply_to="both", name="x_cash", criteria={"column": "asset_class", "operator_type": "!=", "value": "Cash", "table_name": "INSTRUMENT"}),
                CompiledRule(expr=~pl.col("instrument_id").is_in([666, 777]), apply_to="both", name="x_sanctioned", criteria={"column": "instrument_id", "operator_type": "NotIn", "value": [666, 777]})
            ]
        }
        self.modifier_overrides = {
            "exclude_simulated_trades": ["include_all_trade_cash", "include_trade_cash_within_perspective"],
            "exclude_simulated_cash": ["exclude_perspective_level_simulated_cash", "include_simulated_cash"],
            "include_all_trade_cash": ["exclude_perspective_level_simulated_cash"],
            "include_trade_cash_within_perspective": ["exclude_perspective_level_simulated_cash"],
            "exclude_trade_cash": ["exclude_perspective_level_simulated_cash"]
        }

    def _determine_required_tables(self, configs: Dict[str, Any]) -> Dict[str, List[str]]:
        requirements = {}
        all_p_ids = set()
        all_mods = set(self.default_modifiers)

        for perspectives in configs.values():
            for pid, mods in perspectives.items():
                all_p_ids.add(int(pid))
                if mods: all_mods.update(mods)

        # Extract tables from required_columns (live format)
        for pid in all_p_ids:
            if pid in self.perspective_required_columns:
                for table, cols in self.perspective_required_columns[pid].items():
                    # Map old names
                    table = table.replace('InstrumentInput', 'position_data')
                    if table.lower() != 'position_data':
                        if table not in requirements:
                            requirements[table] = ['instrument_id']
                        for col in cols:
                            if col.lower() != 'instrument_id' and col not in requirements[table]:
                                requirements[table].append(col)

        def extract(criteria):
            if not criteria: return
            if "and" in criteria: [extract(c) for c in criteria["and"]]
            elif "or" in criteria: [extract(c) for c in criteria["or"]]
            elif "not" in criteria: extract(criteria["not"])
            else:
                tbl = criteria.get('table_name', 'position_data')
                col = criteria.get('column')

                if tbl != 'position_data':
                    if tbl not in requirements: requirements[tbl] = ['instrument_id']
                    if col and col not in requirements[tbl]: requirements[tbl].append(col)
                if isinstance(criteria.get('value'), dict): extract(criteria.get('value'))

        for pid in all_p_ids:
            for r in self.perspectives.get(pid, []): extract(r.criteria)
        for m_name in all_mods:
            if m_name in self.compiled_modifiers: extract(self.compiled_modifiers[m_name].criteria)

        return requirements

    # -------------------------------------------------------------------------
    # 3. Data Loading (Robust)
    # -------------------------------------------------------------------------
    def _build_lazy_dataframes(self, input_json, tables_required, weight_labels):
        pos_rows, lt_rows = [], []
        
        for key, value in input_json.items():
            if not isinstance(value, dict) or "position_type" not in value: continue
            container, pos_type = key, value["position_type"]
            
            if "positions" in value:
                for pid, attrs in value["positions"].items():
                    pos_rows.append({**attrs, "identifier": pid, "container": container, "position_type": pos_type, "record_type": "position"})
            
            for lt_key, lt_data in value.items():
                if "lookthrough" in lt_key and isinstance(lt_data, dict):
                    for lid, attrs in lt_data.items():
                        lt_rows.append({**attrs, "identifier": lid, "container": container, "position_type": pos_type, "record_type": lt_key})

        if not pos_rows: return pl.LazyFrame(), pl.LazyFrame()

        pos_lf = pl.LazyFrame(pos_rows, infer_schema_length=None)
        
        if lt_rows:
            lt_lf = pl.LazyFrame(lt_rows, infer_schema_length=None)
        else:
            # Create empty schema with all required columns for unpivot operation
            empty_schema = {
                "identifier": pl.Utf8,
                "instrument_identifier": pl.Int64,
                "parent_instrument_id": pl.Int64,
                "sub_portfolio_id": pl.Utf8,
                "instrument_id": pl.Int64,
                "container": pl.Utf8,
                "record_type": pl.Utf8,
                "position_type": pl.Utf8
            }
            # Add weight columns
            for w in weight_labels:
                empty_schema[w] = pl.Float64
            lt_lf = pl.LazyFrame(schema=empty_schema)

        pos_cols = pos_lf.collect_schema().names()
        pos_lf = pos_lf.with_columns([
            pl.col("instrument_identifier").alias("instrument_id"),
            pl.col("sub_portfolio_id").fill_null("default").cast(pl.Utf8) if "sub_portfolio_id" in pos_cols else pl.lit("default").alias("sub_portfolio_id")
        ])
        
        if lt_rows:
            lt_cols = lt_lf.collect_schema().names()
            lt_lf = lt_lf.with_columns([
                pl.col("instrument_identifier").alias("instrument_id"),
                pl.col("parent_instrument_id").cast(pl.Int64).fill_null(INT_NULL),
                pl.col("sub_portfolio_id").fill_null("default").cast(pl.Utf8) if "sub_portfolio_id" in lt_cols else pl.lit("default").alias("sub_portfolio_id")
            ])

        def enrich_and_fill(lf, is_empty):
            if is_empty: return lf
            lf = lf.with_columns(cs.numeric().exclude(weight_labels).fill_null(INT_NULL))
            for col, dtype in lf.collect_schema().items():
                if col not in weight_labels and dtype in [pl.Float32, pl.Float64]:
                    lf = lf.with_columns(pl.col(col).fill_null(FLOAT_NULL))
            return lf

        pos_lf = enrich_and_fill(pos_lf, False)
        lt_lf = enrich_and_fill(lt_lf, not lt_rows)

        if tables_required:
            p_ids = pos_lf.select('instrument_id')
            l_ids = lt_lf.select('instrument_id') if lt_rows else pl.LazyFrame(schema={'instrument_id': pl.Int64})
            unique_ids = pl.concat([p_ids, l_ids]).unique().collect().to_series().to_list()
            
            ref_tables = self._load_reference_tables(unique_ids, input_json.get('ed', '2024-01-01'), tables_required)
            
            for tbl_lf in ref_tables.values():
                pos_lf = pos_lf.join(tbl_lf, on='instrument_id', how='left')
                if lt_rows: lt_lf = lt_lf.join(tbl_lf, on='instrument_id', how='left')
        else:
            ids = pos_lf.select('instrument_id').unique().collect().to_series().to_list()
            ed = input_json.get('ed', '2024-01-01')
            mock_ref = self.database_loader.load_reference_table(ids, 'INSTRUMENT_CATEGORIZATION', ['liquidity_type_id', 'position_source_type_id'], ed=ed).lazy()
            pos_lf = pos_lf.join(mock_ref, on='instrument_id', how='left')
            if lt_rows: lt_lf = lt_lf.join(mock_ref, on='instrument_id', how='left')

        return pos_lf, lt_lf

    def _load_reference_tables(self, id_list, ed, reqs):
        refs = {}
        reqs = dict(reqs)
        if 'INSTRUMENT_CATEGORIZATION' not in reqs: reqs['INSTRUMENT_CATEGORIZATION'] = ['liquidity_type_id', 'position_source_type_id']
        else: reqs['INSTRUMENT_CATEGORIZATION'] = list(set(reqs['INSTRUMENT_CATEGORIZATION'] + ['liquidity_type_id', 'position_source_type_id']))

        for tbl, cols in reqs.items():
            db_cols = [c for c in cols if c != 'instrument_id']
            if tbl == 'INSTRUMENT': refs[tbl] = self.database_loader.load_reference_table(id_list, tbl, db_cols).lazy()
            elif tbl == 'INSTRUMENT_CATEGORIZATION': refs[tbl] = self.database_loader.load_reference_table(id_list, tbl, db_cols, ed=ed).lazy()
        return refs

    # -------------------------------------------------------------------------
    # 4. Processing Engine (Split Architecture - Corrected)
    # -------------------------------------------------------------------------
    def process(self, input_json: Dict[str, Any]) -> Dict[str, Any]:
        configs = input_json.get("perspective_configurations", {})
        for p_map in configs.values():
            for pid, mods in p_map.items():
                continue
                # if mods is None: p_map[pid] = ['exclude_perspective_level_simulated_cash']
                # elif 'exclude_perspective_level_simulated_cash' not in mods: mods.append('exclude_perspective_level_simulated_cash')

        reqs = self._determine_required_tables(configs)
        pos_weights = input_json.get("position_weight_labels", ["weight"])
        lt_weights = input_json.get("lookthrough_weight_labels", ["weight"])
        
        pos_lf, lt_lf = self._build_lazy_dataframes(input_json, reqs, pos_weights + lt_weights)
        
        results = {}
        verbose = input_json.get("verbose_output", True)

        for config_name, perspectives in configs.items():
            results[config_name] = self._process_split_architecture(
                pos_lf.clone(), lt_lf.clone(), perspectives, pos_weights, lt_weights, verbose
            )
            
        return {"perspective_configurations": results}

    def _process_split_architecture(self, pos_lf, lt_lf, perspectives, pos_weights, lt_weights, verbose):
        # 1. Process Positions (Factors)
        # No .is_empty() checks needed here. LazyFrames handle empty flows automatically.
        final_positions, removed_positions = self._apply_factor_masks(pos_lf, perspectives, pos_weights, "position")

        # 2. Cascade Removal (Semi-Join)
        # We build the join graph regardless of data presence.
        valid_parents = final_positions.select(["perspective_id", "instrument_id", "sub_portfolio_id"]).unique()
        
        processed_lt, rem_lt = self._apply_factor_masks(lt_lf, perspectives, lt_weights, "lookthrough")
        
        final_lookthroughs = processed_lt.join(
            valid_parents,
            left_on=["perspective_id", "parent_instrument_id", "sub_portfolio_id"],
            right_on=["perspective_id", "instrument_id", "sub_portfolio_id"],
            how="semi"
        )
        
        # 3. Rescaling
        rescale_pos_pids = [int(p) for p, m in perspectives.items() if "scale_holdings_to_100_percent" in self._apply_overrides(m)]
        rescale_lt_pids = [int(p) for p, m in perspectives.items() if "scale_lookthroughs_to_100_percent" in self._apply_overrides(m)]

        # Rescale Positions
        if rescale_pos_pids:
            # We construct the graph blindly. If data is empty, result is empty.
            # Explicitly rename columns to avoid suffix ambiguity
            pos_sums = final_positions.select(
                ["perspective_id", "container", "sub_portfolio_id"] + pos_weights
            ).group_by(["perspective_id", "container", "sub_portfolio_id"]).sum()

            # Rename position sum columns explicitly
            for w in pos_weights:
                pos_sums = pos_sums.rename({w: f"{w}_pos_sum"})

            # Sum Essential Lookthroughs
            ess_sums = final_lookthroughs.filter(
                pl.col("record_type") == "essential_lookthroughs"
            ).select(
                ["perspective_id", "container", "sub_portfolio_id"] + pos_weights
            ).group_by(["perspective_id", "container", "sub_portfolio_id"]).sum()

            # Rename essential lookthrough sum columns explicitly
            for w in pos_weights:
                ess_sums = ess_sums.rename({w: f"{w}_ess_sum"})

            # Join with explicit column names
            final_positions = final_positions.join(
                pos_sums,
                on=["perspective_id", "container", "sub_portfolio_id"],
                how="left"
            ).join(
                ess_sums,
                on=["perspective_id", "container", "sub_portfolio_id"],
                how="left"
            )

            for w in pos_weights:
                # Now we know exact column names
                denom_expr = pl.col(f"{w}_pos_sum").fill_null(0.0) + pl.col(f"{w}_ess_sum").fill_null(0.0)

                final_positions = final_positions.with_columns(
                    pl.when(pl.col("perspective_id").is_in(rescale_pos_pids))
                      .then(pl.col(w) / denom_expr)
                      .otherwise(pl.col(w))
                      .alias(w)
                )

            # Cleanup - drop the explicitly named sum columns
            cols_to_drop = [f"{w}_pos_sum" for w in pos_weights] + [f"{w}_ess_sum" for w in pos_weights]
            final_positions = final_positions.drop(cols_to_drop)

        # Rescale Lookthroughs
        if rescale_lt_pids:
            for w in lt_weights:
                total = pl.col(w).sum().over(["perspective_id", "parent_instrument_id", "sub_portfolio_id", "record_type"])
                final_lookthroughs = final_lookthroughs.with_columns(
                    pl.when(pl.col("perspective_id").is_in(rescale_lt_pids))
                      .then(pl.col(w) / total)
                      .otherwise(pl.col(w))
                      .alias(w)
                )

        # 4. Output (Triggers execution)
        # We collect here. If any DF is empty, the output formatter handles it.
        return self._vectorized_output_format(
            final_positions.collect(), 
            final_lookthroughs.collect(),
            removed_positions.collect() if verbose else None,
            rem_lt.collect() if verbose else None,
            pos_weights, lt_weights
        )

    def _apply_factor_masks(self, lf, perspectives, weights, mode):
        # Removed .is_empty check. We just build the graph.
        factor_exprs = []
        p_ids = sorted([int(k) for k in perspectives.keys()])

        for p_id in p_ids:
            mods = perspectives.get(str(p_id)) or perspectives.get(p_id) or []
            active_mods = self._apply_overrides(list(set(mods + self.default_modifiers)))
            
            keep_expr = self._build_filter_logic(p_id, active_mods, weights, lf, mode)
            
            scale_factor = pl.lit(1.0)
            for r in self.perspectives.get(p_id, []):
                if r.is_scaling_rule:
                    should_apply = True
                    if r.apply_to == "holding" and mode != "position": should_apply = False
                    if r.apply_to == "reference" and mode == "position": should_apply = False
                    
                    if should_apply:
                        crit_expr = RuleEvaluator.evaluate_criteria(r.criteria, p_id, lf) if r.criteria else pl.lit(True)
                        scale_factor = pl.when(crit_expr).then(scale_factor * r.scale_factor).otherwise(scale_factor)

            factor_exprs.append(
                pl.when(keep_expr).then(scale_factor).otherwise(pl.lit(None)).alias(f"fp_{p_id}")
            )

        available_weights = [w for w in weights]
        id_cols = ["identifier", "container", "record_type", "instrument_id", "sub_portfolio_id"]
        if mode == "lookthrough": id_cols.append("parent_instrument_id")
        
        lf_wide = lf.with_columns(factor_exprs)
        
        lf_long = lf_wide.unpivot(
            on=[f"fp_{p}" for p in p_ids],
            index=id_cols + available_weights,
            variable_name="temp_pid",
            value_name="factor"
        ).with_columns(
            pl.col("temp_pid").str.strip_prefix("fp_").cast(pl.Int64).alias("perspective_id")
        ).drop("temp_pid")

        kept = lf_long.drop_nulls(subset=["factor"])
        kept = kept.with_columns([(pl.col(w) * pl.col("factor")).alias(w) for w in available_weights])
        
        removed = lf_long.filter(pl.col("factor").is_null())
        
        return kept, removed

    def _build_filter_logic(self, pid, mods, weights, lf, mode):
        expr = pl.lit(True)
        for w in weights: expr = expr & pl.col(w).is_not_null()
        
        for m in mods:
            if m in self.compiled_modifiers:
                mod = self.compiled_modifiers[m]
                if mod.modifier_type == "PreProcessing":
                    if (mod.apply_to == "holding" and mode != "position") or (mod.apply_to == "reference" and mode == "position"): continue
                    if mod.criteria: expr = expr & RuleEvaluator.evaluate_criteria(mod.criteria, pid, lf)

        rule_expr = None
        for i, rule in enumerate(self.perspectives.get(pid, [])):
            if rule.is_scaling_rule: continue
            if (rule.apply_to == "holding" and mode != "position") or (rule.apply_to == "reference" and mode == "position"): continue
            
            curr = RuleEvaluator.evaluate_criteria(rule.criteria, pid, lf) if rule.criteria else (rule.expr if rule.expr is not None else pl.lit(True))
            
            if rule_expr is None: rule_expr = curr
            else:
                prev = self.perspectives.get(pid)[i-1]
                rule_expr = rule_expr | curr if prev.condition_for_next_rule == "Or" else rule_expr & curr
        
        if rule_expr is None: rule_expr = pl.lit(True)
        
        for m in mods:
            if m in self.compiled_modifiers:
                mod = self.compiled_modifiers[m]
                if mod.modifier_type == "PostProcessing":
                    if (mod.apply_to == "holding" and mode != "position") or (mod.apply_to == "reference" and mode == "position"): continue
                    if mod.criteria:
                        savior = RuleEvaluator.evaluate_criteria(mod.criteria, pid, lf)
                        rule_expr = rule_expr | savior if mod.rule_result_operator == "or" else rule_expr & savior

        return expr & rule_expr

    def _apply_overrides(self, mods):
        final = mods.copy()
        for m in mods:
            if m in self.modifier_overrides:
                for bad in self.modifier_overrides[m]:
                    if bad in final: final.remove(bad)
        return final

    def _vectorized_output_format(self, pos_df, lt_df, rem_pos, rem_lt, pos_w, lt_w):
        results = {}
        if pos_df.is_empty(): return results

        # Partition by Perspective AND Container to avoid filters
        p_parts = pos_df.partition_by(["perspective_id", "container"], as_dict=True, include_key=False)
        
        l_parts = {}
        if not lt_df.is_empty():
            l_parts = lt_df.partition_by(["perspective_id", "container"], as_dict=True, include_key=False)

        rp_parts = {}
        if rem_pos is not None and not rem_pos.is_empty():
            rp_parts = rem_pos.partition_by(["perspective_id", "container"], as_dict=True, include_key=False)

        rl_parts = {}
        if rem_lt is not None and not rem_lt.is_empty():
            rl_parts = rem_lt.partition_by(["perspective_id", "container"], as_dict=True, include_key=False)

        for (pid, cont), c_df in p_parts.items():
            p_key = str(pid)
            if p_key not in results: results[p_key] = {}
            data = {}
            
            cols = ["identifier"] + [w for w in pos_w if w in c_df.columns]
            data["positions"] = {d.pop("identifier"): d for d in c_df.select(cols).to_dicts()}
            
            # Lookthroughs (tuple lookup)
            if (pid, cont) in l_parts:
                l_cont = l_parts[(pid, cont)]
                lt_types = l_cont["record_type"].unique().to_list()
                for ltype in lt_types:
                    sub = l_cont.filter(pl.col("record_type") == ltype)
                    cols = ["identifier"] + [w for w in lt_w if w in sub.columns]
                    data[ltype] = {d.pop("identifier"): d for d in sub.select(cols).to_dicts()}

            # Removals (tuple lookup)
            rem_p = rp_parts.get((pid, cont))
            rem_l = rl_parts.get((pid, cont))
            
            if (rem_p is not None and not rem_p.is_empty()) or (rem_l is not None and not rem_l.is_empty()):
                data["removed_positions_weight_summary"] = self._build_removal_summary(
                    rem_p if rem_p is not None else pl.DataFrame(),
                    rem_l if rem_l is not None else pl.DataFrame(),
                    pos_w, lt_w
                )

            results[p_key][cont] = data
        return results

    def _build_removal_summary(self, rem_p, rem_l, pos_w, lt_w):
        summary = {}
        if not rem_p.is_empty():
            cols = ["identifier"] + [w for w in pos_w if w in rem_p.columns]
            summary["positions"] = {d.pop("identifier"): d for d in rem_p.select(cols).to_dicts()}
        
        if not rem_l.is_empty():
            for ltype in rem_l["record_type"].unique():
                sub = rem_l.filter(pl.col("record_type") == ltype)
                grp = sub.group_by("parent_instrument_id").agg([pl.sum(w) for w in lt_w if w in sub.columns])
                dct = {}
                for d in grp.to_dicts():
                    pid = d.pop("parent_instrument_id")
                    pkey = str(int(pid)) if isinstance(pid, float) and pid==int(pid) else str(pid)
                    dct[pkey] = d
                summary[ltype] = dct
        return summary

def main():
    with open("mock_input.json", "r") as f: input_data = json.load(f)
    engine = FastPerspectiveEngine()
    result = engine.process(input_data)
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    main()