"""
Comprehensive test for weight scaling in perspective service.
This test manually calculates expected values and compares with system output.
"""

import json
import sys
from pathlib import Path

# Add current directory to path to import gemini
sys.path.insert(0, str(Path(__file__).parent))

from gemini import FastPerspectiveEngine


def manual_calculation_test_1001():
    """
    Test 1001: Filter out C (instrument_id=103) and scale holdings to 100%

    Initial positions:
    - pos_A: weight=20.0, instrument_id=101
    - pos_B: weight=30.0, instrument_id=102
    - pos_C: weight=50.0, instrument_id=103

    Initial lookthroughs:
    - lt_A:  weight=10.0, parent=101
    - lt_B1: weight=20.0, parent=102
    - lt_B2: weight=15.0, parent=102
    """
    print("\n" + "=" * 80)
    print("TEST 1001: Filter C and scale_holdings_to_100_percent")
    print("=" * 80)

    # Step 1: Apply filter (instrument_id != 103)
    print("\nStep 1: Apply filter (instrument_id != 103)")
    print("  Positions kept: pos_A (20.0), pos_B (30.0)")
    print("  Position removed: pos_C (50.0)")

    positions_after_filter = {
        'pos_A': 20.0,
        'pos_B': 30.0
    }
    total_weight = sum(positions_after_filter.values())
    print(f"  Total weight after filter: {total_weight}")

    # Step 2: Cascade removal for lookthroughs
    print("\nStep 2: Cascade removal for lookthroughs")
    print("  Parent 101 (pos_A) kept -> lt_A kept")
    print("  Parent 102 (pos_B) kept -> lt_B1, lt_B2 kept")
    print("  Parent 103 (pos_C) removed -> no lookthroughs affected")

    lookthroughs_after_cascade = {
        'lt_A': 10.0,
        'lt_B1': 20.0,
        'lt_B2': 15.0
    }

    # Step 3: Apply scale_holdings_to_100_percent
    print("\nStep 3: Apply scale_holdings_to_100_percent modifier")
    total_lt_weight = sum(lookthroughs_after_cascade.values())
    print(f"  Essential lookthrough total: {total_lt_weight}")
    denominator = total_weight + total_lt_weight
    print(f"  Denominator = position sum + essential lt sum = {total_weight} + {total_lt_weight} = {denominator}")

    expected_positions = {}
    for pid, weight in positions_after_filter.items():
        expected_positions[pid] = weight / denominator
        print(f"  {pid}: {weight} / {denominator} = {expected_positions[pid]:.6f}")

    print(f"\nExpected position weights sum: {sum(expected_positions.values()):.6f}")

    # Lookthroughs should NOT be scaled by scale_holdings_to_100_percent
    print("\nLookthroughs (NOT scaled by holdings modifier):")
    for lid, weight in lookthroughs_after_cascade.items():
        print(f"  {lid}: {weight:.2f}")

    return expected_positions, lookthroughs_after_cascade


def manual_calculation_test_1002():
    """
    Test 1002: No filter, scale_lookthroughs_to_100_percent

    All positions and lookthroughs kept.
    """
    print("\n" + "=" * 80)
    print("TEST 1002: No filter, scale_lookthroughs_to_100_percent")
    print("=" * 80)

    # Step 1: No filter - all kept
    print("\nStep 1: No filter applied")
    print("  All positions kept: pos_A (20.0), pos_B (30.0), pos_C (50.0)")
    print("  All lookthroughs kept: lt_A (10.0), lt_B1 (20.0), lt_B2 (15.0)")

    positions_kept = {
        'pos_A': 20.0,
        'pos_B': 30.0,
        'pos_C': 50.0
    }

    lookthroughs_kept = {
        'lt_A': 10.0,
        'lt_B1': 20.0,
        'lt_B2': 15.0
    }

    # Step 2: Apply scale_lookthroughs_to_100_percent
    print("\nStep 2: Apply scale_lookthroughs_to_100_percent modifier")
    print("  This scales lookthroughs PER PARENT, not globally!")

    # Group by parent
    parent_groups = {
        101: {'lt_A': 10.0},
        102: {'lt_B1': 20.0, 'lt_B2': 15.0}
    }

    expected_lookthroughs = {}
    for parent_id, lts in parent_groups.items():
        parent_total = sum(lts.values())
        print(f"\n  Parent {parent_id}: total = {parent_total}")
        for lid, weight in lts.items():
            expected_lookthroughs[lid] = weight / parent_total
            print(f"    {lid}: {weight} / {parent_total} = {expected_lookthroughs[lid]:.6f}")

    print(f"\nExpected lookthrough weights sum: {sum(expected_lookthroughs.values()):.6f}")
    print(f"  (Note: Sum is 2.0 because we have 2 parent groups, each summing to 1.0)")

    # Positions should NOT be scaled by scale_lookthroughs_to_100_percent
    print("\nPositions (NOT scaled by lookthrough modifier):")
    for pid, weight in positions_kept.items():
        print(f"  {pid}: {weight:.2f}")

    return positions_kept, expected_lookthroughs


def manual_calculation_test_1003():
    """
    Test 1003: Filter B (instrument_id=102) and scale both holdings and lookthroughs
    """
    print("\n" + "=" * 80)
    print("TEST 1003: Filter B, scale both holdings and lookthroughs")
    print("=" * 80)

    # Step 1: Apply filter (instrument_id != 102)
    print("\nStep 1: Apply filter (instrument_id != 102)")
    print("  Positions kept: pos_A (20.0), pos_C (50.0)")
    print("  Position removed: pos_B (30.0)")

    positions_after_filter = {
        'pos_A': 20.0,
        'pos_C': 50.0
    }

    # Step 2: Cascade removal
    print("\nStep 2: Cascade removal for lookthroughs")
    print("  Parent 101 (pos_A) kept -> lt_A kept")
    print("  Parent 102 (pos_B) REMOVED -> lt_B1, lt_B2 REMOVED")
    print("  Parent 103 (pos_C) kept -> no lookthroughs for C")

    lookthroughs_after_cascade = {
        'lt_A': 10.0
    }

    # Step 3: Apply scale_holdings_to_100_percent
    print("\nStep 3: Apply scale_holdings_to_100_percent")
    total_pos_weight = sum(positions_after_filter.values())
    total_lt_weight = sum(lookthroughs_after_cascade.values())
    denominator = total_pos_weight + total_lt_weight
    print(f"  Denominator = {total_pos_weight} + {total_lt_weight} = {denominator}")

    expected_positions = {}
    for pid, weight in positions_after_filter.items():
        expected_positions[pid] = weight / denominator
        print(f"  {pid}: {weight} / {denominator} = {expected_positions[pid]:.6f}")

    # Step 4: Apply scale_lookthroughs_to_100_percent
    print("\nStep 4: Apply scale_lookthroughs_to_100_percent")
    print("  Scales lookthroughs PER PARENT")

    expected_lookthroughs = {}
    if lookthroughs_after_cascade:
        # Only one parent (101) with one lookthrough
        for lid, weight in lookthroughs_after_cascade.items():
            expected_lookthroughs[lid] = 1.0  # Only one per parent = 100%
            print(f"  {lid}: {weight} / {weight} = {expected_lookthroughs[lid]:.6f}")
    else:
        print("  No lookthroughs to scale")

    return expected_positions, expected_lookthroughs


def manual_calculation_test_1004():
    """
    Test 1004: Edge case - filter all (instrument_id > 200)
    """
    print("\n" + "=" * 80)
    print("TEST 1004: Edge case - filter all positions")
    print("=" * 80)

    print("\nStep 1: Apply filter (instrument_id > 200)")
    print("  All positions have instrument_id <= 103, so ALL filtered out")
    print("  Positions kept: NONE")

    print("\nStep 2: Cascade removal")
    print("  All parents removed -> all lookthroughs removed")
    print("  Lookthroughs kept: NONE")

    print("\nStep 3: Apply scale_holdings_to_100_percent")
    print("  No positions to scale")

    return {}, {}


def run_system_test(test_name, perspective_id):
    """Run the actual system and return results."""
    print(f"\n{'='*80}")
    print(f"RUNNING SYSTEM FOR {test_name}")
    print(f"{'='*80}")

    # Load test data
    with open('test_data.json', 'r') as f:
        test_data = json.load(f)

    # Initialize engine
    engine = FastPerspectiveEngine('test_rules.json')

    # Process
    results = engine.process(test_data)

    # Extract results for the specific test
    test_config_name = f"test_{perspective_id}"

    # Handle case where perspective might not exist (all filtered out)
    if str(perspective_id) not in results['perspective_configurations'][test_config_name]:
        print(f"  Perspective {perspective_id} not in results (likely all positions filtered)")
        return {}, {}

    perspective_results = results['perspective_configurations'][test_config_name][str(perspective_id)]['test_portfolio']

    positions = perspective_results.get('positions', {})
    lookthroughs = perspective_results.get('essential_lookthroughs', {})

    print(f"\nSystem output for perspective {perspective_id}:")
    print(f"  Positions: {list(positions.keys())}")
    if positions:
        for pid, data in sorted(positions.items()):
            print(f"    {pid}: weight={data.get('weight', 0):.6f}")

    print(f"  Lookthroughs: {list(lookthroughs.keys())}")
    if lookthroughs:
        for lid, data in sorted(lookthroughs.items()):
            print(f"    {lid}: weight={data.get('weight', 0):.6f}")

    return positions, lookthroughs


def compare_results(expected_pos, expected_lt, actual_pos, actual_lt, test_name):
    """Compare expected vs actual results."""
    print(f"\n{'='*80}")
    print(f"COMPARISON FOR {test_name}")
    print(f"{'='*80}")

    all_passed = True

    # Compare positions
    print("\nPositions comparison:")
    expected_pids = set(expected_pos.keys())
    actual_pids = set(actual_pos.keys())

    if expected_pids != actual_pids:
        print(f"  ERROR: Position IDs mismatch!")
        print(f"    Expected: {sorted(expected_pids)}")
        print(f"    Actual: {sorted(actual_pids)}")
        all_passed = False

    for pid in expected_pids:
        if pid in actual_pos:
            expected_weight = expected_pos[pid]
            actual_weight = actual_pos[pid].get('weight', 0)
            diff = abs(expected_weight - actual_weight)
            status = "PASS" if diff < 0.0001 else "FAIL"
            print(f"  {pid}: expected={expected_weight:.6f}, actual={actual_weight:.6f}, diff={diff:.6f} {status}")
            if diff >= 0.0001:
                all_passed = False

    # Compare lookthroughs
    print("\nLookthroughs comparison:")
    expected_lids = set(expected_lt.keys())
    actual_lids = set(actual_lt.keys())

    if expected_lids != actual_lids:
        print(f"  ERROR: Lookthrough IDs mismatch!")
        print(f"    Expected: {sorted(expected_lids)}")
        print(f"    Actual: {sorted(actual_lids)}")
        all_passed = False

    for lid in expected_lids:
        if lid in actual_lt:
            expected_weight = expected_lt[lid]
            actual_weight = actual_lt[lid].get('weight', 0)
            diff = abs(expected_weight - actual_weight)
            status = "PASS" if diff < 0.0001 else "FAIL"
            print(f"  {lid}: expected={expected_weight:.6f}, actual={actual_weight:.6f}, diff={diff:.6f} {status}")
            if diff >= 0.0001:
                all_passed = False

    # Check sums for scaled items
    if test_name == "TEST 1001":
        # Positions scaled by (pos_sum + lt_sum), so won't sum to 1.0
        actual_pos_sum = sum(p.get('weight', 0) for p in actual_pos.values())
        expected_pos_sum = sum(expected_pos.values())
        print(f"\nPosition weights sum: expected={expected_pos_sum:.6f}, actual={actual_pos_sum:.6f}")

    elif test_name == "TEST 1002":
        # Lookthroughs scaled PER PARENT, so sum = number of parents
        actual_lt_sum = sum(lt.get('weight', 0) for lt in actual_lt.values())
        expected_lt_sum = sum(expected_lt.values())
        print(f"\nLookthrough weights sum: expected={expected_lt_sum:.6f}, actual={actual_lt_sum:.6f}")

    elif test_name == "TEST 1003":
        # Positions scaled by (pos_sum + lt_sum), lookthroughs scaled per parent
        actual_pos_sum = sum(p.get('weight', 0) for p in actual_pos.values())
        actual_lt_sum = sum(lt.get('weight', 0) for lt in actual_lt.values())
        expected_pos_sum = sum(expected_pos.values())
        expected_lt_sum = sum(expected_lt.values()) if expected_lt else 0
        print(f"\nPosition weights sum: expected={expected_pos_sum:.6f}, actual={actual_pos_sum:.6f}")
        print(f"Lookthrough weights sum: expected={expected_lt_sum:.6f}, actual={actual_lt_sum:.6f}")

    if all_passed:
        print(f"\n[PASS] {test_name} PASSED")
    else:
        print(f"\n[FAIL] {test_name} FAILED")

    return all_passed


def main():
    print("=" * 80)
    print("COMPREHENSIVE WEIGHT SCALING TEST")
    print("=" * 80)

    all_tests_passed = True

    # Test 1001
    expected_pos_1001, expected_lt_1001 = manual_calculation_test_1001()
    actual_pos_1001, actual_lt_1001 = run_system_test("TEST 1001", 1001)
    passed_1001 = compare_results(expected_pos_1001, expected_lt_1001,
                                   actual_pos_1001, actual_lt_1001, "TEST 1001")
    all_tests_passed &= passed_1001

    # Test 1002
    expected_pos_1002, expected_lt_1002 = manual_calculation_test_1002()
    actual_pos_1002, actual_lt_1002 = run_system_test("TEST 1002", 1002)
    passed_1002 = compare_results(expected_pos_1002, expected_lt_1002,
                                   actual_pos_1002, actual_lt_1002, "TEST 1002")
    all_tests_passed &= passed_1002

    # Test 1003
    expected_pos_1003, expected_lt_1003 = manual_calculation_test_1003()
    actual_pos_1003, actual_lt_1003 = run_system_test("TEST 1003", 1003)
    passed_1003 = compare_results(expected_pos_1003, expected_lt_1003,
                                   actual_pos_1003, actual_lt_1003, "TEST 1003")
    all_tests_passed &= passed_1003

    # Test 1004
    expected_pos_1004, expected_lt_1004 = manual_calculation_test_1004()
    actual_pos_1004, actual_lt_1004 = run_system_test("TEST 1004", 1004)
    passed_1004 = compare_results(expected_pos_1004, expected_lt_1004,
                                   actual_pos_1004, actual_lt_1004, "TEST 1004")
    all_tests_passed &= passed_1004

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Test 1001 (Filter C, scale holdings): {'PASSED' if passed_1001 else 'FAILED'}")
    print(f"Test 1002 (No filter, scale lookthroughs): {'PASSED' if passed_1002 else 'FAILED'}")
    print(f"Test 1003 (Filter B, scale both): {'PASSED' if passed_1003 else 'FAILED'}")
    print(f"Test 1004 (Filter all, edge case): {'PASSED' if passed_1004 else 'FAILED'}")

    if all_tests_passed:
        print("\n[SUCCESS] ALL TESTS PASSED! Weight calculations are CORRECT.")
    else:
        print("\n[ERROR] SOME TESTS FAILED! Weight calculations have issues.")

    return all_tests_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)