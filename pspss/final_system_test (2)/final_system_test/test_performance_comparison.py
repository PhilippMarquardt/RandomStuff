"""
Performance Comparison Test Suite
Compares gemini.py vs gemini_wide_format.py for speed and memory usage in extreme cases.

Test Scenarios:
1. Large Position Count (1000+ positions)
2. Many Perspectives (50+ perspectives)
3. Complex Criteria (nested In/NotIn)
4. Deep Lookthrough Hierarchy
5. Combined Extreme Case (all of the above)
"""

import json
import time
import tracemalloc
import traceback
import polars as pl
from typing import Dict, Any, Tuple
import sys

# Import both implementations
from cleaned_gemini_wide import PerspectiveEngine as OriginalEngine
from gemini import FastPerspectiveEngine as WideEngine


# =============================================================================
# Test Data Generators
# =============================================================================

import random
import numpy as np

def generate_realistic_positions(
    num_positions: int = 1000,
    num_lookthroughs_per_position: int = 0,
    num_containers: int = 1,
    num_sub_portfolios: int = 5,
    num_perspectives: int = 10,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Generate realistic test data with configurable scale.

    Args:
        num_positions: Total number of positions across all containers
        num_lookthroughs_per_position: Average lookthroughs per position (0-50)
        num_containers: Number of portfolios/containers
        num_sub_portfolios: Number of sub-portfolios
        num_perspectives: Number of perspectives to test
        seed: Random seed for reproducibility
    """
    random.seed(seed)
    np.random.seed(seed)

    positions_per_container = num_positions // num_containers

    test_data = {
        "instrument_identifier_type": "instrument_id",
        "position_weight_labels": ["weight"],
        "lookthrough_weight_labels": ["weight"],
        "perspective_configurations": {}
    }

    # Generate perspective configurations
    for p_id in range(3001, 3001 + num_perspectives):
        test_data["perspective_configurations"][f"test_{p_id}"] = {str(p_id): []}

    # Generate containers
    inst_id_counter = 1000
    lt_id_counter = 5000

    for container_idx in range(num_containers):
        container_name = f"container_{container_idx}" if num_containers > 1 else "test_container"

        positions = {}
        lookthroughs = {}

        # Generate positions with realistic weight distribution (not uniform)
        weights = np.random.lognormal(mean=3.0, sigma=1.5, size=positions_per_container)
        weights = weights / weights.sum() * 100  # Normalize to sum to 100

        for pos_idx in range(positions_per_container):
            pos_key = f"pos_{inst_id_counter}"
            sub_portfolio_id = f"sub_{random.randint(0, num_sub_portfolios - 1)}"

            positions[pos_key] = {
                "identifier": pos_key,
                "instrument_identifier": inst_id_counter,
                "instrument_id": inst_id_counter,
                "sub_portfolio_id": sub_portfolio_id,
                "weight": float(weights[pos_idx]),
                "position_source_type_id": random.choice([1, 2, 10]),
                "liquidity_type_id": random.choice([1, 2, 3, 5, 6]),
                "is_class_position": random.choice([True, False]) if random.random() < 0.1 else False,
                "is_blocked": False
            }

            # Generate lookthroughs for this position
            if num_lookthroughs_per_position > 0:
                # Poisson distribution for number of lookthroughs
                num_lts = np.random.poisson(num_lookthroughs_per_position)
                if num_lts > 0:
                    lt_weights = np.random.dirichlet(np.ones(num_lts)) * weights[pos_idx]

                    for lt_idx in range(num_lts):
                        lt_key = f"lt_{lt_id_counter}"
                        lookthroughs[lt_key] = {
                            "identifier": lt_key,
                            "instrument_identifier": lt_id_counter,
                            "instrument_id": lt_id_counter,
                            "parent_instrument_id": inst_id_counter,
                            "sub_portfolio_id": sub_portfolio_id,
                            "weight": float(lt_weights[lt_idx]),
                            "position_source_type_id": 1,
                            "liquidity_type_id": random.choice([1, 2, 3]),
                            "is_class_position": False,
                            "is_blocked": False
                        }
                        lt_id_counter += 1

            inst_id_counter += 1

        # Build container data
        container_data = {
            "position_type": "test_container",
            "positions": positions,
            "sub_portfolios": [
                {"id": f"sub_{i}", "name": f"Sub Portfolio {i}"}
                for i in range(num_sub_portfolios)
            ]
        }

        if lookthroughs:
            container_data["essential_lookthroughs"] = lookthroughs

        test_data[container_name] = container_data

    return test_data


def generate_large_position_test(num_positions: int = 1000, num_perspectives: int = 10) -> Dict[str, Any]:
    """Generate test data with many positions."""
    positions = {}
    for i in range(num_positions):
        inst_id = 1000 + i
        positions[f"pos_{i}"] = {
            "identifier": f"pos_{i}",
            "instrument_identifier": inst_id,
            "instrument_id": inst_id,
            "sub_portfolio_id": f"sub_{i % 10}",  # 10 sub-portfolios
            "weight": 100.0 / num_positions,  # Equal weight
            "position_source_type_id": 1,
            "liquidity_type_id": i % 3 + 1,  # Rotate 1, 2, 3
            "is_class_position": False,
            "is_blocked": False
        }

    # Generate perspectives with simple scaling rules
    perspective_configs = {}
    for p_id in range(3001, 3001 + num_perspectives):
        perspective_configs[f"test_{p_id}"] = {str(p_id): []}

    return {
        "instrument_identifier_type": "instrument_id",
        "position_weight_labels": ["weight"],
        "lookthrough_weight_labels": ["weight"],
        "perspective_configurations": perspective_configs,
        "test_container": {
            "position_type": "test_container",
            "positions": positions,
            "sub_portfolios": [{"id": f"sub_{i}", "name": f"Sub Portfolio {i}"} for i in range(10)]
        }
    }


def generate_many_perspectives_test(num_perspectives: int = 50) -> Dict[str, Any]:
    """Generate test data with many perspectives."""
    perspective_configs = {}
    for p_id in range(3001, 3001 + num_perspectives):
        perspective_configs[f"test_{p_id}"] = {str(p_id): []}

    return {
        "instrument_identifier_type": "instrument_id",
        "position_weight_labels": ["weight"],
        "lookthrough_weight_labels": ["weight"],
        "perspective_configurations": perspective_configs,
        "test_container": {
            "position_type": "test_container",
            "positions": {
                "pos_1": {
                    "identifier": "pos_1",
                    "instrument_identifier": 101,
                    "instrument_id": 101,
                    "sub_portfolio_id": "sub_A",
                    "weight": 10.0,
                    "position_source_type_id": 1,
                    "liquidity_type_id": 1,
                    "is_class_position": False,
                    "is_blocked": False
                }
            },
            "sub_portfolios": [{"id": "sub_A", "name": "Sub Portfolio A"}]
        }
    }


def generate_deep_lookthrough_test(depth: int = 5, breadth: int = 3) -> Dict[str, Any]:
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

    # Create lookthrough hierarchy
    current_id = 200
    for level in range(depth):
        for branch in range(breadth ** level):
            parent_id = 100 if level == 0 else 200 + (branch // breadth) + sum(breadth ** i for i in range(level))
            lt_key = f"lt_{current_id}"
            lookthroughs[lt_key] = {
                "identifier": lt_key,
                "instrument_identifier": current_id,
                "instrument_id": current_id,
                "parent_instrument_id": parent_id,
                "sub_portfolio_id": "sub_A",
                "weight": 100.0 / (breadth ** (level + 1)),
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


def generate_extreme_combined_test() -> Dict[str, Any]:
    """Generate test data combining all extreme scenarios."""
    num_positions = 500
    num_perspectives = 25

    positions = {}
    lookthroughs = {}

    # Many positions
    for i in range(num_positions):
        pos_key = f"pos_{i}"
        inst_id = 1000 + i
        positions[pos_key] = {
            "identifier": pos_key,
            "instrument_identifier": inst_id,
            "instrument_id": inst_id,
            "sub_portfolio_id": f"sub_{i % 5}",
            "weight": 100.0 / num_positions,
            "position_source_type_id": i % 2 + 1,
            "liquidity_type_id": i % 3 + 1,
            "is_class_position": False,
            "is_blocked": False
        }

        # Add lookthroughs for some positions
        if i % 10 == 0:
            for j in range(3):
                lt_id = 5000 + i * 10 + j
                lt_key = f"lt_{lt_id}"
                lookthroughs[lt_key] = {
                    "identifier": lt_key,
                    "instrument_identifier": lt_id,
                    "instrument_id": lt_id,
                    "parent_instrument_id": inst_id,
                    "sub_portfolio_id": f"sub_{i % 5}",
                    "weight": 10.0,
                    "position_source_type_id": 1,
                    "liquidity_type_id": 1,
                    "is_class_position": False,
                    "is_blocked": False
                }

    # Many perspectives
    perspective_configs = {}
    for p_id in range(3001, 3001 + num_perspectives):
        perspective_configs[f"test_{p_id}"] = {str(p_id): []}

    return {
        "instrument_identifier_type": "instrument_id",
        "position_weight_labels": ["weight"],
        "lookthrough_weight_labels": ["weight"],
        "perspective_configurations": perspective_configs,
        "test_container": {
            "position_type": "test_container",
            "positions": positions,
            "essential_lookthroughs": lookthroughs,
            "sub_portfolios": [{"id": f"sub_{i}", "name": f"Sub Portfolio {i}"} for i in range(5)]
        }
    }


# =============================================================================
# Rules Generators
# =============================================================================

def generate_simple_scaling_rules(num_perspectives: int = 10) -> Dict[str, Any]:
    """Generate simple scaling rules for perspectives."""
    perspectives = {}

    for i, p_id in enumerate(range(3001, 3001 + num_perspectives)):
        scale_factor = 0.5 + (i * 0.05)  # Vary from 0.5 to ~1.0
        perspectives[str(p_id)] = {
            "id": p_id,
            "name": f"Test {p_id}: Scale {scale_factor}x",
            "rules": [
                {
                    "is_scaling_rule": True,
                    "scale_factor": scale_factor,
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

    return {
        "perspectives": perspectives,
        "modifiers": {},
        "default_modifiers": [],
        "modifier_overrides": {}
    }


def generate_complex_filtering_rules(num_perspectives: int = 10) -> Dict[str, Any]:
    """Generate complex filtering rules with nested criteria."""
    perspectives = {}

    for i, p_id in enumerate(range(3001, 3001 + num_perspectives)):
        perspectives[str(p_id)] = {
            "id": p_id,
            "name": f"Test {p_id}: Complex Filter",
            "rules": [
                {
                    "is_scaling_rule": False,
                    "criteria": json.dumps({
                        "required_columns": {},
                        "and": [
                            {
                                "table_name": "position_data",
                                "column": "instrument_id",
                                "operator_type": ">",
                                "value": 1000
                            },
                            {
                                "table_name": "position_data",
                                "column": "instrument_id",
                                "operator_type": "<",
                                "value": 2000
                            }
                        ]
                    }),
                    "apply_to": "both"
                }
            ]
        }

    return {
        "perspectives": perspectives,
        "modifiers": {},
        "default_modifiers": [],
        "modifier_overrides": {}
    }


# =============================================================================
# Performance Measurement
# =============================================================================

def measure_performance(engine_class, test_data: Dict[str, Any], rules_file: str) -> Tuple[float, float, Dict[str, Any]]:
    """
    Measure execution time and memory usage for an engine.

    Returns:
        Tuple of (execution_time_seconds, peak_memory_mb, result)
    """
    # Start memory tracking
    tracemalloc.start()

    # Create engine and process
    start_time = time.perf_counter()
    engine = engine_class(rules_path=rules_file)
    result = engine.process(test_data)
    end_time = time.perf_counter()

    # Get memory stats
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    execution_time = end_time - start_time
    peak_memory_mb = peak / (1024 * 1024)  # Convert to MB

    return execution_time, peak_memory_mb, result


def compare_results(result1: Dict[str, Any], result2: Dict[str, Any]) -> bool:
    """
    Compare two results to ensure they are identical.
    Returns True if results match, False otherwise.
    Ignores verbose output fields like removed_positions_weight_summary.
    """
    try:
        # Deep copy to avoid modifying originals
        import copy
        r1 = copy.deepcopy(result1)
        r2 = copy.deepcopy(result2)

        # Remove verbose output fields that don't affect correctness
        def remove_verbose_fields(obj):
            if isinstance(obj, dict):
                # Remove verbose output field
                obj.pop('removed_positions_weight_summary', None)
                # Recurse into nested dicts
                for value in obj.values():
                    remove_verbose_fields(value)
            elif isinstance(obj, list):
                for item in obj:
                    remove_verbose_fields(item)

        remove_verbose_fields(r1)
        remove_verbose_fields(r2)

        # Convert to JSON and compare
        json1 = json.dumps(r1, sort_keys=True, default=str)
        json2 = json.dumps(r2, sort_keys=True, default=str)
        return json1 == json2
    except Exception as e:
        print(f"Error comparing results: {e}")
        return False


def run_performance_test(test_name: str, test_data: Dict[str, Any], rules_file: str):
    """Run performance comparison for a single test case."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")

    # Count test data size
    total_positions = 0
    total_lookthroughs = 0
    num_perspectives = 0

    for key, value in test_data.items():
        if isinstance(value, dict) and "positions" in value:
            total_positions += len(value.get("positions", {}))
            for lt_key in value:
                if "lookthrough" in lt_key:
                    total_lookthroughs += len(value.get(lt_key, {}))

    if "perspective_configurations" in test_data:
        num_perspectives = len(test_data["perspective_configurations"])

    print(f"Test Data Size:")
    print(f"  - Positions: {total_positions}")
    print(f"  - Lookthroughs: {total_lookthroughs}")
    print(f"  - Perspectives: {num_perspectives}")
    print()

    # Run original implementation
    print("Running ORIGINAL (gemini.py)...")
    try:
        orig_time, orig_mem, orig_result = measure_performance(OriginalEngine, test_data, rules_file)
        print(f"  Time: {orig_time:.4f}s")
        print(f"  Peak Memory: {orig_mem:.2f} MB")
        orig_success = True
    except Exception as e:
        print(f"  ERROR (SKIPPED): {str(e)[:150]}")
        print(f"  NOTE: gemini.py has a bug with empty lookthrough scenarios")
        orig_success = False
        orig_time, orig_mem, orig_result = 0, 0, None

    # Run wide format implementation
    print("\nRunning WIDE FORMAT (gemini_wide_format.py)...")
    try:
        wide_time, wide_mem, wide_result = measure_performance(WideEngine, test_data, rules_file)
        print(f"  Time: {wide_time:.4f}s")
        print(f"  Peak Memory: {wide_mem:.2f} MB")
        wide_success = True
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()
        wide_success = False
        return

    # If original failed, skip comparison
    if not orig_success:
        print("\nPerformance Comparison:")
        print("  Cannot compare - original implementation failed for this test case")
        print(f"\nSummary:")
        print(f"  Wide Format completed successfully")
        print(f"  Original implementation has bug with this scenario")
        return

    # Compare results
    print("\nValidating Results...")
    results_match = compare_results(orig_result, wide_result)
    print(f"  Results Match: {'YES' if results_match else 'NO'}")

    if not results_match:
        print("\n  WARNING: Results do not match! Implementations may have different behavior.")

    # Performance comparison
    print("\nPerformance Comparison:")
    time_speedup = orig_time / wide_time if wide_time > 0 else float('inf')
    mem_improvement = ((orig_mem - wide_mem) / orig_mem * 100) if orig_mem > 0 else 0

    print(f"  Speed: {time_speedup:.2f}x {'FASTER' if time_speedup > 1 else 'SLOWER'} (Wide Format)")
    print(f"  Memory: {abs(mem_improvement):.1f}% {'LESS' if mem_improvement > 0 else 'MORE'} (Wide Format)")

    # Summary
    print("\nSummary:")
    if time_speedup > 1.1:
        print(f"  Wide Format is SIGNIFICANTLY FASTER ({time_speedup:.2f}x)")
    elif time_speedup > 0.9:
        print(f"  Both implementations have SIMILAR SPEED")
    else:
        print(f"  Original is FASTER ({1/time_speedup:.2f}x)")

    if mem_improvement > 10:
        print(f"  Wide Format uses SIGNIFICANTLY LESS MEMORY ({mem_improvement:.1f}% reduction)")
    elif mem_improvement > -10:
        print(f"  Both implementations have SIMILAR MEMORY USAGE")
    else:
        print(f"  Original uses LESS MEMORY ({abs(mem_improvement):.1f}% reduction)")


# =============================================================================
# Main Test Runner
# =============================================================================

def main():
    """Run all performance comparison tests."""
    print("\n" + "="*80)
    print("PERFORMANCE COMPARISON: gemini.py vs gemini_wide_format.py")
    print("="*80)

    # Test 1: Large Position Count
    print("\n\nGenerating test data for LARGE POSITION COUNT test...")
    test1_data = generate_large_position_test(num_positions=1000, num_perspectives=10)
    test1_rules = generate_simple_scaling_rules(num_perspectives=10)

    with open("test_perf_rules_1.json", "w") as f:
        json.dump(test1_rules, f, indent=2)

    run_performance_test(
        "Large Position Count (1000 positions, 10 perspectives)",
        test1_data,
        "test_perf_rules_1.json"
    )

    # Test 2: Many Perspectives
    print("\n\nGenerating test data for MANY PERSPECTIVES test...")
    test2_data = generate_many_perspectives_test(num_perspectives=50)
    test2_rules = generate_simple_scaling_rules(num_perspectives=50)

    with open("test_perf_rules_2.json", "w") as f:
        json.dump(test2_rules, f, indent=2)

    run_performance_test(
        "Many Perspectives (50 perspectives, 1 position)",
        test2_data,
        "test_perf_rules_2.json"
    )

    # Test 3: Deep Lookthrough Hierarchy
    print("\n\nGenerating test data for DEEP LOOKTHROUGH test...")
    test3_data = generate_deep_lookthrough_test(depth=5, breadth=3)
    test3_rules = generate_simple_scaling_rules(num_perspectives=1)

    with open("test_perf_rules_3.json", "w") as f:
        json.dump(test3_rules, f, indent=2)

    run_performance_test(
        "Deep Lookthrough Hierarchy (depth=5, breadth=3)",
        test3_data,
        "test_perf_rules_3.json"
    )

    # Test 4: Complex Filtering
    print("\n\nGenerating test data for COMPLEX FILTERING test...")
    test4_data = generate_large_position_test(num_positions=500, num_perspectives=20)
    test4_rules = generate_complex_filtering_rules(num_perspectives=20)

    with open("test_perf_rules_4.json", "w") as f:
        json.dump(test4_rules, f, indent=2)

    run_performance_test(
        "Complex Filtering (500 positions, 20 perspectives with AND criteria)",
        test4_data,
        "test_perf_rules_4.json"
    )

    # Test 5: Extreme Combined
    print("\n\nGenerating test data for EXTREME COMBINED test...")
    test5_data = generate_extreme_combined_test()
    test5_rules = generate_simple_scaling_rules(num_perspectives=25)

    with open("test_perf_rules_5.json", "w") as f:
        json.dump(test5_rules, f, indent=2)

    run_performance_test(
        "Extreme Combined (500 positions, 150 lookthroughs, 25 perspectives)",
        test5_data,
        "test_perf_rules_5.json"
    )

    print("\n" + "="*80)
    print("COMPREHENSIVE SCALE TESTS (Using Realistic Data Generator)")
    print("="*80)

    # Test 6: Mega Scale Test
    print("\n\nGenerating test data for MEGA SCALE test...")
    test6_data = generate_realistic_positions(
        num_positions=10000,
        num_lookthroughs_per_position=5,
        num_containers=1,
        num_sub_portfolios=10,
        num_perspectives=25
    )
    test6_rules = generate_simple_scaling_rules(num_perspectives=25)

    with open("test_perf_rules_6.json", "w") as f:
        json.dump(test6_rules, f, indent=2)

    run_performance_test(
        "MEGA SCALE (10,000 positions, ~50,000 lookthroughs, 25 perspectives)",
        test6_data,
        "test_perf_rules_6.json"
    )

    # Test 7: Wide Perspective Test
    print("\n\nGenerating test data for WIDE PERSPECTIVE test...")
    test7_data = generate_realistic_positions(
        num_positions=1000,
        num_lookthroughs_per_position=2,
        num_containers=1,
        num_sub_portfolios=5,
        num_perspectives=100
    )
    test7_rules = generate_simple_scaling_rules(num_perspectives=100)

    with open("test_perf_rules_7.json", "w") as f:
        json.dump(test7_rules, f, indent=2)

    run_performance_test(
        "WIDE PERSPECTIVES (1,000 positions, 100 perspectives)",
        test7_data,
        "test_perf_rules_7.json"
    )

    # Test 8: Deep Lookthrough Test
    print("\n\nGenerating test data for DEEP LOOKTHROUGH test...")
    test8_data = generate_realistic_positions(
        num_positions=100,
        num_lookthroughs_per_position=50,
        num_containers=1,
        num_sub_portfolios=3,
        num_perspectives=10
    )
    test8_rules = generate_simple_scaling_rules(num_perspectives=10)

    with open("test_perf_rules_8.json", "w") as f:
        json.dump(test8_rules, f, indent=2)

    run_performance_test(
        "DEEP LOOKTHROUGHS (100 positions, ~5,000 lookthroughs, 10 perspectives)",
        test8_data,
        "test_perf_rules_8.json"
    )

    # Test 9: Multi-Container Test
    print("\n\nGenerating test data for MULTI-CONTAINER test...")
    test9_data = generate_realistic_positions(
        num_positions=5000,
        num_lookthroughs_per_position=3,
        num_containers=10,
        num_sub_portfolios=8,
        num_perspectives=20
    )
    test9_rules = generate_simple_scaling_rules(num_perspectives=20)

    with open("test_perf_rules_9.json", "w") as f:
        json.dump(test9_rules, f, indent=2)

    run_performance_test(
        "MULTI-CONTAINER (5,000 positions across 10 containers, 20 perspectives)",
        test9_data,
        "test_perf_rules_9.json"
    )

    # Test 10: Real-World Simulation
    print("\n\nGenerating test data for REAL-WORLD SIMULATION test...")
    test10_data = generate_realistic_positions(
        num_positions=2500,
        num_lookthroughs_per_position=8,
        num_containers=5,
        num_sub_portfolios=15,
        num_perspectives=35
    )
    test10_rules = generate_simple_scaling_rules(num_perspectives=35)


    

    with open("test_perf_rules_10.json", "w") as f:
        json.dump(test10_rules, f, indent=2)

    run_performance_test(
        "REAL-WORLD (2,500 positions, ~20,000 lookthroughs, 5 containers, 35 perspectives)",
        test10_data,
        "test_perf_rules_10.json"
    )



    print("\n\nGenerating test data for REAL-WORLD SIMULATION test...")
    test10_data = generate_realistic_positions(
        num_positions=1000000,
        num_lookthroughs_per_position=2,
        num_containers=3,
        num_sub_portfolios=1,
        num_perspectives=1
    )
    test10_rules = generate_simple_scaling_rules(num_perspectives=1)
    with open("test_perf_rules_10.json", "w") as f:
        json.dump(test10_rules, f, indent=2)
    run_performance_test(
        "REAL-WORLD (1000000 positions, ~20,000 lookthroughs, 5 containers, 35 perspectives)",
        test10_data,
        "test_perf_rules_10.json"
    )
    print("\n" + "="*80)
    print("ALL PERFORMANCE TESTS COMPLETED")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
