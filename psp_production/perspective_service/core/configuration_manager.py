"""
Configuration Manager - Manages rules, modifiers, and perspective configurations.
"""

import json
from typing import Dict, List, Optional

from perspective_service.models.rule import Rule
from perspective_service.models.modifier import Modifier
from perspective_service.utils.supported_modifiers import SUPPORTED_MODIFIERS, DEFAULT_MODIFIERS
from perspective_service.database.loaders.perspective_loader import load_perspectives, PerspectiveLoadError


class ConfigurationManager:
    """Manages rules, modifiers, and perspective configurations."""

    def __init__(self, db_connection=None, system_version_timestamp: Optional[str] = None):
        """
        Initialize ConfigurationManager.

        Args:
            db_connection: Database connection (required for production)
            system_version_timestamp: Optional timestamp for temporal queries
        """
        self.perspectives: Dict[int, List[Rule]] = {}
        self.modifiers: Dict[str, Modifier] = {}
        self.default_modifiers: List[str] = list(DEFAULT_MODIFIERS)
        self.modifier_overrides: Dict[str, List[str]] = {}
        self.required_columns_by_perspective: Dict[int, Dict[str, List[str]]] = {}

        self._load_configuration(db_connection, system_version_timestamp)

    def _load_configuration(self, db_connection, system_version_timestamp: Optional[str]):
        """Load configuration - DB only, no JSON fallback."""
        if db_connection is not None:
            db_perspectives = load_perspectives(db_connection, system_version_timestamp)
            self._parse_db_perspectives(db_perspectives)
        else:
            # For testing without DB, allow empty perspectives
            print("Warning: No database connection provided, starting with empty perspectives")

        # Always load hardcoded modifiers
        self._load_hardcoded_modifiers()

    def _parse_db_perspectives(self, db_perspectives: Dict[int, Dict]):
        """Parse perspectives from database format."""
        for perspective_id, p_def in db_perspectives.items():
            if not p_def.get('is_active', True):
                continue
            if not p_def.get('is_supported', True):
                continue

            rules = []
            required_columns = {}

            for idx, rule_def in enumerate(p_def.get('rules', [])):
                criteria = self._parse_criteria(rule_def.get('criteria', {}))

                if 'required_columns' in criteria:
                    req_cols = criteria['required_columns']
                    if isinstance(req_cols, str):
                        req_cols = json.loads(req_cols)
                    self._update_required_columns(required_columns, req_cols)

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

        print(f"Parsed {len(self.perspectives)} perspectives from database")

    def _load_hardcoded_modifiers(self):
        """Load modifiers from hardcoded SUPPORTED_MODIFIERS dict."""
        for name, mod_def in SUPPORTED_MODIFIERS.items():
            modifier = Modifier(
                name=name,
                apply_to=mod_def.get('apply_to', 'both'),
                modifier_type=mod_def.get('type', 'PreProcessing'),
                criteria=mod_def.get('criteria'),
                rule_result_operator=mod_def.get('rule_result_operator'),
                required_columns=mod_def.get('required_columns', {}),
                override_modifiers=mod_def.get('override_modifiers', [])
            )
            self.modifiers[name] = modifier

            # Build override map
            if modifier.override_modifiers:
                self.modifier_overrides[name] = modifier.override_modifiers

        print(f"Loaded {len(self.modifiers)} hardcoded modifiers")

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

    def get_modifier_required_columns(self, modifier_names: List[str]) -> Dict[str, List[str]]:
        """
        Get required columns for a list of modifiers.

        Args:
            modifier_names: List of modifier names

        Returns:
            Dict of {table_name: [column_names]}
        """
        required = {}
        for name in modifier_names:
            if name in self.modifiers:
                modifier = self.modifiers[name]
                for table, columns in modifier.required_columns.items():
                    if table not in required:
                        required[table] = []
                    for col in columns:
                        if col not in required[table]:
                            required[table].append(col)
        return required
