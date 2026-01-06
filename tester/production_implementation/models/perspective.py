"""Data models for perspectives."""
from dataclasses import dataclass, field
from typing import List

from .rule import Rule


@dataclass
class Perspective:
    """Represents a perspective with its filtering rules."""
    id: int
    name: str
    is_active: bool = True
    is_supported: bool = True
    rules: List[Rule] = field(default_factory=list)
