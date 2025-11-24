"""
Debug test to compare Deep Lookthrough Hierarchy outputs between implementations.
"""

import json
from gemini import FastPerspectiveEngine as OriginalEngine
from gemini_wide_format import FastPerspectiveEngine as WideEngine


def generate_deep_lookthrough_test():
    """Generate test data with deep lookthrough hierarchy."""
    positions = {}
    lookthroughs = {}

    # Create parent position
    positions["pos_root"] = {
        "identifier": "pos_root",
        "instrument_identifier": 100,
        "instrument_id": 100,
        "sub_portfolio_id": "sub_A",
        "weight": 100.0,
        "position_source_type_id": 1,
        "liquidity_type_id": 1,
        "is_class_position": False,
        "is_blocked": False
    }

    # Create lookthrough hierarchy (depth=5, breadth=3)
    current_id = 200
    for level in range(5):
        for branch in range(3 ** level):
            parent_id = 100 if level == 0 else 200 + (branch // 3) + sum(3 ** i for i in range(level))
            lt_key = f"lt_{current_id}"
            lookthroughs[lt_key] = {
                "identifier": lt_key,
                "instrument_identifier": current_id,
                "instrument_id": current_id,
                "parent_instrument_id": parent_id,
                "sub_portfolio_id": "sub_A",
                "weight": 100.0 / (3 ** (level + 1)),
                "position_source_type_id": 1,
                "liquidity_type_id": 1,
                "is_class_position": False,
                "is_blocked": False
            }
            current_id += 1

    return {
        "instrument_identifier_type": "instrument_id",
        "position_weight_labels": ["weight"],
        "lookthrough_weight_labels": ["weight"],
        "perspective_configurations": {
            "test_3001": {"3001": []}
        },
        "test_container": {
            "position_type": "test_container",
            "positions": positions,
            "essential_lookthroughs": lookthroughs,
            "sub_portfolios": [{"id": "sub_A", "name": "Sub Portfolio A"}]
        }
    }


def generate_simple_scaling_rules():
    """Generate simple scaling rule."""
    return {
        "perspectives": {
            "3001": {
                "id": 3001,
                "name": "Test 3001: Simple scale_factor 0.5x",
                "rules": [
                    {
                        "is_scaling_rule": True,
                        "scale_factor": 0.5,
                        "criteria": json.dumps({
                            "required_columns": {},
                            "table_name": "position_data",
                            "column": "instrument_id",
                            "operator_type": ">",
                            "value": 0
                        }),
                        "apply_to": "both"
                    }
                ]
            }
        },
        "modifiers": {},
        "default_modifiers": [],
        "modifier_overrides": {}
    }


# Generate test data
print("Generating test data...")
test_data = generate_deep_lookthrough_test()
test_rules = generate_simple_scaling_rules()

# Save rules
with open("debug_lookthrough_rules.json", "w") as f:
    json.dump(test_rules, f, indent=2)

print(f"\nTest has {len(test_data['test_container']['positions'])} position(s)")
print(f"Test has {len(test_data['test_container']['essential_lookthroughs'])} lookthrough(s)")

# Run original implementation
print("\n" + "="*80)
print("ORIGINAL (gemini.py)")
print("="*80)
try:
    orig_engine = OriginalEngine(rules_path="debug_lookthrough_rules.json")
    orig_result = orig_engine.process(test_data)

    # Extract result
    orig_positions = orig_result["perspective_configurations"]["test_3001"]["3001"]["test_container"]["positions"]
    orig_lts = orig_result["perspective_configurations"]["test_3001"]["3001"]["test_container"].get("essential_lookthroughs", {})

    print(f"\nPositions returned: {len(orig_positions)}")
    for pid, data in sorted(orig_positions.items()):
        print(f"  {pid}: weight={data.get('weight', 'N/A'):.4f}")

    print(f"\nLookthroughs returned: {len(orig_lts)}")
    for lid, data in sorted(list(orig_lts.items())[:10]):  # Show first 10
        print(f"  {lid}: weight={data.get('weight', 'N/A'):.6f}")
    if len(orig_lts) > 10:
        print(f"  ... and {len(orig_lts) - 10} more")

    # Save full result
    with open("debug_orig_result.json", "w") as f:
        json.dump(orig_result, f, indent=2, default=str)
    print("\nFull result saved to: debug_orig_result.json")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

# Run wide format implementation
print("\n" + "="*80)
print("WIDE FORMAT (gemini_wide_format.py)")
print("="*80)
try:
    wide_engine = WideEngine(rules_path="debug_lookthrough_rules.json")
    wide_result = wide_engine.process(test_data)

    # Extract result
    wide_positions = wide_result["perspective_configurations"]["test_3001"]["3001"]["test_container"]["positions"]
    wide_lts = wide_result["perspective_configurations"]["test_3001"]["3001"]["test_container"].get("essential_lookthroughs", {})

    print(f"\nPositions returned: {len(wide_positions)}")
    for pid, data in sorted(wide_positions.items()):
        print(f"  {pid}: weight={data.get('weight', 'N/A'):.4f}")

    print(f"\nLookthroughs returned: {len(wide_lts)}")
    for lid, data in sorted(list(wide_lts.items())[:10]):  # Show first 10
        print(f"  {lid}: weight={data.get('weight', 'N/A'):.6f}")
    if len(wide_lts) > 10:
        print(f"  ... and {len(wide_lts) - 10} more")

    # Save full result
    with open("debug_wide_result.json", "w") as f:
        json.dump(wide_result, f, indent=2, default=str)
    print("\nFull result saved to: debug_wide_result.json")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

# Compare
print("\n" + "="*80)
print("COMPARISON")
print("="*80)

try:
    print(f"Position count match: {len(orig_positions) == len(wide_positions)}")
    print(f"Lookthrough count match: {len(orig_lts) == len(wide_lts)}")

    # Compare position weights
    pos_match = True
    for pid in orig_positions:
        if pid in wide_positions:
            orig_w = orig_positions[pid].get('weight', 0)
            wide_w = wide_positions[pid].get('weight', 0)
            if abs(orig_w - wide_w) > 0.0001:
                print(f"  Position {pid}: orig={orig_w:.6f}, wide={wide_w:.6f} MISMATCH")
                pos_match = False

    if pos_match:
        print("Position weights: ALL MATCH")

    # Compare lookthrough weights
    lt_match = True
    for lid in list(orig_lts.keys())[:10]:
        if lid in wide_lts:
            orig_w = orig_lts[lid].get('weight', 0)
            wide_w = wide_lts[lid].get('weight', 0)
            if abs(orig_w - wide_w) > 0.0001:
                print(f"  Lookthrough {lid}: orig={orig_w:.6f}, wide={wide_w:.6f} MISMATCH")
                lt_match = False

    if lt_match:
        print("Lookthrough weights: ALL MATCH (first 10)")

except Exception as e:
    print(f"Comparison failed: {e}")
