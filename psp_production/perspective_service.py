"""
Perspective Service - Main API entry point.
"""

from typing import Dict, List, Optional

from config import load_config, DatabaseConfig
from perspective_service.database.connection import get_connection
from perspective_service.core.engine import PerspectiveEngine


class PerspectiveService:
    """
    Main API for perspective processing.

    Usage:
        service = PerspectiveService()
        result = service.process(input_json, perspective_configs, weights)
    """

    def __init__(self,
                 config: Optional[DatabaseConfig] = None,
                 config_path: str = ".env"):
        """
        Initialize the PerspectiveService.

        Args:
            config: Optional DatabaseConfig. If not provided, loads from env.
            config_path: Path to .env file (used if config not provided)
        """
        self.config = config or load_config(config_path)
        self._engine: Optional[PerspectiveEngine] = None

    def process(self,
                input_json: Dict,
                perspective_configs: Dict[str, Dict[str, List[str]]],
                position_weights: List[str],
                lookthrough_weights: Optional[List[str]] = None,
                system_version_timestamp: Optional[str] = None,
                verbose: bool = False) -> Dict:
        """
        Process input data through perspective rules.

        Args:
            input_json: Raw input data containing positions and lookthroughs
            perspective_configs: {config_name: {perspective_id: [modifier_names]}}
            position_weights: List of weight column names for positions
            lookthrough_weights: List of weight column names for lookthroughs
            system_version_timestamp: Optional timestamp for temporal DB queries
            verbose: Whether to include removal summary in output

        Returns:
            Formatted output dictionary with perspective_configurations

        Example:
            input_json = {
                "container_1": {
                    "position_type": "benchmark",
                    "positions": {
                        "pos_1": {"instrument_id": 123, "weight": 0.5},
                        "pos_2": {"instrument_id": 456, "weight": 0.3}
                    }
                }
            }

            perspective_configs = {
                "default": {
                    "1": ["exclude_other_net_assets"],
                    "2": []
                }
            }

            result = service.process(
                input_json,
                perspective_configs,
                position_weights=["weight"]
            )
        """
        if lookthrough_weights is None:
            lookthrough_weights = position_weights

        with get_connection(self.config) as conn:
            engine = PerspectiveEngine(conn, system_version_timestamp)
            return engine.process(
                input_json,
                perspective_configs,
                position_weights,
                lookthrough_weights,
                verbose
            )

    def process_without_db(self,
                           input_json: Dict,
                           perspective_configs: Dict[str, Dict[str, List[str]]],
                           position_weights: List[str],
                           lookthrough_weights: Optional[List[str]] = None,
                           verbose: bool = False) -> Dict:
        """
        Process input data without database connection (for testing).

        Note: This will only work with empty perspectives or pre-loaded config.
        """
        if lookthrough_weights is None:
            lookthrough_weights = position_weights

        engine = PerspectiveEngine(None, None)
        return engine.process(
            input_json,
            perspective_configs,
            position_weights,
            lookthrough_weights,
            verbose
        )
