"""Data models for perspectives and rules."""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class Rule:
    """Represents a single filtering rule within a perspective."""
    name: str
    apply_to: str  # 'position', 'lookthrough', 'both'
    criteria: Optional[Dict[str, Any]] = None
    condition_for_next_rule: Optional[str] = None  # 'And' or 'Or'


@dataclass
class Perspective:
    """Represents a perspective with its filtering rules."""
    id: int
    name: str
    is_active: bool = True
    is_supported: bool = True
    rules: List[Rule] = field(default_factory=list)
