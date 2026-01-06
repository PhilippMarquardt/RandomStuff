"""Modifier data model."""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class Modifier:
    """Represents a rule modifier that can adjust rule behavior."""
    name: str
    apply_to: str  # 'position', 'lookthrough', 'both'
    modifier_type: str  # 'PreProcessing', 'PostProcessing', 'Scaling'
    criteria: Optional[Dict[str, Any]] = None
    rule_result_operator: Optional[str] = None  # 'and' or 'or'
    override_modifiers: List[str] = field(default_factory=list)
