"""Database loaders for perspectives and reference data."""

from perspective_service.database.loaders.perspective_loader import load_perspectives
from perspective_service.database.loaders.reference_loader import ReferenceLoader

__all__ = ['load_perspectives', 'ReferenceLoader']
