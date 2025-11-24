import polars as pl
import polars.selectors as cs
import json
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple, Set, Union

# -----------------------------------------------------------------------------
# 1. Constants & Models
# -----------------------------------------------------------------------------

INT_NULL = -2147483648
FLOAT_NULL = -2147483648.49438

@dataclass
class CompiledRule:
    name: str
    apply_to: str
    criteria: Optional[Dict[str, Any]] = None
    expr: Optional[pl.Expr] = None
    condition_for_next_rule: Optional[str] = None
    is_scaling_rule: bool = False
    scale_factor: float = 1.0

@dataclass
class CompiledModifier:
    name: str
    apply_to: str
    modifier_type: str
    criteria: Optional[Dict[str, Any]] = None
    expr: Optional[pl.Expr] = None
    rule_result_operator: Optional[str] = None

# -----------------------------------------------------------------------------
# 2. Rule Logic Engine
# -----------------------------------------------------------------------------

class RuleEvaluator:
    @staticmethod
    def _build_like_expr(col: str, val: str, negate: bool) -> pl.Expr:
        val_lower = val.lower()
        expr = pl.col(col).str.to_lowercase()
        if val.startswith("%") and val.endswith("%"):
            expr = expr.str.contains(val_lower[1:-1])
        elif val.endswith("%"):
            expr = expr.str.starts_with(val_lower[:-1])
        elif val.startswith("%"):
            expr = expr.str.ends_with(val_lower[1:])
        else:
            expr = expr == val_lower
        return ~expr if negate else expr

    @classmethod
    def get_operator_expr(cls, op: str, col: str, val: Any) -> pl.Expr:
        if op == "=" or op == "==": return pl.col(col) == val
        if op == "!=": return pl.col(col) != val
        if op == ">": return pl.col(col) > val
        if op == "<": return pl.col(col) < val
        if op == ">=": return pl.col(col) >= val
        if op == "<=": return pl.col(col) <= val
        if op == "In": return pl.col(col).is_in(val)
        if op == "NotIn": return ~pl.col(col).is_in(val)
        if op == "IsNull": return pl.col(col).is_null()
        if op == "IsNotNull": return pl.col(col).is_not_null()
        if op == "Between": return (pl.col(col) >= val[0]) & (pl.col(col) <= val[1])
        if op == "NotBetween": return (pl.col(col) < val[0]) | (pl.col(col) > val[1])
        if op == "Like": return cls._build_like_expr(col, val, False)
        if op == "NotLike": return cls._build_like_expr(col, val, True)
        return pl.lit(True)

    @classmethod
    def evaluate(cls, criteria: Dict[str, Any], perspective_id: Optional[int] = None, 
                 precomputed_values: Dict[str, List[Any]] = None) -> pl.Expr:
        if "and" in criteria:
            sub = criteria["and"]
            if not sub: return pl.lit(True)
            expr = cls.evaluate(sub[0], perspective_id, precomputed_values)
            for crit in sub[1:]: expr = expr & cls.evaluate(crit, perspective_id, precomputed_values)
            return expr
        if "or" in criteria:
            sub = criteria["or"]
            if not sub: return pl.lit(False)
            expr = cls.evaluate(sub[0], perspective_id, precomputed_values)
            for crit in sub[1:]: expr = expr | cls.evaluate(crit, perspective_id, precomputed_values)
            return expr
        if "not" in criteria:
            return ~cls.evaluate(criteria["not"], perspective_id, precomputed_values)

        column = criteria.get("column")
        operator = criteria.get("operator_type")
        value = criteria.get("value")

        if not column or not operator: return pl.lit(True)

        if perspective_id is not None and isinstance(value, str) and 'perspective_id' in value:
            value = value.replace('perspective_id', str(perspective_id))

        if operator in ["In", "NotIn"] and isinstance(value, dict):
            if precomputed_values is None: return pl.lit(True)
            criteria_key = json.dumps(value, sort_keys=True)
            matching_values = precomputed_values.get(criteria_key, [])
            if operator == "In": return pl.col(column).is_in(matching_values)
            return ~pl.col(column).is_in(matching_values)

        parsed_value = cls._parse_value(value, operator)
        return cls.get_operator_expr(operator, column, parsed_value)

    @staticmethod
    def _parse_value(value: Any, operator: str) -> Any:
        if operator in ["IsNull", "IsNotNull"]: return None
        if operator in ["In", "NotIn"]:
            if isinstance(value, str):
                items = [item.strip() for item in value.strip("[]").split(",")]
                return [int(x) if x.lstrip('-').isdigit() else x for x in items]
            return value if isinstance(value, list) else [value]
        if operator in ["Between", "NotBetween"]:
            if isinstance(value, str) and 'fncriteria:' in value:
                try:
                    parts = value.replace('fncriteria:', '').split(':')
                    return [float(p) if p.replace('.','',1).isdigit() else p for p in parts]
                except ValueError: return [0, 0]
            return value if isinstance(value, list) and len(value) == 2 else [0, 0]
        return value

# -----------------------------------------------------------------------------
# 3. Data Ingestion
# -----------------------------------------------------------------------------

class DataFrameFactory:
    @staticmethod
    def build_lazy_frames(input_json: Dict, tables_required: Dict, weight_labels: List[str], db_loader) -> Tuple[pl.LazyFrame, pl.LazyFrame]:
        pos_rows, lt_rows = [], []
        for key, value in input_json.items():
            if not isinstance(value, dict) or "position_type" not in value: continue
            container_info = {"container": key, "position_type": value["position_type"]}
            if "positions" in value:
                for pid, attrs in value["positions"].items():
                    pos_rows.append({**attrs, **container_info, "identifier": pid, "record_type": "position"})
            for lt_key, lt_data in value.items():
                if "lookthrough" in lt_key and isinstance(lt_data, dict):
                    for lid, attrs in lt_data.items():
                        lt_rows.append({**attrs, **container_info, "identifier": lid, "record_type": lt_key})

        if not pos_rows: return pl.LazyFrame(), pl.LazyFrame()

        pos_lf = pl.LazyFrame(pos_rows, infer_schema_length=None)
        lt_lf = DataFrameFactory._create_lt_frame(lt_rows)
        pos_lf = DataFrameFactory._standardize_cols(pos_lf)
        lt_lf = DataFrameFactory._standardize_cols(lt_lf)
        pos_lf = DataFrameFactory._enrich_nulls(pos_lf, weight_labels)
        lt_lf = DataFrameFactory._enrich_nulls(lt_lf, weight_labels)

        if tables_required:
            pos_lf, lt_lf = DataFrameFactory._join_reference_data(pos_lf, lt_lf, tables_required, db_loader, input_json.get('ed', '2024-01-01'))
        return pos_lf, lt_lf

    @staticmethod
    def _create_lt_frame(rows):
        if rows: return pl.LazyFrame(rows, infer_schema_length=None)
        return pl.LazyFrame(schema={"instrument_identifier": pl.Int64, "parent_instrument_id": pl.Int64, "sub_portfolio_id": pl.Utf8, "instrument_id": pl.Int64})

    @staticmethod
    def _standardize_cols(lf: pl.LazyFrame) -> pl.LazyFrame:
        cols = lf.collect_schema().names()
        return lf.with_columns([
            pl.col("instrument_identifier").alias("instrument_id"),
            (pl.col("sub_portfolio_id").fill_null("default").cast(pl.Utf8) if "sub_portfolio_id" in cols else pl.lit("default").alias("sub_portfolio_id")),
            (pl.col("parent_instrument_id").cast(pl.Int64).fill_null(INT_NULL) if "parent_instrument_id" in cols else pl.lit(INT_NULL).alias("parent_instrument_id"))
        ])

    @staticmethod
    def _enrich_nulls(lf: pl.LazyFrame, exclude_cols: List[str]) -> pl.LazyFrame:
        if not lf.collect_schema().names(): return lf
        lf = lf.with_columns(cs.numeric().exclude(exclude_cols).fill_null(INT_NULL))
        float_fills = [pl.col(col).fill_null(FLOAT_NULL) for col, dtype in lf.collect_schema().items() if col not in exclude_cols and dtype in [pl.Float32, pl.Float64]]
        if float_fills: lf = lf.with_columns(float_fills)
        return lf

    @staticmethod
    def _join_reference_data(pos_lf, lt_lf, tables_required, db_loader, ed):
        p_ids = pos_lf.select('instrument_id')
        l_ids = lt_lf.select('instrument_id') if lt_lf.collect_schema().names() else pl.LazyFrame(schema={'instrument_id': pl.Int64})
        unique_ids = pl.concat([p_ids, l_ids]).unique().collect().to_series().to_list()
        reqs = dict(tables_required)
        base_cols = ['liquidity_type_id', 'position_source_type_id']
        if 'INSTRUMENT_CATEGORIZATION' not in reqs: reqs['INSTRUMENT_CATEGORIZATION'] = base_cols
        else: reqs['INSTRUMENT_CATEGORIZATION'] = list(set(reqs['INSTRUMENT_CATEGORIZATION'] + base_cols))

        for tbl, cols in reqs.items():
            db_cols = [c for c in cols if c != 'instrument_id']
            ref_lf = pl.LazyFrame()
            if tbl == 'INSTRUMENT': ref_lf = db_loader.load_reference_table(unique_ids, tbl, db_cols).lazy()
            elif tbl == 'INSTRUMENT_CATEGORIZATION': ref_lf = db_loader.load_reference_table(unique_ids, tbl, db_cols, ed=ed).lazy()
            if ref_lf.collect_schema().names():
                pos_lf = pos_lf.join(ref_lf, on='instrument_id', how='left')
                if lt_lf.collect_schema().names(): lt_lf = lt_lf.join(ref_lf, on='instrument_id', how='left')
        return pos_lf, lt_lf

# -----------------------------------------------------------------------------
# 4. Configuration Manager
# -----------------------------------------------------------------------------

class RuleConfigLoader:
    def __init__(self, rules_path: str):
        self.perspectives: Dict[int, List[CompiledRule]] = {}
        self.modifiers: Dict[str, CompiledModifier] = {}
        self.defaults: List[str] = []
        self.overrides: Dict[str, List[str]] = {}
        self.perspective_required_columns: Dict[int, Dict[str, List[str]]] = {}
        self._load(rules_path)

    def _load(self, path):
        try:
            with open(path, "r") as f: data = json.load(f)
        except FileNotFoundError:
            self._load_mock()
            return
        self._parse_perspectives(data.get("perspectives", {}))
        self._parse_modifiers(data.get("modifiers", {}))
        self.defaults = data.get("default_modifiers", [])
        self.overrides = data.get("modifier_overrides", {})

    def _parse_perspectives(self, data):
        items = data.items() if isinstance(data, dict) else [(p.get("id"), p) for p in data if p.get("id")]
        for pid_raw, p_def in items:
            pid = int(pid_raw)
            if not p_def.get("is_active", True): continue
            rules, perspective_reqs = [], {}
            raw_rules = p_def.get("rules", [])
            for i, r_def in enumerate(raw_rules):
                raw_crit = r_def.get("criteria", {})
                crit_dict = json.loads(raw_crit) if isinstance(raw_crit, str) else raw_crit
                if 'required_columns' in crit_dict:
                    for tbl, cols in crit_dict['required_columns'].items():
                        if tbl not in perspective_reqs: perspective_reqs[tbl] = []
                        for c in cols:
                            if c not in perspective_reqs[tbl]: perspective_reqs[tbl].append(c)
                crit = self._clean_criteria(crit_dict)
                rules.append(CompiledRule(
                    name=f"rule_{i}", apply_to=r_def.get("apply_to", "both"),
                    condition_for_next_rule=r_def.get("condition_for_next_rule", "And" if i < len(raw_rules)-1 else None),
                    criteria=crit, is_scaling_rule=bool(r_def.get("is_scaling_rule", False)),
                    scale_factor=r_def.get("scale_factor", 1.0)
                ))
            self.perspectives[pid] = rules
            if perspective_reqs: self.perspective_required_columns[pid] = perspective_reqs

    def _parse_modifiers(self, data):
        for name, m_def in data.items():
            m_type_raw = m_def.get("type", "PreProcessing")
            if any(x in m_type_raw for x in ["PostProcessing", "TradeCash", "SimulatedCash"]): m_type = "PostProcessing"
            elif "Scaling" in m_type_raw: m_type = "Scaling"
            else: m_type = "PreProcessing"
            rule_def = m_def.get("rule", {}) or {}
            criteria_raw = rule_def.get("criteria", {})
            parsed_criteria = json.loads(criteria_raw) if isinstance(criteria_raw, str) else criteria_raw
            self.modifiers[name] = CompiledModifier(
                name=name, apply_to=rule_def.get("apply_to", "both"), modifier_type=m_type,
                rule_result_operator=m_def.get("rule_result_operator", "and"), criteria=self._clean_criteria(parsed_criteria)
            )

    def _clean_criteria(self, criteria):
        if isinstance(criteria, str): criteria = json.loads(criteria)
        if not isinstance(criteria, dict): return criteria
        return {k: v for k, v in criteria.items() if k != 'required_columns'}

    def _load_mock(self):
        self.perspective_required_columns, self.modifiers, self.perspectives, self.overrides = {}, {}, {}, {}

# -----------------------------------------------------------------------------
# 5. HYBRID Orchestrator (Original Calc + Vectorized Shredder + Timing)
# -----------------------------------------------------------------------------

class FastPerspectiveEngine:
    def __init__(self, rules_path: str = "rules.json", database_loader=None):
        if database_loader is None:
            class MockLoader:
                def load_reference_table(self, ids, tbl, cols, ed=None): return pl.DataFrame({"instrument_id": ids})
            database_loader = MockLoader()
        self.db_loader = database_loader
        self.config = RuleConfigLoader(rules_path)

    @contextmanager
    def timer(self, label: str):
        start = time.time()
        try: yield
        finally:
            end = time.time()
            print(f"[DEBUG] {label}: {end - start:.4f}s")

    def process(self, input_json: Dict[str, Any]) -> Dict[str, Any]:
        with self.timer("TOTAL PROCESS EXECUTION"):
            # 1. Setup
            with self.timer("1. Setup & Config"):
                configs = input_json.get("perspective_configurations", {})
                pos_weights = input_json.get("position_weight_labels", ["weight"])
                lt_weights = input_json.get("lookthrough_weight_labels", ["weight"])
                verbose = input_json.get("verbose_output", True)
                reqs = self._determine_required_tables(configs)
            
            # 2. Build Base Data
            with self.timer("2. Data Ingestion (Factory)"):
                pos_lf, lt_lf = DataFrameFactory.build_lazy_frames(input_json, reqs, pos_weights + lt_weights, self.db_loader)
            
            with self.timer("3. Precomputing Nested Criteria"):
                precomputed_map = self._precompute_nested_criteria(pos_lf, configs)

            # 3. EXECUTE SUPER WIDE PIPELINE (Fastest Method)
            with self.timer("4. Building Super Wide Graph"):
                final_pos, final_lt, meta_map = self._build_super_wide_plan(pos_lf, lt_lf, configs, pos_weights, lt_weights, precomputed_map)

            # 4. Single Materialization
            with self.timer("5. Polars Materialization (collect)"):
                if final_lt is not None:
                     pos_df, lt_df = pl.collect_all([final_pos, final_lt])
                else:
                     pos_df, lt_df = final_pos.collect(), pl.DataFrame()

            # 5. Shred Output (VECTORIZED REPLACEMENT - FASTEST SHREDDING)
            with self.timer("6. Shredding Output (Vectorized)"):
                return self._shred_output(pos_df, lt_df, meta_map, pos_weights, lt_weights, verbose)

    # --- Core Graph Building Logic (Unchanged - Super Fast) ---
    def _build_super_wide_plan(self, pos_lf, lt_lf, configs, pos_weights, lt_weights, precomputed_map):
        all_factor_exprs_pos, all_factor_exprs_lt = [], []
        all_rescale_aggs_pos, all_rescale_aggs_lt = [], []
        all_final_scale_exprs_pos, all_final_scale_exprs_lt = [], []
        meta_map, required_lt_sum_names = {}, set()
        has_lt = bool(lt_lf.collect_schema().names())

        for config_name, perspective_map in configs.items():
            meta_map[config_name] = {}
            p_ids = sorted([int(k) for k in perspective_map.keys()])
            for pid in p_ids:
                unique_col = f"f_{config_name}_{pid}"
                meta_map[config_name][pid] = unique_col
                mod_names = perspective_map.get(str(pid)) or perspective_map.get(pid) or []
                active_mods = self._filter_overridden_mods(mod_names)
                
                keep = self._build_keep_expression(pid, active_mods, "position", precomputed_map)
                scale = self._build_scale_expression(pid, "position", precomputed_map)
                all_factor_exprs_pos.append(pl.when(keep).then(scale).otherwise(pl.lit(None)).alias(unique_col))

                if has_lt:
                    keep_l = self._build_keep_expression(pid, active_mods, "lookthrough", precomputed_map)
                    scale_l = self._build_scale_expression(pid, "lookthrough", precomputed_map)
                    all_factor_exprs_lt.append(pl.when(keep_l).then(scale_l).otherwise(pl.lit(None)).alias(unique_col))

        pos_lf = pos_lf.with_columns(all_factor_exprs_pos)
        if has_lt:
            lt_lf = lt_lf.with_columns(all_factor_exprs_lt)
            all_unique_cols = [c for m in meta_map.values() for c in m.values()]
            lt_lf = self._sync_lookthroughs_super_wide(lt_lf, pos_lf, all_unique_cols)

        for config_name, perspective_map in configs.items():
            rescale_p_ids = self._get_rescale_ids(perspective_map, "scale_holdings_to_100_percent")
            rescale_l_ids = self._get_rescale_ids(perspective_map, "scale_lookthroughs_to_100_percent")
            
            for pid in rescale_p_ids:
                col = meta_map[config_name][pid]
                for w in pos_weights:
                    all_rescale_aggs_pos.append((pl.col(w) * pl.col(col)).sum().alias(f"sum_{w}_{col}_pos"))
                    required_lt_sum_names.add(f"sum_{w}_{col}_lt")
                
                w_key = pos_weights[0]
                denom = pl.col(f"sum_{w_key}_{col}_pos").fill_null(0) + pl.col(f"sum_{w_key}_{col}_lt").fill_null(0)
                all_final_scale_exprs_pos.append(pl.when(denom != 0).then(pl.col(col) / denom).otherwise(pl.col(col)).alias(col))

            if has_lt:
                for pid in rescale_l_ids:
                    col = meta_map[config_name][pid]
                    for w in lt_weights:
                        all_rescale_aggs_lt.append((pl.col(w) * pl.col(col)).sum().alias(f"sum_{w}_{col}_lt"))
                    w_key = lt_weights[0]
                    total = (pl.col(w_key) * pl.col(col)).sum().over(["container", "parent_instrument_id", "sub_portfolio_id", "record_type"])
                    all_final_scale_exprs_lt.append(pl.when(total != 0).then(pl.col(col) / total).otherwise(pl.col(col)).alias(col))

        if all_rescale_aggs_pos:
            pos_sums = pos_lf.group_by(["container", "sub_portfolio_id"]).agg(all_rescale_aggs_pos)
            if has_lt and all_rescale_aggs_lt:
                lt_sums = lt_lf.filter(pl.col("record_type") == "essential_lookthroughs").group_by(["container", "sub_portfolio_id"]).agg(all_rescale_aggs_lt)
            else:
                lt_sums = pos_sums.select(["container", "sub_portfolio_id"])

            existing_lt_cols = set(lt_sums.collect_schema().names())
            missing_lt_zeros = [pl.lit(0.0).alias(n) for n in required_lt_sum_names if n not in existing_lt_cols]
            if missing_lt_zeros: lt_sums = lt_sums.with_columns(missing_lt_zeros)

            pos_lf = pos_lf.join(pos_sums, on=["container", "sub_portfolio_id"], how="left").join(lt_sums, on=["container", "sub_portfolio_id"], how="left")
            pos_lf = pos_lf.with_columns(all_final_scale_exprs_pos)
        
        if has_lt and all_final_scale_exprs_lt:
            lt_lf = lt_lf.with_columns(all_final_scale_exprs_lt)

        return pos_lf, (lt_lf if has_lt else None), meta_map

    # --- REPLACED SHREDDER (Vectorized from Wide Format) ---
    def _shred_output(self, pos_df, lt_df, meta_map, pos_weights, lt_weights, verbose):
        results = {}
        map_rows = []
        for config, p_map in meta_map.items():
            if not p_map: continue
            results[config] = {} 
            for pid, col in p_map.items():
                map_rows.append({"col_name": col, "config": config, "pid": str(pid)})
                results[config][str(pid)] = {}

        if not map_rows: return {"perspective_configurations": results}

        map_df = pl.DataFrame(map_rows)
        factor_cols = [r["col_name"] for r in map_rows]

        self._process_shred_batch(pos_df, "positions", map_df, factor_cols, pos_weights, results, "identifier")
        if not lt_df.is_empty():
            self._process_shred_batch(lt_df, "lookthrough", map_df, factor_cols, lt_weights, results, "identifier")

        if verbose:
            self._add_fast_removal_summary(pos_df, lt_df, map_df, pos_weights, lt_weights, results)
        return {"perspective_configurations": results}

    def _process_shred_batch(self, df, mode, map_df, factor_cols, weights, results_dict, id_col):
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
        group_keys = ["config", "pid", "container"]
        if mode == "lookthrough": group_keys.append("record_type")

        grouped = melted.with_columns(weight_exprs).group_by(group_keys).agg(pl.struct(struct_cols).alias("data_items"))

        for row in grouped.iter_rows(named=True):
            cfg, pid, cont = row["config"], row["pid"], row["container"]
            items = row["data_items"]
            formatted_data = {item[id_col]: {k: v for k, v in item.items() if k != id_col} for item in items}
            target = results_dict[cfg][pid].setdefault(cont, {})
            
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
                grp = melted.group_by(["config", "pid", "container"]).agg(pl.struct(struct_cols).alias("items"))
                for row in grp.iter_rows(named=True):
                    d = {x.pop("identifier"): x for x in row["items"]}
                    t = results[row["config"]][row["pid"]].setdefault(row["container"], {})
                    t.setdefault("removed_positions_weight_summary", {}).setdefault("positions", d)
            else:
                if "parent_instrument_id" in melted.columns:
                     melted = melted.with_columns(pl.col("parent_instrument_id").cast(pl.Utf8))
                     agg_exprs = [pl.col(w).sum() for w in valid_w]
                     grp = melted.group_by(["config", "pid", "container", "record_type", "parent_instrument_id"]).agg(agg_exprs)
                     struct_cols = ["parent_instrument_id"] + valid_w
                     final_grp = grp.group_by(["config", "pid", "container", "record_type"]).agg(pl.struct(struct_cols).alias("items"))
                     for row in final_grp.iter_rows(named=True):
                         d = {x.pop("parent_instrument_id"): x for x in row["items"]}
                         t = results[row["config"]][row["pid"]].setdefault(row["container"], {})
                         t.setdefault("removed_positions_weight_summary", {}).setdefault(row["record_type"], d)

        process_removals(pos_df, pos_w, "positions")
        if not lt_df.is_empty(): process_removals(lt_df, lt_w, "lookthrough")

    def _sync_lookthroughs_super_wide(self, lt_lf, pos_lf, all_unique_cols):
        parent_factors = pos_lf.select(["instrument_id", "sub_portfolio_id"] + all_unique_cols).unique(subset=["instrument_id", "sub_portfolio_id"])
        rename_map = {c: f"parent_{c}" for c in all_unique_cols}
        parent_factors = parent_factors.rename(rename_map)
        lt_synced = lt_lf.join(parent_factors, left_on=["parent_instrument_id", "sub_portfolio_id"], right_on=["instrument_id", "sub_portfolio_id"], how="left")
        final_exprs = [pl.when(pl.col(f"parent_{c}").is_null()).then(pl.lit(None)).otherwise(pl.col(c)).alias(c) for c in all_unique_cols]
        return lt_synced.with_columns(final_exprs)

    def _build_keep_expression(self, pid, mods, mode, precomputed_map) -> pl.Expr:
        expr = pl.lit(True)
        for m_name in mods:
            mod = self.config.modifiers.get(m_name)
            if mod and mod.modifier_type == "PreProcessing" and self._is_applicable(mod.apply_to, mode):
                expr &= RuleEvaluator.evaluate(mod.criteria, pid, precomputed_map)
        
        rule_expr = None
        rules = self.config.perspectives.get(pid, [])
        for i, rule in enumerate(rules):
            if rule.is_scaling_rule: continue
            if not self._is_applicable(rule.apply_to, mode): continue
            curr_expr = RuleEvaluator.evaluate(rule.criteria, pid, precomputed_map)
            if rule_expr is None: rule_expr = curr_expr
            else:
                prev = rules[i-1]
                rule_expr = rule_expr | curr_expr if prev.condition_for_next_rule == "Or" else rule_expr & curr_expr
        if rule_expr is None: rule_expr = pl.lit(True)
        
        for m_name in mods:
            mod = self.config.modifiers.get(m_name)
            if mod and mod.modifier_type == "PostProcessing" and self._is_applicable(mod.apply_to, mode):
                savior = RuleEvaluator.evaluate(mod.criteria, pid, precomputed_map)
                rule_expr = rule_expr | savior if mod.rule_result_operator == "or" else rule_expr & savior
        return expr & rule_expr

    def _build_scale_expression(self, pid, mode, precomputed_map) -> pl.Expr:
        scale_factor = pl.lit(1.0)
        for rule in self.config.perspectives.get(pid, []):
            if rule.is_scaling_rule and self._is_applicable(rule.apply_to, mode):
                crit = RuleEvaluator.evaluate(rule.criteria, pid, precomputed_map)
                scale_factor = pl.when(crit).then(scale_factor * rule.scale_factor).otherwise(scale_factor)
        return scale_factor

    def _determine_required_tables(self, configs: Dict[str, Any]) -> Dict[str, List[str]]:
        requirements = {}
        all_p_ids, all_mods = set(), set(self.config.defaults)
        for perspectives in configs.values():
            for pid, mods in perspectives.items():
                all_p_ids.add(int(pid))
                if mods: all_mods.update(mods)
        for pid in all_p_ids:
            if pid in self.config.perspective_required_columns:
                for table, cols in self.config.perspective_required_columns[pid].items():
                    table = table.replace('InstrumentInput', 'position_data')
                    if table.lower() != 'position_data':
                        if table not in requirements: requirements[table] = ['instrument_id']
                        for col in cols:
                            if col.lower() != 'instrument_id' and col not in requirements[table]: requirements[table].append(col)
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
            for r in self.config.perspectives.get(pid, []): extract(r.criteria)
        for m_name in all_mods:
            if m_name in self.config.modifiers: extract(self.config.modifiers[m_name].criteria)
        return requirements

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
                    inner_expr = RuleEvaluator.evaluate(val, None, None)
                    query = (lf.filter(inner_expr).select(pl.col(target_col)).drop_nulls().unique())
                    nested_queries[key] = query
        for p_map in configs.values():
            for pid in p_map.keys():
                for rule in self.config.perspectives.get(int(pid), []):
                    if rule.criteria: find_nested(rule.criteria)
                mods = p_map[pid] or []
                for m_name in list(set(mods + self.config.defaults)):
                    if m_name in self.config.modifiers: find_nested(self.config.modifiers[m_name].criteria)
        if not nested_queries: return {}
        keys = list(nested_queries.keys())
        results = pl.collect_all(list(nested_queries.values()))
        return {k: res.to_series().to_list() for k, res in zip(keys, results)}

    def _get_rescale_ids(self, perspective_map, modifier_key):
        return [int(p) for p, m in perspective_map.items() if modifier_key in self._filter_overridden_mods(m or [])]

    def _is_applicable(self, rule_apply_to, mode):
        rule_apply_to = rule_apply_to.lower()
        if rule_apply_to == "both": return True
        if rule_apply_to == "holding" and mode == "position": return True
        if (rule_apply_to == "lookthrough" or rule_apply_to == "reference") and mode == "lookthrough": return True
        return False

    def _filter_overridden_mods(self, mods):
        final = set(mods + self.config.defaults)
        for m in list(final):
            if m in self.config.overrides:
                for bad in self.config.overrides[m]:
                    if bad in final: final.remove(bad)
        return list(final)

if __name__ == "__main__":
    with open("mock_input.json", "r") as f: input_data = json.load(f)
    engine = FastPerspectiveEngine()
    result = engine.process(input_data)
    print(json.dumps(result, indent=2, default=str))