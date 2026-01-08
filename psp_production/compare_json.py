"""
JSON Comparison Tool - Compare two JSON files with tolerance for numerical differences.

Usage:
    python compare_json.py <expected.json> <actual.json> [--delta 1e-10]

Example:
    python compare_json.py production_output.json psp_output.json --delta 0.0001
"""

import sys
import json
import argparse
from typing import Any, List, Tuple


def compare_values(expected: Any, actual: Any, path: str, delta: float) -> List[Tuple[str, str, Any, Any]]:
    """
    Compare two values recursively.

    Returns list of (path, reason, expected, actual) for each mismatch.
    """
    mismatches = []

    # Handle None
    if expected is None and actual is None:
        return []
    if expected is None or actual is None:
        mismatches.append((path, "one is None", expected, actual))
        return mismatches

    # Type mismatch (but allow int/float comparison)
    if type(expected) != type(actual):
        # Allow int vs float comparison
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            pass  # Continue to numeric comparison
        else:
            mismatches.append((path, f"type mismatch ({type(expected).__name__} vs {type(actual).__name__})", expected, actual))
            return mismatches

    # Dict comparison
    if isinstance(expected, dict):
        # Check for missing keys
        expected_keys = set(expected.keys())
        actual_keys = set(actual.keys())

        missing_in_actual = expected_keys - actual_keys
        extra_in_actual = actual_keys - expected_keys

        for key in missing_in_actual:
            mismatches.append((f"{path}.{key}", "missing in actual", expected[key], "<MISSING>"))

        for key in extra_in_actual:
            mismatches.append((f"{path}.{key}", "extra in actual", "<MISSING>", actual[key]))

        # Compare common keys
        for key in expected_keys & actual_keys:
            child_path = f"{path}.{key}" if path else str(key)
            mismatches.extend(compare_values(expected[key], actual[key], child_path, delta))

        return mismatches

    # List comparison
    if isinstance(expected, list):
        if len(expected) != len(actual):
            mismatches.append((path, f"list length ({len(expected)} vs {len(actual)})", len(expected), len(actual)))
            # Still compare what we can

        for i in range(min(len(expected), len(actual))):
            child_path = f"{path}[{i}]"
            mismatches.extend(compare_values(expected[i], actual[i], child_path, delta))

        return mismatches

    # Numeric comparison with delta
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if abs(expected - actual) > delta:
            mismatches.append((path, f"value diff > {delta}", expected, actual))
        return mismatches

    # String/bool/other direct comparison
    if expected != actual:
        mismatches.append((path, "value mismatch", expected, actual))

    return mismatches


def main():
    parser = argparse.ArgumentParser(description='Compare two JSON files')
    parser.add_argument('expected', help='Path to expected JSON file (e.g., production output)')
    parser.add_argument('actual', help='Path to actual JSON file (e.g., PSP output)')
    parser.add_argument('--delta', '-d', type=float, default=1e-10,
                        help='Tolerance for numerical comparison (default: 1e-10)')
    parser.add_argument('--max-errors', '-m', type=int, default=50,
                        help='Maximum number of errors to display (default: 50)')
    args = parser.parse_args()

    # Load JSON files
    print(f"Loading expected: {args.expected}")
    try:
        with open(args.expected, 'r', encoding='utf-8') as f:
            expected = json.load(f)
    except Exception as e:
        print(f"ERROR loading expected file: {e}")
        sys.exit(1)

    print(f"Loading actual: {args.actual}")
    try:
        with open(args.actual, 'r', encoding='utf-8') as f:
            actual = json.load(f)
    except Exception as e:
        print(f"ERROR loading actual file: {e}")
        sys.exit(1)

    print(f"Comparing with delta={args.delta}...")
    print("=" * 80)

    # Compare
    mismatches = compare_values(expected, actual, "", args.delta)

    if not mismatches:
        print("\nSUCCESS: No differences found!")
        sys.exit(0)

    # Print mismatches
    print(f"\nFOUND {len(mismatches)} DIFFERENCES:\n")

    for i, (path, reason, exp_val, act_val) in enumerate(mismatches[:args.max_errors]):
        print(f"{i+1}. {path or 'ROOT'}")
        print(f"   Reason: {reason}")

        # Truncate long values
        exp_str = str(exp_val)
        act_str = str(act_val)
        if len(exp_str) > 100:
            exp_str = exp_str[:100] + "..."
        if len(act_str) > 100:
            act_str = act_str[:100] + "..."

        print(f"   Expected: {exp_str}")
        print(f"   Actual:   {act_str}")
        print()

    if len(mismatches) > args.max_errors:
        print(f"... and {len(mismatches) - args.max_errors} more differences (use --max-errors to see more)")

    print("=" * 80)
    print(f"FAILED: {len(mismatches)} differences found")
    sys.exit(1)


if __name__ == "__main__":
    main()
