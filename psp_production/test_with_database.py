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

    # Extract request components (matching actual request format)
    perspective_configs = request.get('perspective_configurations', {})
    position_weights = request.get('position_weight_labels', ['weight'])
    lookthrough_weights = request.get('lookthrough_weight_labels', ['weight'])
    system_version_timestamp = request.get('system_version_timestamp')
    effective_date = request.get('ed')

    # The input_json is the request itself (containers are at root level)
    input_json = request

    print(f"  Effective date: {effective_date}")
    print(f"  System version timestamp: {system_version_timestamp}")
    print(f"  Position weights: {position_weights}")
    print(f"  Lookthrough weights: {lookthrough_weights}")

    # DEBUG: Print full perspective_configs
    print(f"\n  DEBUG perspective_configs:")
    print(f"    Raw value: {perspective_configs}")
    print(f"    Keys: {list(perspective_configs.keys())}")
    for config_name, pmap in perspective_configs.items():
        print(f"    Config '{config_name}':")
        for pid, mods in pmap.items():
            print(f"      Perspective {pid} (type: {type(pid).__name__}): modifiers={mods}")

    # Count containers and positions
    print(f"\n  Containers found:")
    containers_found = []
    for key, value in input_json.items():
        if isinstance(value, dict) and 'position_type' in value:
            containers_found.append(key)
            pos_count = len(value.get('positions', {}))
            lt_keys = [k for k in value.keys() if 'lookthrough' in k]
            lt_count = sum(len(value.get(k, {})) for k in lt_keys)
            print(f"    Container '{key}': {pos_count} positions, {lt_count} lookthroughs, lt_keys={lt_keys}")
            # Show first position
            positions = value.get('positions', {})
            if positions:
                first_key = list(positions.keys())[0]
                print(f"      First position '{first_key}': {list(positions[first_key].keys())}")

    if not containers_found:
        print(f"    WARNING: No containers found! Looking for dicts with 'position_type' key")
        print(f"    All top-level keys in input_json: {list(input_json.keys())}")
        for key, value in input_json.items():
            if isinstance(value, dict):
                print(f"      '{key}' is a dict with keys: {list(value.keys())[:10]}...")
            else:
                print(f"      '{key}' is type: {type(value).__name__}")

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

    # DEBUG: Check if requested perspectives exist in DB
    print(f"\n  DEBUG: Checking requested perspectives:")
    for config_name, perspective_map in perspective_configs.items():
        for pid_str, modifiers in perspective_map.items():
            pid_int = int(pid_str)
            if pid_int in engine.config.perspectives:
                rules = engine.config.perspectives[pid_int]
                print(f"    Perspective {pid_int}: FOUND ({len(rules)} rules)")
            else:
                print(f"    Perspective {pid_int}: NOT FOUND in DB!")

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
    print(f"    input_json keys: {list(input_json.keys())}")
    print(f"    perspective_configs: {perspective_configs}")
    print(f"    position_weights: {position_weights}")
    print(f"    lookthrough_weights: {lookthrough_weights}")

    try:
        result = engine.process(
            input_json=input_json,
            perspective_configs=perspective_configs,
            position_weights=position_weights,
            lookthrough_weights=lookthrough_weights,
            verbose=args.verbose
        )
        print("  Processing complete!")
        print(f"  Result type: {type(result)}")
        print(f"  Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
    except Exception as e:
        print(f"  ERROR during processing: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return

    # =========================================================================
    # STEP 8: Output Summary
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 8: Output Summary")
    print("=" * 80)

    configs = result.get('perspective_configurations', {})
    print(f"  Output configs: {list(configs.keys())}")
    print(f"  DEBUG: Full result structure: {json.dumps({k: type(v).__name__ for k, v in result.items()}, indent=4)}")

    if not configs:
        print("  WARNING: perspective_configurations is empty!")
        print(f"  Full result: {json.dumps(result, indent=2, default=str)}")

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
