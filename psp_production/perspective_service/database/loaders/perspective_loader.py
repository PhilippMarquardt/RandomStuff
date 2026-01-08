"""
Perspective loader - loads perspectives from database.
"""

import json
from typing import Dict, Optional

import pyodbc


class PerspectiveLoadError(Exception):
    """Raised when perspective loading fails."""
    pass


def load_perspectives(conn: pyodbc.Connection, system_version_timestamp: Optional[str] = None) -> Dict[int, Dict]:
    """
    Load perspectives from database using FN_GET_SUBSETTING_SERVICE_PERSPECTIVES.

    Args:
        conn: Database connection
        system_version_timestamp: Optional timestamp for temporal queries

    Returns:
        Dict of {perspective_id: perspective_dict}

    Raises:
        PerspectiveLoadError: If loading fails
    """
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT [dbo].[FN_GET_SUBSETTING_SERVICE_PERSPECTIVES]({system_version_timestamp!r})")
        perspective_data = cursor.fetchall()

        if len(perspective_data) == 0 or len(perspective_data[0]) == 0:
            raise PerspectiveLoadError("No perspectives found in database")

        json_data = json.loads(perspective_data[0][0])
        raw_perspectives = json_data.get('perspectives', [])

        # Group by perspective ID (SQL can return multiple rows per perspective)
        grouped = {}
        for p in raw_perspectives:
            pid = p.get('id')
            if pid not in grouped:
                grouped[pid] = {
                    'id': pid,
                    'name': p.get('name'),
                    'is_active': p.get('is_active', True),
                    'is_supported': p.get('is_compatible_with_sub_setting_service', True),
                    'rules': []
                }
            grouped[pid]['is_active'] &= p.get('is_active', True)
            grouped[pid]['is_supported'] &= bool(p.get('is_compatible_with_sub_setting_service', True))
            grouped[pid]['rules'].extend(p.get('rules', []))

        print(f"Loaded {len(grouped)} perspectives from database")
        return grouped

    except json.JSONDecodeError as e:
        raise PerspectiveLoadError(f"Failed to parse perspective JSON: {e}")
    except pyodbc.Error as e:
        raise PerspectiveLoadError(f"Database error loading perspectives: {e}")
