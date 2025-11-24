"""
Test suite for exposure factors (per-row scaling) in perspective service.

These tests validate the per-row scaling mechanism where individual positions/lookthroughs
are multiplied by a scale_factor based on criteria matching.

All expected values are manually calculated based on formulas from:
core_perspective_functions/position_and_lookthrough_data.py:725-743
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cleaned_gemini_wide import FastPerspectiveEngine


def test_3001_simple_scale_factor_0_5x():
    """
    Test 3001: Simple exposure_factor of 0.5x applied to all positions

    Manual calculation based on ORIGINAL_FORMULAS.md:

    Input:
      pos_1: weight=10.0, sub_portfolio_id=sub_A
      pos_2: weight=20.0, sub_portfolio_id=sub_A
      pos_3: weight=30.0, sub_portfolio_id=sub_A

    Scaling rule: exposure_factor=0.5, applies to all positions

    Step 1: Apply exposure_factor=0.5 (ORIGINAL_FORMULAS.md line 735)
      pos_1: weight = 10.0 * 0.5 = 5.0
      pos_2: weight = 20.0 * 0.5 = 10.0
      pos_3: weight = 30.0 * 0.5 = 15.0

    Lookthroughs:
      lt_1: weight=5.0, parent=pos_1
      lt_2: weight=8.0, parent=pos_1

    Expected output:
      pos_1: weight=5.0
      pos_2: weight=10.0
      pos_3: weight=15.0
      lt_1: weight=2.5 (5.0 * 0.5)
      lt_2: weight=4.0 (8.0 * 0.5)
    """
    print("\n" + "="*80)
    print("TEST 3001: Simple scale_factor 0.5x")
    print("="*80)

    print("\nManual calculation:")
    print("  Input: pos_1 (10.0), pos_2 (20.0), pos_3 (30.0)")
    print("        lt_1 (5.0), lt_2 (8.0)")
    print("  Scaling rule: exposure_factor=0.5 for all (apply_to=both)")
    print("  Step 1: Apply scale_factor")
    print("    pos_1: 10.0 * 0.5 = 5.0")
    print("    pos_2: 20.0 * 0.5 = 10.0")
    print("    pos_3: 30.0 * 0.5 = 15.0")
    print("    lt_1: 5.0 * 0.5 = 2.5")
    print("    lt_2: 8.0 * 0.5 = 4.0")

    expected_pos = {'pos_1': 5.0, 'pos_2': 10.0, 'pos_3': 15.0}
    expected_lt = {'lt_1': 2.5, 'lt_2': 4.0}

    return expected_pos, expected_lt


def test_3002_conditional_scale_factor():
    """
    Test 3002: Conditional exposure_factor (only applies to positions matching criteria)

    Manual calculation based on ORIGINAL_FORMULAS.md:

    Input:
      pos_1: weight=10.0, liquidity_type_id=1, sub_portfolio_id=sub_A
      pos_2: weight=20.0, liquidity_type_id=2, sub_portfolio_id=sub_A
      pos_3: weight=30.0, liquidity_type_id=1, sub_portfolio_id=sub_A

    Scaling rule: exposure_factor=0.75, applies WHERE liquidity_type_id=1

    Step 1: Evaluate criteria
      pos_1: liquidity_type_id=1 → matches
      pos_2: liquidity_type_id=2 → does NOT match
      pos_3: liquidity_type_id=1 → matches

    Step 2: Apply exposure_factor to matching rows (ORIGINAL_FORMULAS.md line 738)
      pos_1: weight = 10.0 * 0.75 = 7.5
      pos_2: weight = 20.0 (unchanged)
      pos_3: weight = 30.0 * 0.75 = 22.5
      lt_1: liquidity_type_id=1 -> matches -> 5.0 * 0.75 = 3.75
      lt_2: liquidity_type_id=1 -> matches -> 8.0 * 0.75 = 6.0

    Expected output:
      pos_1: weight=7.5
      pos_2: weight=20.0
      pos_3: weight=22.5
      lt_1: weight=3.75
      lt_2: weight=6.0
    """
    print("\n" + "="*80)
    print("TEST 3002: Conditional scale_factor (liquidity_type_id=1)")
    print("="*80)

    print("\nManual calculation:")
    print("  Input: pos_1 (10.0, liq=1), pos_2 (20.0, liq=2), pos_3 (30.0, liq=1)")
    print("        lt_1 (5.0, liq=1), lt_2 (8.0, liq=1)")
    print("  Scaling rule: exposure_factor=0.75 WHERE liquidity_type_id=1")
    print("  Step 1: Evaluate criteria")
    print("    pos_1: liq=1 -> matches")
    print("    pos_2: liq=2 -> NO match")
    print("    pos_3: liq=1 -> matches")
    print("    lt_1: liq=1 -> matches")
    print("    lt_2: liq=1 -> matches")
    print("  Step 2: Apply scale_factor to matching rows")
    print("    pos_1: 10.0 * 0.75 = 7.5")
    print("    pos_2: 20.0 (unchanged)")
    print("    pos_3: 30.0 * 0.75 = 22.5")
    print("    lt_1: 5.0 * 0.75 = 3.75")
    print("    lt_2: 8.0 * 0.75 = 6.0")

    expected_pos = {'pos_1': 7.5, 'pos_2': 20.0, 'pos_3': 22.5}
    expected_lt = {'lt_1': 3.75, 'lt_2': 6.0}

    return expected_pos, expected_lt


def test_3003_chained_scale_factors():
    """
    Test 3003: Multiple scaling rules applied in sequence (cumulative)

    Manual calculation based on ORIGINAL_FORMULAS.md (cumulative multiplication):

    Input:
      pos_1: weight=10.0, sub_portfolio_id=sub_A
      pos_2: weight=20.0, sub_portfolio_id=sub_A
      pos_3: weight=30.0, sub_portfolio_id=sub_A
      lt_1: weight=5.0
      lt_2: weight=8.0

    Scaling rule 1: exposure_factor=0.8 (applies to all)
    Scaling rule 2: exposure_factor=1.25 (applies to all)

    Step 1: Apply first scale_factor (ORIGINAL_FORMULAS.md line 735)
      pos_1: cumulative_factor = 1.0 * 0.8 = 0.8, weight = 10.0 * 0.8 = 8.0
      pos_2: cumulative_factor = 1.0 * 0.8 = 0.8, weight = 20.0 * 0.8 = 16.0
      pos_3: cumulative_factor = 1.0 * 0.8 = 0.8, weight = 30.0 * 0.8 = 24.0
      lt_1: cumulative_factor = 1.0 * 0.8 = 0.8, weight = 5.0 * 0.8 = 4.0
      lt_2: cumulative_factor = 1.0 * 0.8 = 0.8, weight = 8.0 * 0.8 = 6.4

    Step 2: Apply second scale_factor (CUMULATIVE - line 735)
      pos_1: cumulative = 0.8 * 1.25 = 1.0, weight = 8.0 * 1.25 = 10.0
      pos_2: cumulative = 0.8 * 1.25 = 1.0, weight = 16.0 * 1.25 = 20.0
      pos_3: cumulative = 0.8 * 1.25 = 1.0, weight = 24.0 * 1.25 = 30.0
      lt_1: cumulative = 0.8 * 1.25 = 1.0, weight = 4.0 * 1.25 = 5.0
      lt_2: cumulative = 0.8 * 1.25 = 1.0, weight = 6.4 * 1.25 = 8.0

    Expected output (back to original due to 0.8 * 1.25 = 1.0):
      pos_1: weight=10.0
      pos_2: weight=20.0
      pos_3: weight=30.0
      lt_1: weight=5.0
      lt_2: weight=8.0
    """
    print("\n" + "="*80)
    print("TEST 3003: Chained scale_factors (0.8x then 1.25x)")
    print("="*80)

    print("\nManual calculation:")
    print("  Input: pos_1 (10.0), pos_2 (20.0), pos_3 (30.0), lt_1 (5.0), lt_2 (8.0)")
    print("  Scaling rule 1: exposure_factor=0.8")
    print("  Scaling rule 2: exposure_factor=1.25")
    print("  Step 1: Apply first scale_factor")
    print("    All positions/lookthroughs: * 0.8")
    print("  Step 2: Apply second scale_factor (CUMULATIVE)")
    print("    All positions/lookthroughs: * 1.25")
    print("  Result: 0.8 * 1.25 = 1.0 (back to original)")

    expected_pos = {'pos_1': 10.0, 'pos_2': 20.0, 'pos_3': 30.0}
    expected_lt = {'lt_1': 5.0, 'lt_2': 8.0}

    return expected_pos, expected_lt


def test_3004_scale_factor_holdings_only():
    """
    Test 3004: Scaling rule with apply_to="holding" (positions only, not lookthroughs)

    Manual calculation based on ORIGINAL_FORMULAS.md:

    Input:
      pos_1: weight=10.0, sub_portfolio_id=sub_A
      pos_2: weight=20.0, sub_portfolio_id=sub_A
      pos_3: weight=30.0, sub_portfolio_id=sub_A
      lt_1: weight=5.0, parent=pos_1, sub_portfolio_id=sub_A
      lt_2: weight=8.0, parent=pos_1, sub_portfolio_id=sub_A

    Scaling rule: exposure_factor=0.5, apply_to="holding"

    Step 1: Check apply_to (gemini.py lines 580-581)
      For positions (mode="position"): apply_to="holding" -> APPLY
      For lookthroughs (mode="lookthrough"): apply_to="holding" -> SKIP

    Step 2: Apply to positions only
      pos_1: weight = 10.0 * 0.5 = 5.0
      pos_2: weight = 20.0 * 0.5 = 10.0
      pos_3: weight = 30.0 * 0.5 = 15.0
      lt_1: weight = 5.0 (unchanged)
      lt_2: weight = 8.0 (unchanged)

    Expected output:
      pos_1: weight=5.0
      pos_2: weight=10.0
      pos_3: weight=15.0
      lt_1: weight=5.0
      lt_2: weight=8.0
    """
    print("\n" + "="*80)
    print("TEST 3004: scale_factor apply_to='holding' (positions only)")
    print("="*80)

    print("\nManual calculation:")
    print("  Input: pos_1 (10.0), pos_2 (20.0), pos_3 (30.0), lt_1 (5.0), lt_2 (8.0)")
    print("  Scaling rule: exposure_factor=0.5, apply_to='holding'")
    print("  Step 1: Check apply_to")
    print("    Positions: apply_to='holding' -> APPLY")
    print("    Lookthroughs: apply_to='holding' -> SKIP")
    print("  Step 2: Apply to positions only")
    print("    pos_1: 10.0 * 0.5 = 5.0")
    print("    pos_2: 20.0 * 0.5 = 10.0")
    print("    pos_3: 30.0 * 0.5 = 15.0")
    print("    lt_1: 5.0 (unchanged)")
    print("    lt_2: 8.0 (unchanged)")

    expected_pos = {'pos_1': 5.0, 'pos_2': 10.0, 'pos_3': 15.0}
    expected_lt = {'lt_1': 5.0, 'lt_2': 8.0}

    return expected_pos, expected_lt


def test_3005_scale_factor_lookthroughs_only():
    """
    Test 3005: Scaling rule with apply_to="reference" (lookthroughs only, not positions)

    Manual calculation based on ORIGINAL_FORMULAS.md:

    Input:
      pos_1: weight=10.0, sub_portfolio_id=sub_A
      pos_2: weight=20.0, sub_portfolio_id=sub_A
      pos_3: weight=30.0, sub_portfolio_id=sub_A
      lt_1: weight=5.0, parent=pos_1, sub_portfolio_id=sub_A
      lt_2: weight=8.0, parent=pos_1, sub_portfolio_id=sub_A

    Scaling rule: exposure_factor=1.5, apply_to="reference"

    Step 1: Check apply_to (gemini.py lines 580-581)
      For positions (mode="position"): apply_to="reference" -> SKIP
      For lookthroughs (mode="lookthrough"): apply_to="reference" -> APPLY

    Step 2: Apply to lookthroughs only
      pos_1: weight = 10.0 (unchanged)
      pos_2: weight = 20.0 (unchanged)
      pos_3: weight = 30.0 (unchanged)
      lt_1: weight = 5.0 * 1.5 = 7.5
      lt_2: weight = 8.0 * 1.5 = 12.0

    Expected output:
      pos_1: weight=10.0
      pos_2: weight=20.0
      pos_3: weight=30.0
      lt_1: weight=7.5
      lt_2: weight=12.0
    """
    print("\n" + "="*80)
    print("TEST 3005: scale_factor apply_to='reference' (lookthroughs only)")
    print("="*80)

    print("\nManual calculation:")
    print("  Input: pos_1 (10.0), pos_2 (20.0), pos_3 (30.0), lt_1 (5.0), lt_2 (8.0)")
    print("  Scaling rule: exposure_factor=1.5, apply_to='reference'")
    print("  Step 1: Check apply_to")
    print("    Positions: apply_to='reference' -> SKIP")
    print("    Lookthroughs: apply_to='reference' -> APPLY")
    print("  Step 2: Apply to lookthroughs only")
    print("    pos_1: 10.0 (unchanged)")
    print("    pos_2: 20.0 (unchanged)")
    print("    pos_3: 30.0 (unchanged)")
    print("    lt_1: 5.0 * 1.5 = 7.5")
    print("    lt_2: 8.0 * 1.5 = 12.0")

    expected_pos = {'pos_1': 10.0, 'pos_2': 20.0, 'pos_3': 30.0}
    expected_lt = {'lt_1': 7.5, 'lt_2': 12.0}

    return expected_pos, expected_lt


def run_system_test(test_name, perspective_id, test_data_file, rules_file):
    """Run the actual system and return results"""
    print(f"\n{'='*80}")
    print(f"RUNNING SYSTEM FOR {test_name}")
    print(f"{'='*80}")

    with open(test_data_file, 'r') as f:
        test_data = json.load(f)

    engine = FastPerspectiveEngine(rules_file)
    results = engine.process(test_data)

    test_config_name = f"test_{perspective_id}"

    if str(perspective_id) not in results['perspective_configurations'].get(test_config_name, {}):
        print(f"  Perspective {perspective_id} not in results (likely all filtered)")
        return {}, {}

    perspective_results = results['perspective_configurations'][test_config_name][str(perspective_id)]['test_container']

    positions = perspective_results.get('positions', {})
    lookthroughs = perspective_results.get('essential_lookthroughs', {})

    print(f"\nSystem output for perspective {perspective_id}:")
    print(f"  Positions: {list(positions.keys())}")
    if positions:
        for pid, data in sorted(positions.items()):
            print(f"    {pid}: weight={data.get('weight', 0):.10f}")

    print(f"  Lookthroughs: {list(lookthroughs.keys())}")
    if lookthroughs:
        for lid, data in sorted(lookthroughs.items()):
            print(f"    {lid}: weight={data.get('weight', 0):.10f}")

    return positions, lookthroughs


def compare_results(expected_pos, expected_lt, actual_pos, actual_lt, test_name):
    """Compare expected vs actual results"""
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
            print(f"  {pid}: expected={expected_weight:.10f}, actual={actual_weight:.10f}, diff={diff:.10f} [{status}]")
            if diff >= 0.0001:
                all_passed = False

    # Compare lookthroughs
    if expected_lt or actual_lt:
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
                print(f"  {lid}: expected={expected_weight:.10f}, actual={actual_weight:.10f}, diff={diff:.10f} [{status}]")
                if diff >= 0.0001:
                    all_passed = False

    if all_passed:
        print(f"\n[PASS] {test_name} PASSED")
    else:
        print(f"\n[FAIL] {test_name} FAILED")

    return all_passed


def main():
    print("=" * 80)
    print("EXPOSURE FACTOR (PER-ROW SCALING) TEST SUITE")
    print("=" * 80)

    all_tests_passed = True

    # Test 3001
    expected_pos_3001, expected_lt_3001 = test_3001_simple_scale_factor_0_5x()
    actual_pos_3001, actual_lt_3001 = run_system_test("TEST 3001", 3001,
                                                        'test_exposure_data.json',
                                                        'test_exposure_rules.json')
    passed_3001 = compare_results(expected_pos_3001, expected_lt_3001,
                                   actual_pos_3001, actual_lt_3001, "TEST 3001")
    all_tests_passed &= passed_3001

    # Test 3002
    expected_pos_3002, expected_lt_3002 = test_3002_conditional_scale_factor()
    actual_pos_3002, actual_lt_3002 = run_system_test("TEST 3002", 3002,
                                                        'test_exposure_data.json',
                                                        'test_exposure_rules.json')
    passed_3002 = compare_results(expected_pos_3002, expected_lt_3002,
                                   actual_pos_3002, actual_lt_3002, "TEST 3002")
    all_tests_passed &= passed_3002

    # Test 3003
    expected_pos_3003, expected_lt_3003 = test_3003_chained_scale_factors()
    actual_pos_3003, actual_lt_3003 = run_system_test("TEST 3003", 3003,
                                                        'test_exposure_data.json',
                                                        'test_exposure_rules.json')
    passed_3003 = compare_results(expected_pos_3003, expected_lt_3003,
                                   actual_pos_3003, actual_lt_3003, "TEST 3003")
    all_tests_passed &= passed_3003

    # Test 3004
    expected_pos_3004, expected_lt_3004 = test_3004_scale_factor_holdings_only()
    actual_pos_3004, actual_lt_3004 = run_system_test("TEST 3004", 3004,
                                                        'test_exposure_data.json',
                                                        'test_exposure_rules.json')
    passed_3004 = compare_results(expected_pos_3004, expected_lt_3004,
                                   actual_pos_3004, actual_lt_3004, "TEST 3004")
    all_tests_passed &= passed_3004

    # Test 3005
    expected_pos_3005, expected_lt_3005 = test_3005_scale_factor_lookthroughs_only()
    actual_pos_3005, actual_lt_3005 = run_system_test("TEST 3005", 3005,
                                                        'test_exposure_data.json',
                                                        'test_exposure_rules.json')
    passed_3005 = compare_results(expected_pos_3005, expected_lt_3005,
                                   actual_pos_3005, actual_lt_3005, "TEST 3005")
    all_tests_passed &= passed_3005

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Test 3001 (Simple 0.5x): {'PASSED' if passed_3001 else 'FAILED'}")
    print(f"Test 3002 (Conditional): {'PASSED' if passed_3002 else 'FAILED'}")
    print(f"Test 3003 (Chained 0.8x * 1.25x): {'PASSED' if passed_3003 else 'FAILED'}")
    print(f"Test 3004 (Holdings only): {'PASSED' if passed_3004 else 'FAILED'}")
    print(f"Test 3005 (Lookthroughs only): {'PASSED' if passed_3005 else 'FAILED'}")

    if all_tests_passed:
        print("\n[SUCCESS] ALL EXPOSURE FACTOR TESTS PASSED!")
    else:
        print("\n[ERROR] SOME TESTS FAILED!")

    return all_tests_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
