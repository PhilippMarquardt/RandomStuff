"""Rule data model."""
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class Rule:
    """Represents a single filtering or scaling rule within a perspective."""
    name: str
    apply_to: str  # 'position', 'lookthrough', 'both'
    criteria: Optional[Dict[str, Any]] = None
    condition_for_next_rule: Optional[str] = None  # 'And' or 'Or'
    is_scaling_rule: bool = False
    scale_factor: float = 1.0
