"""
Perspective Engine - Main orchestrator for the perspective processing pipeline.

Implements the 9-step flow:
1. Load Perspective
2. Load Modifiers
3. Parse Criteria & Required Data
4. Load Reference Data
5. Build DataFrames (Position + Lookthrough)
6. Precompute Nested Criteria
7. Build Plan (keep/scale expressions)
8. Collect All (materialize)
9. Format Output
"""

from typing import Dict, List, Optional, Any

import polars as pl

from perspective_service.core.configuration_manager import ConfigurationManager
from perspective_service.core.data_ingestion import DataIngestion
from perspective_service.core.perspective_processor import PerspectiveProcessor
from perspective_service.core.output_formatter import OutputFormatter
from perspective_service.core.rule_evaluator import RuleEvaluator
from perspective_service.database.loaders.database_loader import DatabaseLoader
from perspective_service.models.rule import Rule
from perspective_service.utils.constants import INT_NULL


class PerspectiveEngine:
    """Main orchestrator for perspective processing."""

    def __init__(self,
                 connection_string: Optional[str] = None,
                 system_version_timestamp: Optional[str] = None):
        """
        Initialize the PerspectiveEngine.

        Args:
            connection_string: ODBC connection string for database access
            system_version_timestamp: Optional timestamp for temporal queries
        """
        self.system_version_timestamp = system_version_timestamp

        # Create DatabaseLoader if connection string provided
        if connection_string:
            self.db_loader = DatabaseLoader(connection_string)
        else:
            self.db_loader = None

        # Step 1 & 2: Load Perspectives and Modifiers
        self.config = ConfigurationManager(self.db_loader, system_version_timestamp)

    def process(self,
                input_json: Dict,
                perspective_configs: Dict[str, Dict[str, List[str]]],
                position_weights: List[str],
                lookthrough_weights: List[str],
                verbose: bool = False,
                flatten_response: bool = False) -> Dict:
        """
        Process input data through perspective rules.

        Args:
            input_json: Raw input data containing positions and lookthroughs
            perspective_configs: {config_name: {perspective_id: [modifier_names]}}
            position_weights: List of weight column names for positions
            lookthrough_weights: List of weight column names for lookthroughs
            verbose: Whether to include removal summary in output
            flatten_response: Whether to flatten output to columnar format

        Returns:
            Formatted output dictionary
        """
        # Parse custom perspective rules from input JSON (if any)
        self._parse_custom_perspectives(input_json)

        # Step 3: Determine required tables based on perspectives and modifiers
        required_tables = self._determine_required_tables(perspective_configs)

        # Step 4 & 5: Load reference data and build dataframes
        positions_lf, lookthroughs_lf = DataIngestion.build_dataframes(
            input_json,
            required_tables,
            position_weights + lookthrough_weights,
            self.db_loader
        )

        if positions_lf.collect_schema().names() == []:
            return {"perspective_configurations": {}}

        # Step 6: Precompute nested criteria values
        precomputed_values = self._precompute_nested_criteria(
            positions_lf, lookthroughs_lf, perspective_configs
        )

        # Step 7: Build perspective plan (keep/scale expressions)
        processor = PerspectiveProcessor(self.config)
        positions_lf, lookthroughs_lf, metadata_map = processor.build_perspective_plan(
            positions_lf,
            lookthroughs_lf,
            perspective_configs,
            position_weights,
            lookthrough_weights,
            precomputed_values
        )

        # Step 8: Collect all (materialize LazyFrames)
        if lookthroughs_lf is not None:
            positions_df, lookthroughs_df = pl.collect_all([
                positions_lf,
                lookthroughs_lf
            ])
        else:
            positions_df = positions_lf.collect()
            lookthroughs_df = pl.DataFrame()

        # Step 9: Format output
        return OutputFormatter.format_output(
            positions_df,
            lookthroughs_df,
            metadata_map,
            position_weights,
            lookthrough_weights,
            verbose,
            flatten_response
        )

    def _determine_required_tables(self,
                                   perspective_configs: Dict[str, Dict[str, List[str]]]) -> Dict[str, List[str]]:
        """
        Determine which database tables are needed based on perspective rules and modifiers.

        Returns:
            Dict of {table_name: [column_names]}
        """
        required_tables: Dict[str, List[str]] = {}

        # Collect all perspective IDs being used
        perspective_ids = set()
        all_modifier_names = set()

        for config_name, perspective_map in perspective_configs.items():
            for perspective_id, modifier_names in perspective_map.items():
                perspective_ids.add(int(perspective_id))
                if modifier_names:
                    all_modifier_names.update(modifier_names)

        # Add default modifiers
        all_modifier_names.update(self.config.default_modifiers)

        # Get required columns from perspectives
        for pid in perspective_ids:
            if pid in self.config.required_columns_by_perspective:
                for table, columns in self.config.required_columns_by_perspective[pid].items():
                    if table not in required_tables:
                        required_tables[table] = []
                    for col in columns:
                        if col not in required_tables[table]:
                            required_tables[table].append(col)

        # Get required columns from modifiers
        modifier_columns = self.config.get_modifier_required_columns(list(all_modifier_names))
        for table, columns in modifier_columns.items():
            if table == 'position_data':
                # Skip - position_data comes from input JSON
                continue
            if table not in required_tables:
                required_tables[table] = []
            for col in columns:
                if col not in required_tables[table]:
                    required_tables[table].append(col)

        return required_tables

    def _precompute_nested_criteria(self,
                                    positions_lf: pl.LazyFrame,
                                    lookthroughs_lf: pl.LazyFrame,
                                    perspective_configs: Dict) -> Dict[str, Any]:
        """
        Precompute values for nested criteria (like ANY_OF lookups).

        Returns:
            Dict of precomputed values for use in rule evaluation
        """
        precomputed = {}

        # Collect all perspective IDs
        perspective_ids = set()
        for config_name, perspective_map in perspective_configs.items():
            for perspective_id in perspective_map.keys():
                perspective_ids.add(int(perspective_id))

        # Check each perspective's rules for nested criteria
        for perspective_id in perspective_ids:
            rules = self.config.perspectives.get(perspective_id, [])
            for rule in rules:
                self._extract_precomputed_values(
                    rule.criteria, perspective_id, positions_lf, lookthroughs_lf, precomputed
                )

        # Check modifiers for nested criteria
        for modifier in self.config.modifiers.values():
            if modifier.criteria:
                self._extract_precomputed_values(
                    modifier.criteria, None, positions_lf, lookthroughs_lf, precomputed
                )

        return precomputed

    def _extract_precomputed_values(self,
                                    criteria: Dict,
                                    perspective_id: Optional[int],
                                    positions_lf: pl.LazyFrame,
                                    lookthroughs_lf: pl.LazyFrame,
                                    precomputed: Dict):
        """Extract and compute values for nested criteria."""
        if not isinstance(criteria, dict):
            return

        operator_type = criteria.get('operator_type')

        # Handle ANY_OF with nested query
        if operator_type == 'ANY_OF':
            value = criteria.get('value')
            if isinstance(value, dict) and 'column' in value:
                nested_column = value['column']
                cache_key = f"any_of_{nested_column}"

                if cache_key not in precomputed:
                    # Get unique values from positions
                    try:
                        values = (positions_lf
                                  .select(pl.col(nested_column))
                                  .filter(pl.col(nested_column) != INT_NULL)
                                  .unique()
                                  .collect()
                                  .to_series()
                                  .to_list())
                        precomputed[cache_key] = values
                    except Exception:
                        precomputed[cache_key] = []

        # Handle NONE_OF with nested query
        elif operator_type == 'NONE_OF':
            value = criteria.get('value')
            if isinstance(value, dict) and 'column' in value:
                nested_column = value['column']
                cache_key = f"none_of_{nested_column}"

                if cache_key not in precomputed:
                    try:
                        values = (positions_lf
                                  .select(pl.col(nested_column))
                                  .filter(pl.col(nested_column) != INT_NULL)
                                  .unique()
                                  .collect()
                                  .to_series()
                                  .to_list())
                        precomputed[cache_key] = values
                    except Exception:
                        precomputed[cache_key] = []

        # Handle AND/OR - recurse into sub-criteria
        elif operator_type in ['AND', 'OR']:
            sub_criteria = criteria.get('criteria', [])
            for sub in sub_criteria:
                self._extract_precomputed_values(
                    sub, perspective_id, positions_lf, lookthroughs_lf, precomputed
                )

    def _parse_custom_perspectives(self, input_json: Dict) -> None:
        """
        Parse custom perspective rules from input JSON.

        Custom perspective IDs MUST be negative to distinguish them from
        database-loaded perspectives.

        Args:
            input_json: Raw input data that may contain 'custom_perspective_rules'
        """
        custom_rules = input_json.get('custom_perspective_rules', {})
        if not custom_rules:
            return

        # Validate all IDs are negative
        for pid in custom_rules.keys():
            if int(pid) > 0:
                raise ValueError(
                    "Custom Perspective Rule IDs MUST be negative to separate them from real Perspective IDs"
                )

        # Add each custom perspective
        for pid_str, perspective_data in custom_rules.items():
            pid = int(pid_str)

            # rules is REQUIRED
            if 'rules' not in perspective_data:
                raise ValueError(f"Custom perspective {pid} is missing required 'rules' field")
            rules = perspective_data['rules']

            if not rules:
                continue

            # Track required columns for this custom perspective
            required_columns: Dict[str, List[str]] = {}

            # Convert to internal Rule format
            internal_rules = []
            for i, rule in enumerate(rules):
                # criteria is REQUIRED
                if 'criteria' not in rule:
                    raise ValueError(f"Custom perspective {pid} rule {i} is missing required 'criteria' field")
                criteria = rule['criteria']

                # apply_to is REQUIRED
                if 'apply_to' not in rule:
                    raise ValueError(f"Custom perspective {pid} rule {i} is missing required 'apply_to' field")

                # Extract required_columns for tracking, then remove from criteria
                if 'required_columns' in criteria:
                    for table, columns in criteria['required_columns'].items():
                        if table not in required_columns:
                            required_columns[table] = []
                        for col in columns:
                            if col not in required_columns[table]:
                                required_columns[table].append(col)

                # Remove required_columns metadata from criteria (not needed for evaluation)
                clean_criteria = {k: v for k, v in criteria.items()
                                  if k != 'required_columns'}

                is_scaling_rule = rule.get('is_scaling_rule', False)
                if is_scaling_rule and 'scale_factor' not in rule:
                    raise ValueError(f"Custom perspective {pid} rule {i} is a scaling rule but missing 'scale_factor'")

                internal_rules.append(Rule(
                    name=f"custom_rule_{pid}_{i}",
                    apply_to=rule['apply_to'],
                    criteria=clean_criteria,
                    condition_for_next_rule=rule.get('condition_for_next_rule'),
                    is_scaling_rule=is_scaling_rule,
                    scale_factor=(rule['scale_factor'] / 100) if is_scaling_rule else 1.0
                ))

            self.config.perspectives[pid] = internal_rules

            # Track required columns for this custom perspective
            if required_columns:
                self.config.required_columns_by_perspective[pid] = required_columns
