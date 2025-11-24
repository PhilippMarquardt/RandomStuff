"""
EXTREME PERFORMANCE VERSION - DEBUG INSTRUMENTED
Architecture: SPLIT DATAFRAMES + WIDE FACTOR COLUMNS + VECTORIZED SHREDDING
"""

import polars as pl
import polars.selectors as cs
import json
import time
from contextlib import contextmanager
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
    def evaluate_criteria(cls, criteria: Dict[str, Any], perspective_id: Optional[int] = None, 
                          precomputed_values: Dict[str, List[Any]] = None) -> pl.Expr:
        
        if "and" in criteria:
            sub = criteria["and"]
            if not sub: return pl.lit(True)
            expr = cls.evaluate_criteria(sub[0], perspective_id, precomputed_values)
            for crit in sub[1:]: expr = expr & cls.evaluate_criteria(crit, perspective_id, precomputed_values)
            return expr

        if "or" in criteria:
            sub = criteria["or"]
            if not sub: return pl.lit(False)
            expr = cls.evaluate_criteria(sub[0], perspective_id, precomputed_values)
            for crit in sub[1:]: expr = expr | cls.evaluate_criteria(crit, perspective_id, precomputed_values)
            return expr

        if "not" in criteria:
            return ~cls.evaluate_criteria(criteria["not"], perspective_id, precomputed_values)

        column = criteria.get("column")
        operator_type = criteria.get("operator_type")
        value = criteria.get("value")

        if not column or not operator_type: return pl.lit(True)

        if perspective_id is not None and isinstance(value, str) and 'perspective_id' in value:
            value = value.replace('perspective_id', str(perspective_id))

        # --- OPTIMIZED LAZY LOOKUP ---
        if operator_type in ["In", "NotIn"] and isinstance(value, dict):
            if precomputed_values is None: return pl.lit(True) # Fallback
            
            criteria_key = json.dumps(value, sort_keys=True)
            matching_values = precomputed_values.get(criteria_key, [])
            
            if operator_type == "In":
                return pl.col(column).is_in(matching_values)
            else: 
                return ~pl.col(column).is_in(matching_values)

        parsed_value = cls._parse_value(value, operator_type)
        op_func = cls.OPERATORS.get(operator_type)
        return op_func(column, parsed_value) if op_func else pl.lit(True)

    @staticmethod
    def _parse_value(value: Any, operator_type: str) -> Any:
        if operator_type in ["IsNull", "IsNotNull"]: return None
        if operator_type in ["In", "NotIn"]:
            if isinstance(value, str):
                items = [item.strip() for item in value.strip("[]").split(",")]
                return [int(x) if x.lstrip('-').isdigit() else x for x in items]
            return value if isinstance(value, list) else [value]
        if operator_type in ["Between", "NotBetween"]:
            if isinstance(value, str) and 'fncriteria:' in value:
                try:
                    parts = value.replace('fncriteria:', '').split(':')
                    return [float(p) if p.replace('.','',1).isdigit() else p for p in parts]
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
            # Placeholder/Mock
            class MockLoader:
                def load_reference_table(self, ids, tbl, cols, ed=None):
                    return pl.DataFrame({"instrument_id": ids})
            database_loader = MockLoader()

        self.database_loader = database_loader
        self._load_rules_from_json(rules_path)

    @contextmanager
    def timer(self, label: str):
        """Simple Context Manager for debugging performance."""
        start = time.time()
        try:
            yield
        finally:
            end = time.time()
            print(f"[DEBUG_WIDE] {label}: {end - start:.4f}s")

    def _load_rules_from_json(self, rules_path: str):
        try:
            with open(rules_path, "r") as f: rules_data = json.load(f)
        except FileNotFoundError:
            self._load_mock_configurations()
            return

        self.perspective_required_columns = {}
        perspectives_data = rules_data.get("perspectives", {})
        
        p_items = []
        if isinstance(perspectives_data, list):
            p_items = [(p.get("id"), p) for p in perspectives_data if p.get("id") is not None]
        else:
            p_items = [(pid, p) for pid, p in perspectives_data.items()]

        for pid_raw, p_def in p_items:
            pid = int(pid_raw)
            if not p_def.get("is_active", True): continue
            
            rules = []
            raw_rules = p_def.get("rules", [])
            perspective_required_cols = {}

            for i, r_def in enumerate(raw_rules):
                criteria_raw = r_def.get("criteria", {})
                parsed_criteria = json.loads(criteria_raw) if isinstance(criteria_raw, str) else criteria_raw

                if 'required_columns' in parsed_criteria:
                    req_cols = parsed_criteria['required_columns']
                    if isinstance(req_cols, dict):
                        for table, cols in req_cols.items():
                            if table not in perspective_required_cols: perspective_required_cols[table] = []
                            for col in cols:
                                if col not in perspective_required_cols[table]: perspective_required_cols[table].append(col)

                criteria = {k: v for k, v in parsed_criteria.items() if k != 'required_columns'}

                rules.append(CompiledRule(
                    expr=None, apply_to=r_def.get("apply_to", "both"), name=f"rule_{i}",
                    condition_for_next_rule=r_def.get("condition_for_next_rule", "And" if i < len(raw_rules)-1 else None),
                    criteria=criteria, is_scaling_rule=bool(r_def.get("is_scaling_rule", False)),
                    scale_factor=r_def.get("scale_factor", 1.0)
                ))

            self.perspectives[pid] = rules
            if perspective_required_cols:
                self.perspective_required_columns[pid] = perspective_required_cols

        for name, m_def in rules_data.get("modifiers", {}).items():
            m_type_full = m_def.get("type", "PreProcessing")
            m_type = "PostProcessing" if any(x in m_type_full for x in ["PostProcessing", "TradeCash", "SimulatedCash"]) else "Scaling" if "Scaling" in m_type_full else "PreProcessing"
            rule_def = m_def.get("rule", {}) or {}

            criteria_raw = rule_def.get("criteria", {})
            parsed_criteria = json.loads(criteria_raw) if isinstance(criteria_raw, str) else criteria_raw
            criteria = {k: v for k, v in parsed_criteria.items() if k != 'required_columns'} if isinstance(parsed_criteria, dict) else parsed_criteria

            self.compiled_modifiers[name] = CompiledModifier(
                expr=None, apply_to=rule_def.get("apply_to", "both"), name=name, modifier_type=m_type,
                rule_result_operator=m_def.get("rule_result_operator", "and") if m_type == "PostProcessing" else None,
                criteria=criteria
            )

        self.default_modifiers = rules_data.get("default_modifiers", [])
        self.modifier_overrides = rules_data.get("modifier_overrides", {})

    def _load_mock_configurations(self):
        self.perspective_required_columns = {}
        self.compiled_modifiers = {}
        self.perspectives = {}
        self.modifier_overrides = {}

    def _determine_required_tables(self, configs: Dict[str, Any]) -> Dict[str, List[str]]:
        requirements = {}
        all_p_ids = set()
        all_mods = set(self.default_modifiers)

        for perspectives in configs.values():
            for pid, mods in perspectives.items():
                all_p_ids.add(int(pid))
                if mods: all_mods.update(mods)

        for pid in all_p_ids:
            if pid in self.perspective_required_columns:
                for table, cols in self.perspective_required_columns[pid].items():
                    table = table.replace('InstrumentInput', 'position_data')
                    if table.lower() != 'position_data':
                        if table not in requirements: requirements[table] = ['instrument_id']
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
    # 3. Data Loading
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
            lt_lf = pl.LazyFrame(schema={"instrument_identifier": pl.Int64, "parent_instrument_id": pl.Int64, "sub_portfolio_id": pl.Utf8, "instrument_id": pl.Int64})

        pos_cols = pos_lf.collect_schema().names()
        pos_lf = pos_lf.with_columns([
            pl.col("instrument_identifier").alias("instrument_id"),
            pl.col("sub_portfolio_id").fill_null("default").cast(pl.Utf8) if "sub_portfolio_id" in pos_cols else pl.lit("default").alias("sub_portfolio_id")
        ])
        
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
    # 4. Processing Engine (WIDE Format Architecture)
    # -------------------------------------------------------------------------
    
    def _precompute_nested_criteria(self, lf: pl.LazyFrame, configs: Dict[str, Any]) -> Dict[str, List[Any]]:
        nested_queries = {}

        def find_nested(criteria):
            if not criteria: return
            if "and" in criteria: [find_nested(c) for c in criteria["and"]]
            elif "or" in criteria: [find_nested(c) for c in criteria["or"]]
            elif "not" in criteria: find_nested(criteria["not"])
            else:
                val = criteria.get("value")
                op = criteria.get("operator_type")
                if op in ["In", "NotIn"] and isinstance(val, dict):
                    key = json.dumps(val, sort_keys=True)
                    target_col = criteria.get("column")
                    inner_expr = RuleEvaluator.evaluate_criteria(val, None, None)
                    
                    query = (
                        lf.filter(inner_expr)
                        .select(pl.col(target_col))
                        .drop_nulls()
                        .unique()
                    )
                    nested_queries[key] = query

        for p_map in configs.values():
            for pid in p_map.keys():
                for rule in self.perspectives.get(int(pid), []):
                    if rule.criteria: find_nested(rule.criteria)
                mods = p_map[pid] or []
                for m_name in list(set(mods + self.default_modifiers)):
                    if m_name in self.compiled_modifiers:
                        find_nested(self.compiled_modifiers[m_name].criteria)

        if not nested_queries: return {}

        keys = list(nested_queries.keys())
        results = pl.collect_all(list(nested_queries.values()))
        
        return {k: res.to_series().to_list() for k, res in zip(keys, results)}

    def process(self, input_json: Dict[str, Any]) -> Dict[str, Any]:
        with self.timer("TOTAL PROCESS EXECUTION"):
            with self.timer("1. Setup & Config"):
                configs = input_json.get("perspective_configurations", {})
                reqs = self._determine_required_tables(configs)
                pos_weights = input_json.get("position_weight_labels", ["weight"])
                lt_weights = input_json.get("lookthrough_weight_labels", ["weight"])
                verbose = input_json.get("verbose_output", True)
            
            with self.timer("2. Data Ingestion (Factory)"):
                pos_lf, lt_lf = self._build_lazy_dataframes(input_json, reqs, pos_weights + lt_weights)
            
            with self.timer("3. Precomputing Nested Criteria"):
                precomputed_map = self._precompute_nested_criteria(pos_lf, configs)

            results = {}
            
            # Note: V9 processes per-config loop, unlike Original which creates one Super-Graph.
            # We will instrument inside the loop to show where time goes.
            for config_name, perspectives in configs.items():
                results[config_name] = self._process_wide_architecture(
                    pos_lf.clone(), lt_lf.clone(), perspectives, 
                    pos_weights, lt_weights, verbose, precomputed_map
                )
            
            return {"perspective_configurations": results}

    def _process_wide_architecture(self, pos_lf, lt_lf, perspectives, pos_weights, lt_weights, verbose, precomputed_map):
        
        # 1. Compute Factors (Wide)
        with self.timer("  > 4. Building Wide Graph"):
            pos_lf_wide, p_cols = self._compute_wide_factors(pos_lf, perspectives, "position", precomputed_map)
            
            lt_lf_wide = pl.LazyFrame()
            if not lt_lf.collect_schema().names():
                 pass 
            else:
                 lt_lf_wide, _ = self._compute_wide_factors(lt_lf, perspectives, "lookthrough", precomputed_map)

            # 2. Cascade Removal (Sync Lookthroughs with Parents)
            if not lt_lf.collect_schema().names():
                 lt_lf_wide = lt_lf 
            else:
                 lt_lf_wide = self._sync_lookthroughs_wide(lt_lf_wide, pos_lf_wide, p_cols)

            # 3. Rescaling
            rescale_pos_pids = [int(p) for p, m in perspectives.items() if "scale_holdings_to_100_percent" in self._apply_overrides(m)]
            rescale_lt_pids = [int(p) for p, m in perspectives.items() if "scale_lookthroughs_to_100_percent" in self._apply_overrides(m)]

            if rescale_pos_pids:
                pos_lf_wide = self._rescale_wide_positions(pos_lf_wide, lt_lf_wide, p_cols, pos_weights, rescale_pos_pids)
            
            if rescale_lt_pids:
                lt_lf_wide = self._rescale_wide_lookthroughs(lt_lf_wide, p_cols, lt_weights, rescale_lt_pids)

        # 4. Collect & Generate Output
        with self.timer("  > 5. Materialization (collect)"):
            pos_df = pos_lf_wide.collect()
            lt_df = lt_lf_wide.collect()

        with self.timer("  > 6. Shredding (Vectorized)"):
            return self._generate_output_from_wide(
                pos_df, lt_df, p_cols, pos_weights, lt_weights, verbose
            )

    def _compute_wide_factors(self, lf, perspectives, mode, precomputed_map):
        factor_exprs = []
        p_ids = sorted([int(k) for k in perspectives.keys()])
        p_cols = []

        for p_id in p_ids:
            mods = perspectives.get(str(p_id)) or perspectives.get(p_id) or []
            active_mods = self._apply_overrides(list(set(mods + self.default_modifiers)))
            
            keep_expr = self._build_filter_logic(p_id, active_mods, [], lf, mode, precomputed_map)
            
            scale_factor = pl.lit(1.0)
            for r in self.perspectives.get(p_id, []):
                if r.is_scaling_rule:
                    should_apply = True
                    if r.apply_to == "holding" and mode != "position": should_apply = False
                    if r.apply_to == "reference" and mode == "position": should_apply = False
                    
                    if should_apply:
                        crit_expr = RuleEvaluator.evaluate_criteria(r.criteria, p_id, precomputed_map)
                        scale_factor = pl.when(crit_expr).then(scale_factor * r.scale_factor).otherwise(scale_factor)

            col_name = f"factor_p{p_id}"
            p_cols.append(col_name)
            
            factor_exprs.append(
                pl.when(keep_expr).then(scale_factor).otherwise(pl.lit(None)).alias(col_name)
            )

        return lf.with_columns(factor_exprs), p_cols

    def _sync_lookthroughs_wide(self, lt_lf, pos_lf, factor_cols):
        parent_factors = pos_lf.select(
            ["instrument_id", "sub_portfolio_id"] + factor_cols
        ).unique(subset=["instrument_id", "sub_portfolio_id"])

        rename_map = {c: f"parent_{c}" for c in factor_cols}
        parent_factors = parent_factors.rename(rename_map)

        lt_synced = lt_lf.join(
            parent_factors,
            left_on=["parent_instrument_id", "sub_portfolio_id"],
            right_on=["instrument_id", "sub_portfolio_id"],
            how="left"
        )

        final_exprs = [
            pl.when(pl.col(f"parent_{c}").is_null())
              .then(pl.lit(None))
              .otherwise(pl.col(c))
              .alias(c)
            for c in factor_cols
        ]
        
        return lt_synced.with_columns(final_exprs)

    def _rescale_wide_positions(self, pos_lf, lt_lf, factor_cols, weights, pids_to_rescale):
        pos_aggs = []
        for pid in pids_to_rescale:
            col = f"factor_p{pid}"
            for w in weights:
                pos_aggs.append((pl.col(w) * pl.col(col)).sum().alias(f"sum_{w}_{col}_pos"))

        pos_sums = pos_lf.group_by(["container", "sub_portfolio_id"]).agg(pos_aggs)

        lt_aggs = []
        for pid in pids_to_rescale:
            col = f"factor_p{pid}"
            for w in weights:
                lt_aggs.append((pl.col(w) * pl.col(col)).sum().alias(f"sum_{w}_{col}_lt"))

        if not lt_lf.collect_schema().names():
            dummy_exprs = [pl.lit(0.0).alias(f"sum_{w}_factor_p{pid}_lt") for pid in pids_to_rescale for w in weights]
            lt_sums = pos_sums.select(["container", "sub_portfolio_id"]).with_columns(dummy_exprs)
        else:
            lt_sums = lt_lf.filter(pl.col("record_type") == "essential_lookthroughs") \
                           .group_by(["container", "sub_portfolio_id"]).agg(lt_aggs)

        pos_lf = pos_lf.join(pos_sums, on=["container", "sub_portfolio_id"], how="left") \
                       .join(lt_sums, on=["container", "sub_portfolio_id"], how="left")

        scale_ops = []
        for pid in pids_to_rescale:
            col = f"factor_p{pid}"
            for w in weights:
                w_key = weights[0]
                denom = pl.col(f"sum_{w_key}_{col}_pos").fill_null(0) + pl.col(f"sum_{w_key}_{col}_lt").fill_null(0)
                
                scale_ops.append(
                    pl.when(denom != 0)
                    .then(pl.col(col) / denom)
                    .otherwise(pl.col(col))
                    .alias(col)
                )
                break 

        return pos_lf.with_columns(scale_ops)

    def _rescale_wide_lookthroughs(self, lt_lf, factor_cols, weights, pids_to_rescale):
        scale_ops = []
        for pid in pids_to_rescale:
            col = f"factor_p{pid}"
            w_key = weights[0]
            total = (pl.col(w_key) * pl.col(col)).sum().over(["container", "parent_instrument_id", "sub_portfolio_id", "record_type"])
            
            scale_ops.append(
                pl.when(total != 0)
                .then(pl.col(col) / total)
                .otherwise(pl.col(col))
                .alias(col)
            )
        return lt_lf.with_columns(scale_ops)

    def _generate_output_from_wide(self, pos_df, lt_df, factor_cols, pos_weights, lt_weights, verbose):
        results = {}
        
        # Prepare map for vectorized shredding
        # Map factor_col -> pid
        col_map_rows = []
        for f_col in factor_cols:
            pid = f_col.replace("factor_p", "")
            col_map_rows.append({"col_name": f_col, "pid": pid})
            results[pid] = {}

        map_df = pl.DataFrame(col_map_rows)

        # Vectorized Processing Positions
        self._process_shred_batch(pos_df, "positions", map_df, factor_cols, pos_weights, results, "identifier")

        # Vectorized Processing Lookthroughs
        if not lt_df.is_empty():
            self._process_shred_batch(lt_df, "lookthrough", map_df, factor_cols, lt_weights, results, "identifier")

        # Verbose Removal (Optimized)
        if verbose:
            self._add_fast_removal_summary(pos_df, lt_df, map_df, pos_weights, lt_weights, results)

        return results

    def _process_shred_batch(self, df, mode, map_df, factor_cols, weights, results_dict, id_col):
        """Vectorized Shredder helper"""
        available_factors = [c for c in factor_cols if c in df.columns]
        if not available_factors: return

        base_cols = [id_col, "container"]
        if mode == "lookthrough": base_cols.append("record_type")
        valid_weights = [w for w in weights if w in df.columns]

        try:
            melted = (
                df.select(base_cols + valid_weights + available_factors)
                .melt(id_vars=base_cols + valid_weights, value_vars=available_factors, variable_name="col_name", value_name="factor")
                .filter(pl.col("factor").is_not_null())
                .join(map_df, on="col_name", how="inner")
            )
        except Exception: return

        if melted.is_empty(): return

        weight_exprs = [(pl.col(w) * pl.col("factor")).alias(w) for w in valid_weights]
        struct_cols = [id_col] + valid_weights
        group_keys = ["pid", "container"]
        if mode == "lookthrough": group_keys.append("record_type")

        grouped = (
            melted.with_columns(weight_exprs)
            .group_by(group_keys)
            .agg(pl.struct(struct_cols).alias("data_items"))
        )

        for row in grouped.iter_rows(named=True):
            pid, cont = row["pid"], row["container"]
            items = row["data_items"]
            formatted_data = {item[id_col]: {k: v for k, v in item.items() if k != id_col} for item in items}
            
            target = results_dict[pid].setdefault(cont, {})
            if mode == "positions": target["positions"] = formatted_data
            else: target[row["record_type"]] = formatted_data

    def _add_fast_removal_summary(self, pos_df, lt_df, map_df, pos_w, lt_w, results):
        def process_removals(df, w_cols, key_type):
            cols = [c for c in map_df["col_name"] if c in df.columns]
            if not cols: return
            
            id_vars = ["identifier", "container", "record_type"]
            if "parent_instrument_id" in df.columns: id_vars.append("parent_instrument_id")
            valid_w = [c for c in w_cols if c in df.columns]
            id_vars.extend(valid_w)

            melted = (
                df.select(id_vars + cols)
                .melt(id_vars=id_vars, value_vars=cols, variable_name="col_name", value_name="factor")
                .filter(pl.col("factor").is_null())
                .join(map_df, on="col_name")
            )
            
            if melted.is_empty(): return

            if key_type == "positions":
                struct_cols = ["identifier"] + valid_w
                grp = melted.group_by(["pid", "container"]).agg(pl.struct(struct_cols).alias("items"))
                for row in grp.iter_rows(named=True):
                    d = {x.pop("identifier"): x for x in row["items"]}
                    t = results[row["pid"]].setdefault(row["container"], {})
                    t.setdefault("removed_positions_weight_summary", {}).setdefault("positions", d)
            else:
                if "parent_instrument_id" in melted.columns:
                     melted = melted.with_columns(pl.col("parent_instrument_id").cast(pl.Utf8))
                     agg_exprs = [pl.col(w).sum() for w in valid_w]
                     grp = melted.group_by(["pid", "container", "record_type", "parent_instrument_id"]).agg(agg_exprs)
                     struct_cols = ["parent_instrument_id"] + valid_w
                     final_grp = grp.group_by(["pid", "container", "record_type"]).agg(pl.struct(struct_cols).alias("items"))
                     for row in final_grp.iter_rows(named=True):
                         d = {x.pop("parent_instrument_id"): x for x in row["items"]}
                         t = results[row["pid"]].setdefault(row["container"], {})
                         t.setdefault("removed_positions_weight_summary", {}).setdefault(row["record_type"], d)

        process_removals(pos_df, pos_w, "positions")
        if not lt_df.is_empty(): process_removals(lt_df, lt_w, "lookthrough")

    def _build_filter_logic(self, pid, mods, weights, lf, mode, precomputed_map):
        expr = pl.lit(True)
        for w in weights: expr = expr & pl.col(w).is_not_null()
        
        for m in mods:
            if m in self.compiled_modifiers:
                mod = self.compiled_modifiers[m]
                if mod.modifier_type == "PreProcessing":
                    if (mod.apply_to == "holding" and mode != "position") or (mod.apply_to == "reference" and mode == "position"): continue
                    if mod.criteria: 
                        expr = expr & RuleEvaluator.evaluate_criteria(mod.criteria, pid, precomputed_map)

        rule_expr = None
        for i, rule in enumerate(self.perspectives.get(pid, [])):
            if rule.is_scaling_rule: continue
            if (rule.apply_to == "holding" and mode != "position") or (rule.apply_to == "reference" and mode == "position"): continue
            
            curr = RuleEvaluator.evaluate_criteria(rule.criteria, pid, precomputed_map) if rule.criteria else (rule.expr if rule.expr is not None else pl.lit(True))
            
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
                        savior = RuleEvaluator.evaluate_criteria(mod.criteria, pid, precomputed_map)
                        rule_expr = rule_expr | savior if mod.rule_result_operator == "or" else rule_expr & savior

        return expr & rule_expr

    def _apply_overrides(self, mods):
        final = mods.copy()
        for m in mods:
            if m in self.modifier_overrides:
                for bad in self.modifier_overrides[m]:
                    if bad in final: final.remove(bad)
        return final

def main():
    with open("mock_input.json", "r") as f: input_data = json.load(f)
    engine = FastPerspectiveEngine()
    result = engine.process(input_data)
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    main()