"""
Perspective Service - Production Implementation

A Polars-based perspective processing engine for financial position
and lookthrough data.
"""

from perspective_service.core.engine import PerspectiveEngine
from perspective_service.core.configuration_manager import ConfigurationManager
from perspective_service.core.data_ingestion import DataIngestion
from perspective_service.core.perspective_processor import PerspectiveProcessor
from perspective_service.core.output_formatter import OutputFormatter
from perspective_service.core.rule_evaluator import RuleEvaluator

__all__ = [
    'PerspectiveEngine',
    'ConfigurationManager',
    'DataIngestion',
    'PerspectiveProcessor',
    'OutputFormatter',
    'RuleEvaluator',
]
