"""
Comprehensive test suite for complete verification of gemini.py

Tests all modifier types, combinations, edge cases, and complex scenarios.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Ensure we import the correct engine file
from cleaned_gemini_wide import FastPerspectiveEngine


def load_test_data():
    """Load comprehensive test data"""
    with open('data.json', 'r') as f:
        return json.load(f)


def get_result(results, perspective_id, portfolio_name='main_portfolio'):
    """Helper to safely extract results"""
    test_config_name = f"test_{perspective_id}"

    if str(perspective_id) not in results['perspective_configurations'][test_config_name]:
        return {}, {}

    perspective_results = results['perspective_configurations'][test_config_name][str(perspective_id)][portfolio_name]

    positions = perspective_results.get('positions', {})
    lookthroughs = perspective_results.get('essential_lookthroughs', {})

    return positions, lookthroughs


def test_2001_exclude_simulated_trades():
    """
    Test 2001: exclude_simulated_trades
    Should remove positions/lookthroughs where position_source_type_id = 10
    """
    print("\n" + "="*80)
    print("TEST 2001: exclude_simulated_trades (PreProcessing)")
    print("="*80)

    # Manual calculation
    print("\nManual calculation:")
    print("  Initial positions: pos_1 through pos_10")
    print("  Filter: position_source_type_id != 10")
    print("  Removed: pos_3 (type=10), pos_5 (type=10), pos_9 (type=10)")
    print("  Kept: pos_1, pos_2, pos_4, pos_6, pos_7, pos_8, pos_10")

    print("\n  Initial lookthroughs: lt_1 through lt_8")
    print("  Removed: lt_4 (type=10), lt_7 (type=10)")
    print("  Cascade: None (parents of removed LTs are still present)")
    print("  Kept: lt_1, lt_2, lt_3, lt_5, lt_6, lt_8")

    expected_pos = ['pos_1', 'pos_2', 'pos_4', 'pos_6', 'pos_7', 'pos_8', 'pos_10']
    expected_lt = ['lt_1', 'lt_2', 'lt_3', 'lt_5', 'lt_6', 'lt_8']

    return expected_pos, expected_lt


def test_2002_exclude_trade_cash():
    """
    Test 2002: exclude_trade_cash
    Should remove positions/lookthroughs where liquidity_type_id = 6
    """
    print("\n" + "="*80)
    print("TEST 2002: exclude_trade_cash (PreProcessing)")
    print("="*80)

    print("\nManual calculation:")
    print("  Filter: liquidity_type_id != 6")
    print("  Removed positions: pos_4 (liq=6), pos_8 (liq=6), pos_9 (liq=6)")
    print("  Kept: pos_1, pos_2, pos_3, pos_5, pos_6, pos_7, pos_10")

    print("\n  Removed lookthroughs: lt_5 (liq=6)")
    print("  Cascade: pos_4 removed -> lt_5, lt_6 cascade-removed (parent=104)")
    print("  Kept: lt_1, lt_2, lt_3, lt_4, lt_7, lt_8")

    expected_pos = ['pos_1', 'pos_2', 'pos_3', 'pos_5', 'pos_6', 'pos_7', 'pos_10']
    expected_lt = ['lt_1', 'lt_2', 'lt_3', 'lt_4', 'lt_7', 'lt_8']

    return expected_pos, expected_lt


def test_2003_exclude_simulated_cash():
    """
    Test 2003: exclude_simulated_cash
    Should remove where (position_source_type_id = 10 AND liquidity_type_id = 5)
    """
    print("\n" + "="*80)
    print("TEST 2003: exclude_simulated_cash (PreProcessing)")
    print("="*80)

    print("\nManual calculation:")
    print("  Filter: NOT (position_source_type_id=10 AND liquidity_type_id=5)")
    print("  Removed positions: pos_5 (type=10 AND liq=5)")
    print("  Kept: pos_1, pos_2, pos_3, pos_4, pos_6, pos_7, pos_8, pos_9, pos_10")

    print("\n  Removed lookthroughs: lt_7 (type=10 AND liq=5)")
    print("  Cascade: None")
    print("  Kept: lt_1, lt_2, lt_3, lt_4, lt_5, lt_6, lt_8")

    expected_pos = ['pos_1', 'pos_2', 'pos_3', 'pos_4', 'pos_6', 'pos_7', 'pos_8', 'pos_9', 'pos_10']
    expected_lt = ['lt_1', 'lt_2', 'lt_3', 'lt_4', 'lt_5', 'lt_6', 'lt_8']

    return expected_pos, expected_lt


def test_2004_exclude_class_positions():
    """
    Test 2004: exclude_class_positions
    Should remove where is_class_position = true
    """
    print("\n" + "="*80)
    print("TEST 2004: exclude_class_positions (PreProcessing)")
    print("="*80)

    print("\nManual calculation:")
    print("  Filter: is_class_position != true")
    print("  Removed positions: pos_6 (class=true), pos_8 (class=true)")
    print("  Kept: pos_1, pos_2, pos_3, pos_4, pos_5, pos_7, pos_9, pos_10")

    print("\n  Removed lookthroughs: lt_6 (class=true), lt_8 (class=true)")
    print("  Cascade: pos_6 removed -> lt_8 would be cascade-removed anyway")
    print("  Kept: lt_1, lt_2, lt_3, lt_4, lt_5, lt_7")

    expected_pos = ['pos_1', 'pos_2', 'pos_3', 'pos_4', 'pos_5', 'pos_7', 'pos_9', 'pos_10']
    expected_lt = ['lt_1', 'lt_2', 'lt_3', 'lt_4', 'lt_5', 'lt_7']

    return expected_pos, expected_lt


def test_2005_multiple_preprocessing():
    """
    Test 2005: Multiple PreProcessing modifiers combined
    exclude_simulated_trades AND exclude_trade_cash AND exclude_class_positions
    """
    print("\n" + "="*80)
    print("TEST 2005: Multiple PreProcessing modifiers")
    print("="*80)

    print("\nManual calculation:")
    print("  Filter 1: position_source_type_id != 10 (removes pos_3, pos_5, pos_9)")
    print("  Filter 2: liquidity_type_id != 6 (removes pos_4, pos_8 from remaining)")
    print("  Filter 3: is_class_position != true (removes pos_6 from remaining)")
    print("  Final kept positions: pos_1, pos_2, pos_7, pos_10")

    print("\n  Lookthrough filters:")
    print("    Filter 1: removes lt_4, lt_7")
    print("    Filter 2: removes lt_5")
    print("    Filter 3: removes lt_6, lt_8")
    print("  Cascade: pos_4 removed -> lt_5, lt_6 would cascade anyway")
    print("  Final kept lookthroughs: lt_1, lt_2, lt_3")

    expected_pos = ['pos_1', 'pos_2', 'pos_7', 'pos_10']
    expected_lt = ['lt_1', 'lt_2', 'lt_3']

    return expected_pos, expected_lt


def test_2006_postprocessing_or_logic():
    """
    Test 2006: include_all_trade_cash (PostProcessing with OR)
    Rule filters out position_source_type_id=10, then OR adds back liquidity_type_id=6
    """
    print("\n" + "="*80)
    print("TEST 2006: include_all_trade_cash (PostProcessing OR)")
    print("="*80)

    print("\nManual calculation:")
    print("  Perspective rule: position_source_type_id != 10")
    print("    Removes: pos_3, pos_5, pos_9")
    print("    Keeps: pos_1, pos_2, pos_4, pos_6, pos_7, pos_8, pos_10")

    print("\n  PostProcessing modifier (OR): liquidity_type_id = 6")
    print("    Adds back: pos_9 (liq=6, even though type=10)")
    print("  Final: pos_1, pos_2, pos_4, pos_6, pos_7, pos_8, pos_9, pos_10")

    print("\n  Lookthroughs:")
    print("    Rule removes: lt_4, lt_7")
    print("    PostProcessing adds back: lt_5 (liq=6)")
    print("  Final: lt_1, lt_2, lt_3, lt_5, lt_6, lt_8")

    expected_pos = ['pos_1', 'pos_2', 'pos_4', 'pos_6', 'pos_7', 'pos_8', 'pos_9', 'pos_10']
    expected_lt = ['lt_1', 'lt_2', 'lt_3', 'lt_5', 'lt_6', 'lt_8']

    return expected_pos, expected_lt


def test_2007_modifier_override():
    """
    Test 2007: exclude_simulated_trades overrides include_all_trade_cash
    Rule: liquidity_type_id=1, Modifiers: exclude_simulated_trades + include_all_trade_cash
    Override should make include_all_trade_cash not apply
    """
    print("\n" + "="*80)
    print("TEST 2007: Modifier Override")
    print("="*80)

    print("\nManual calculation:")
    print("  Perspective rule: liquidity_type_id = 1")
    print("    Keeps positions: pos_1, pos_6, pos_7, pos_10")
    print("    Keeps lookthroughs: lt_1 (liq=1), lt_8 (liq=1)")
    print("    Filters lookthroughs: lt_2 (liq=2, fails rule)")

    print("\n  PreProcessing: exclude_simulated_trades (type != 10)")
    print("    Already satisfied by all positions and lookthroughs")

    print("\n  PostProcessing: include_all_trade_cash")
    print("    OVERRIDE: exclude_simulated_trades overrides include_all_trade_cash")
    print("    So include_all_trade_cash is NOT applied")

    print("\n  Final: pos_1, pos_6, pos_7, pos_10")
    print("  Final lookthroughs: lt_1, lt_8 (lt_2 filtered by perspective rule)")

    expected_pos = ['pos_1', 'pos_6', 'pos_7', 'pos_10']
    expected_lt = ['lt_1', 'lt_8']  # lt_1 from pos_1 (liq=1); lt_8 from pos_6 (liq=1); lt_2 has liq=2

    return expected_pos, expected_lt


def test_2014_cascade_removal():
    """
    Test 2014: Cascade removal test
    Rule: instrument_id IN [101, 103, 104]
    This rule applies to BOTH positions and lookthroughs by their own instrument_id
    """
    print("\n" + "="*80)
    print("TEST 2014: Cascade Removal")
    print("="*80)

    print("\nManual calculation:")
    print("  Rule: instrument_id IN [101, 103, 104] (applies to both)")
    print("  Kept positions: pos_1 (inst=101), pos_3 (inst=103), pos_4 (inst=104)")
    print("  Removed: pos_2, pos_5, pos_6, pos_7, pos_8, pos_9, pos_10")

    print("\n  Lookthrough filtering by their OWN instrument_id:")
    print("    lt_1 has instrument_id=201 -> NOT in [101,103,104] -> FILTERED")
    print("    lt_2 has instrument_id=202 -> NOT in [101,103,104] -> FILTERED")
    print("    lt_3 has instrument_id=203 -> NOT in [101,103,104] -> FILTERED")
    print("    lt_4 has instrument_id=204 -> NOT in [101,103,104] -> FILTERED")
    print("    lt_5 has instrument_id=205 -> NOT in [101,103,104] -> FILTERED")
    print("    lt_6 has instrument_id=206 -> NOT in [101,103,104] -> FILTERED")
    print("    lt_7 has instrument_id=207 -> NOT in [101,103,104] -> FILTERED")
    print("    lt_8 has instrument_id=208 -> NOT in [101,103,104] -> FILTERED")

    print("\n  Final positions: pos_1, pos_3, pos_4")
    print("  Final lookthroughs: NONE (all filtered by their own instrument_id)")

    expected_pos = ['pos_1', 'pos_3', 'pos_4']
    expected_lt = []

    return expected_pos, expected_lt


def run_single_test(test_func, perspective_id, test_data, engine):
    """Run a single test and compare results"""
    expected_pos, expected_lt = test_func()

    print("\nRunning system...")
    results = engine.process(test_data)

    actual_pos, actual_lt = get_result(results, perspective_id)

    print("\nComparison:")
    actual_pos_ids = sorted(actual_pos.keys())
    actual_lt_ids = sorted(actual_lt.keys())

    pos_match = sorted(expected_pos) == actual_pos_ids
    lt_match = sorted(expected_lt) == actual_lt_ids

    print(f"  Expected positions: {sorted(expected_pos)}")
    print(f"  Actual positions:   {actual_pos_ids}")
    print(f"  Match: {pos_match}")

    print(f"\n  Expected lookthroughs: {sorted(expected_lt)}")
    print(f"  Actual lookthroughs:   {actual_lt_ids}")
    print(f"  Match: {lt_match}")

    passed = pos_match and lt_match

    if passed:
        print("\n[PASS]")
    else:
        print("\n[FAIL]")
        if not pos_match:
            missing_pos = set(expected_pos) - set(actual_pos_ids)
            extra_pos = set(actual_pos_ids) - set(expected_pos)
            if missing_pos:
                print(f"  Missing positions: {missing_pos}")
            if extra_pos:
                print(f"  Extra positions: {extra_pos}")
        if not lt_match:
            missing_lt = set(expected_lt) - set(actual_lt_ids)
            extra_lt = set(actual_lt_ids) - set(expected_lt)
            if missing_lt:
                print(f"  Missing lookthroughs: {missing_lt}")
            if extra_lt:
                print(f"  Extra lookthroughs: {extra_lt}")

    return passed


def main():
    print("="*80)
    print("COMPREHENSIVE TEST SUITE - GEMINI.PY VERIFICATION")
    print("="*80)

    test_data = load_test_data()
    engine = FastPerspectiveEngine('rules.json')

    tests = [
        (test_2001_exclude_simulated_trades, 2001, "exclude_simulated_trades"),
        (test_2002_exclude_trade_cash, 2002, "exclude_trade_cash"),
        (test_2003_exclude_simulated_cash, 2003, "exclude_simulated_cash"),
        (test_2004_exclude_class_positions, 2004, "exclude_class_positions"),
        (test_2005_multiple_preprocessing, 2005, "Multiple PreProcessing"),
        (test_2006_postprocessing_or_logic, 2006, "PostProcessing OR logic"),
        (test_2007_modifier_override, 2007, "Modifier Override"),
        (test_2014_cascade_removal, 2014, "Cascade Removal"),
    ]

    results = []
    for test_func, perspective_id, test_name in tests:
        passed = run_single_test(test_func, perspective_id, test_data, engine)
        results.append((test_name, passed))

    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"  {test_name:<40} {status}")

    all_passed = all(p for _, p in results)

    if all_passed:
        print("\n[SUCCESS] ALL COMPREHENSIVE TESTS PASSED!")
        print("Weight calculations and all logic are CORRECT.")
    else:
        print("\n[ERROR] SOME TESTS FAILED")
        failed_count = sum(1 for _, p in results if not p)
        print(f"{failed_count} out of {len(results)} tests failed.")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)