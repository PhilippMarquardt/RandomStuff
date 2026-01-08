"""
Test with Database - Run perspective service with real DB connection and JSON input.

Usage:
    python test_with_database.py <input_json_file> [--verbose]

Example:
    python test_with_database.py request.json --verbose

Requires .env file with database configuration (see config.py).
"""

import sys
import io
import json
import argparse

import pyodbc

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add current directory to path
sys.path.insert(0, '.')

from config import load_config, DatabaseConfig
from perspective_service.core.engine import PerspectiveEngine


def get_db_connection(config: DatabaseConfig):
    """Create database connection from config."""
    print(f"  DB Server: {config.server}")
    print(f"  DB Database: {config.database}")
    print(f"  DB Driver: {config.driver}")
    print(f"  Trusted Connection: {config.trusted_connection}")

    if config.trusted_connection:
        conn_string = f"DRIVER={{{config.driver}}};SERVER={config.server};DATABASE={config.database};Trusted_Connection=yes;"
    else:
        conn_string = f"DRIVER={{{config.driver}}};SERVER={config.server};DATABASE={config.database};UID={config.username};PWD={config.password};"

    print(f"  Connecting...")
    connection = pyodbc.connect(conn_string)
    print(f"  Connected!")

    return connection


def main():
    # Parse args first
    parser = argparse.ArgumentParser(description='Test perspective service with JSON input')
    parser.add_argument('input_file', help='Path to input JSON file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Include removal summary in output')
    args = parser.parse_args()

    # =========================================================================
    # STEP 1: Load Config
    # =========================================================================
    print("=" * 80)
    print("STEP 1: Loading Config")
    print("=" * 80)

    config = load_config()
    print(f"  Config loaded from .env")

    # =========================================================================
    # STEP 2: Load Input JSON
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 2: Loading Input JSON")
    print("=" * 80)

    with open(args.input_file, 'r') as f:
        request = json.load(f)

    print(f"  Loaded: {args.input_file}")
    print(f"  Top-level keys: {list(request.keys())}")

    # Extract request components
    input_json = request.get('input_json', request)
    perspective_configs = request.get('perspective_configs', {})
    position_weights = request.get('position_weights', ['weight'])
    lookthrough_weights = request.get('lookthrough_weights', ['weight'])
    system_version_timestamp = request.get('system_version_timestamp')

    print(f"  Perspective configs: {list(perspective_configs.keys())}")
    print(f"  Position weights: {position_weights}")
    print(f"  Lookthrough weights: {lookthrough_weights}")

    # Count containers and positions
    for key, value in input_json.items():
        if isinstance(value, dict) and 'position_type' in value:
            pos_count = len(value.get('positions', {}))
            lt_count = sum(len(v) for k, v in value.items() if 'lookthrough' in k and isinstance(v, dict))
            print(f"  Container '{key}': {pos_count} positions, {lt_count} lookthroughs")

    # =========================================================================
    # STEP 3: Connect to Database
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 3: Connecting to Database")
    print("=" * 80)

    db_connection = get_db_connection(config)

    # =========================================================================
    # STEP 4: Initialize Engine
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 4: Initializing Engine")
    print("=" * 80)

    engine = PerspectiveEngine(
        db_connection=db_connection,
        system_version_timestamp=system_version_timestamp
    )

    print(f"  Engine initialized")
    print(f"  Loaded {len(engine.config.perspectives)} perspectives from DB")
    print(f"  Loaded {len(engine.config.modifiers)} modifiers")
    print(f"  Default modifiers: {engine.config.default_modifiers}")

    # =========================================================================
    # STEP 5: Show Perspective Details
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 5: Perspective Configuration Details")
    print("=" * 80)

    for config_name, perspective_map in perspective_configs.items():
        print(f"\n  Config: {config_name}")
        for pid, modifiers in perspective_map.items():
            pid_int = int(pid)
            rules = engine.config.perspectives.get(pid_int, [])
            print(f"    Perspective {pid}: {len(rules)} rules, modifiers: {modifiers or 'none'}")
            for i, rule in enumerate(rules[:3]):
                print(f"      Rule {i}: apply_to={rule.apply_to}, scaling={rule.is_scaling_rule}")
            if len(rules) > 3:
                print(f"      ... and {len(rules) - 3} more rules")

    # =========================================================================
    # STEP 6: Check Custom Perspectives
    # =========================================================================
    if 'custom_perspective_rules' in input_json:
        print("\n" + "=" * 80)
        print("STEP 6: Custom Perspective Rules")
        print("=" * 80)

        for pid, data in input_json['custom_perspective_rules'].items():
            print(f"  Custom Perspective {pid}: {data.get('name', 'unnamed')}")
            rules = data.get('rules', [])
            print(f"    Rules: {len(rules)}")

    # =========================================================================
    # STEP 7: Process
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 7: Processing")
    print("=" * 80)

    print("  Calling engine.process()...")

    result = engine.process(
        input_json=input_json,
        perspective_configs=perspective_configs,
        position_weights=position_weights,
        lookthrough_weights=lookthrough_weights,
        verbose=args.verbose
    )

    print("  Processing complete!")

    # =========================================================================
    # STEP 8: Output Summary
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 8: Output Summary")
    print("=" * 80)

    configs = result.get('perspective_configurations', {})
    print(f"  Output configs: {list(configs.keys())}")

    for config_name, perspectives in configs.items():
        print(f"\n  Config: {config_name}")
        for pid, containers_data in perspectives.items():
            print(f"    Perspective {pid}:")
            for container, data in containers_data.items():
                positions = data.get('positions', {})
                scale_factors = data.get('scale_factors', {})
                removed = data.get('removed_positions_weight_summary', {})

                lt_keys = [k for k in data.keys() if 'lookthrough' in k]
                lt_count = sum(len(data.get(k, {})) for k in lt_keys)

                print(f"      {container}:")
                print(f"        Positions kept: {len(positions)}")
                print(f"        Lookthroughs kept: {lt_count}")
                if scale_factors:
                    print(f"        Scale factors: {scale_factors}")
                if removed:
                    print(f"        Removed summary keys: {list(removed.keys())}")

    # =========================================================================
    # STEP 9: Full Output
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 9: Full Output JSON")
    print("=" * 80)

    print(json.dumps(result, indent=2, default=str))

    # =========================================================================
    # STEP 10: Cleanup
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 10: Cleanup")
    print("=" * 80)

    if db_connection:
        db_connection.close()
        print("  Database connection closed")

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    main()
