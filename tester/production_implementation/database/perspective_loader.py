"""Load perspectives from the database."""
import json
import logging
from typing import Dict, Optional

from ..config import DatabaseConfig
from ..models.perspective import Perspective, Rule
from .connection import get_connection

logger = logging.getLogger(__name__)


class PerspectiveLoader:
    """Loads perspectives and rules from the database."""

    def __init__(self, config: DatabaseConfig):
        """
        Initialize the loader with database configuration.

        Args:
            config: Database connection configuration.
        """
        self.config = config

    def load_perspectives(self, system_version_timestamp: Optional[str] = None) -> Dict[int, Perspective]:
        """
        Load perspectives from FN_GET_SUBSETTING_SERVICE_PERSPECTIVES.

        Args:
            system_version_timestamp: Optional timestamp for versioned perspective loading.

        Returns:
            Dictionary mapping perspective ID to Perspective object.
        """
        with get_connection(self.config) as conn:
            cursor = conn.cursor()

            # Build and execute query
            if system_version_timestamp:
                query = f"SELECT [dbo].[FN_GET_SUBSETTING_SERVICE_PERSPECTIVES]('{system_version_timestamp}')"
            else:
                query = "SELECT [dbo].[FN_GET_SUBSETTING_SERVICE_PERSPECTIVES](NULL)"

            cursor.execute(query)
            result = cursor.fetchone()

            if not result or not result[0]:
                logger.warning("No perspectives found in database")
                return {}

            return self._parse_perspectives(json.loads(result[0]))

    def _parse_perspectives(self, json_data: dict) -> Dict[int, Perspective]:
        """
        Parse JSON response into Perspective objects.

        Handles the case where SQL returns multiple rows per perspective
        by grouping them by ID.

        Args:
            json_data: Parsed JSON from the stored procedure.

        Returns:
            Dictionary mapping perspective ID to Perspective object.
        """
        raw_perspectives = json_data.get('perspectives', [])
        grouped: Dict[int, Perspective] = {}

        for p in raw_perspectives:
            pid = p.get('id')
            if pid is None:
                continue

            if pid not in grouped:
                grouped[pid] = Perspective(
                    id=pid,
                    name=p.get('name', ''),
                    is_active=p.get('is_active', True),
                    is_supported=p.get('is_compatible_with_sub_setting_service', True),
                    rules=[]
                )

            # Combine flags across multiple rows
            grouped[pid].is_active &= p.get('is_active', True)
            grouped[pid].is_supported &= bool(p.get('is_compatible_with_sub_setting_service', True))

            # Add rules from this row
            for rule_data in p.get('rules', []):
                grouped[pid].rules.append(self._parse_rule(rule_data))

        logger.info(f"Loaded {len(grouped)} perspectives from database")
        return grouped

    def _parse_rule(self, rule_data: dict) -> Rule:
        """
        Parse a rule dictionary into a Rule object.

        Args:
            rule_data: Dictionary containing rule definition.

        Returns:
            Rule object.
        """
        criteria = rule_data.get('criteria')

        # Handle criteria stored as JSON string
        if isinstance(criteria, str):
            try:
                criteria = json.loads(criteria)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse criteria JSON: {criteria}")
                criteria = None

        return Rule(
            name=rule_data.get('name', ''),
            apply_to=rule_data.get('apply_to', 'both'),
            criteria=criteria,
            condition_for_next_rule=rule_data.get('condition_for_next_rule')
        )
