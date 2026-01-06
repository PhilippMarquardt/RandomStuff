"""
Step-by-step integration test for the Perspective Engine pipeline.

Usage: python test_pipeline.py <path_to_request.json>
"""
import sys
import json
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


def main(request_path: str):
    """Run the pipeline step by step."""
    total_start = time.time()

    # =========================================================================
    # STEP 1: Load configuration from .env
    # =========================================================================
    log.info("=" * 60)
    log.info("STEP 1: Loading configuration from .env")
    log.info("=" * 60)

    from production_implementation.config import load_config
    config = load_config()

    log.info(f"  Server: {config.server}")
    log.info(f"  Database: {config.database}")
    log.info(f"  Driver: {config.driver}")
    log.info(f"  Trusted Connection: {config.trusted_connection}")

    if not config.server or not config.database:
        log.error("DB_SERVER and DB_DATABASE must be set in .env file")
        sys.exit(1)

    # =========================================================================
    # STEP 2: Load perspectives from database
    # =========================================================================
    log.info("")
    log.info("=" * 60)
    log.info("STEP 2: Loading perspectives from database")
    log.info("=" * 60)

    from production_implementation.database import PerspectiveLoader
    loader = PerspectiveLoader(config)

    try:
        perspectives = loader.load_perspectives()
    except Exception as e:
        log.error(f"Failed to load perspectives: {e}")
        sys.exit(1)

    log.info(f"  Loaded {len(perspectives)} perspectives")

    # Show first 5 perspectives
    for pid, p in list(perspectives.items())[:5]:
        log.info(f"    ID {pid}: {p.name} ({len(p.rules)} rules)")

    if len(perspectives) > 5:
        log.info(f"    ... and {len(perspectives) - 5} more")

    # =========================================================================
    # STEP 3: Load hardcoded modifiers
    # =========================================================================
    log.info("")
    log.info("=" * 60)
    log.info("STEP 3: Loading hardcoded modifiers")
    log.info("=" * 60)

    from production_implementation.modifiers import SUPPORTED_MODIFIERS

    log.info(f"  Loaded {len(SUPPORTED_MODIFIERS)} modifiers")

    # Count by type
    preprocessing = sum(1 for m in SUPPORTED_MODIFIERS.values() if m['type'] == 'PreProcessing')
    postprocessing = sum(1 for m in SUPPORTED_MODIFIERS.values() if m['type'] == 'PostProcessing')
    scaling = sum(1 for m in SUPPORTED_MODIFIERS.values() if m['type'] == 'Scaling')

    log.info(f"    PreProcessing: {preprocessing}")
    log.info(f"    PostProcessing: {postprocessing}")
    log.info(f"    Scaling: {scaling}")

    # =========================================================================
    # STEP 4: Load request JSON
    # =========================================================================
    log.info("")
    log.info("=" * 60)
    log.info(f"STEP 4: Loading request from {request_path}")
    log.info("=" * 60)

    try:
        with open(request_path, 'r') as f:
            request = json.load(f)
    except FileNotFoundError:
        log.error(f"Request file not found: {request_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON in request file: {e}")
        sys.exit(1)

    log.info(f"  Top-level keys: {list(request.keys())}")

    # Extract key config
    ed = request.get('ed', 'N/A')
    position_weights = request.get('position_weight_labels', ['weight'])
    lookthrough_weights = request.get('lookthrough_weight_labels', ['weight'])
    perspective_configs = request.get('perspective_configurations', {})
    verbose_output = request.get('verbose_output', True)

    log.info(f"  Effective date: {ed}")
    log.info(f"  Position weights: {position_weights}")
    log.info(f"  Lookthrough weights: {lookthrough_weights}")
    log.info(f"  Perspective configurations: {len(perspective_configs)}")

    # Count containers (position data)
    containers = [k for k, v in request.items() if isinstance(v, dict) and 'position_type' in v]
    log.info(f"  Data containers: {containers}")

    # =========================================================================
    # STEP 5: Extract positions/lookthroughs
    # =========================================================================
    log.info("")
    log.info("=" * 60)
    log.info("STEP 5: Building DataFrames from request")
    log.info("=" * 60)

    from production_implementation.engine import DataIngestion

    all_weights = list(set(position_weights + lookthrough_weights))
    positions_lf, lookthroughs_lf = DataIngestion.build_dataframes(request, all_weights)

    pos_cols = positions_lf.collect_schema().names()
    lt_cols = lookthroughs_lf.collect_schema().names()

    log.info(f"  Positions: {len(pos_cols)} columns")
    log.info(f"  Lookthroughs: {len(lt_cols)} columns")

    # =========================================================================
    # STEP 6: Load reference data from DB
    # =========================================================================
    log.info("")
    log.info("=" * 60)
    log.info("STEP 6: Loading reference data from database")
    log.info("=" * 60)

    from production_implementation.database import ReferenceLoader
    import polars as pl

    ref_loader = ReferenceLoader(config)

    # Get unique instrument IDs
    pos_ids = positions_lf.select('instrument_id').collect().to_series().to_list()
    lt_ids = lookthroughs_lf.select('instrument_id').collect().to_series().to_list() if lt_cols else []
    unique_ids = list(set(pos_ids + lt_ids))
    unique_ids = [i for i in unique_ids if i is not None]

    log.info(f"  Unique instrument IDs: {len(unique_ids)}")

    # Load reference tables
    required_tables = {
        'INSTRUMENT_CATEGORIZATION': ['liquidity_type_id', 'position_source_type_id']
    }

    try:
        reference_data = ref_loader.load_multiple_tables(unique_ids, required_tables, ed)
        for table_name, df in reference_data.items():
            log.info(f"  Loaded {table_name}: {len(df)} rows")

        # Join reference data
        positions_lf, lookthroughs_lf = DataIngestion.join_reference_data(
            positions_lf, lookthroughs_lf, reference_data
        )
    except Exception as e:
        log.warning(f"  Could not load reference data: {e}")
        log.info("  Continuing without reference data...")

    # =========================================================================
    # STEP 7: Build perspective expressions
    # =========================================================================
    log.info("")
    log.info("=" * 60)
    log.info("STEP 7: Building perspective expressions")
    log.info("=" * 60)

    from production_implementation.engine import PerspectiveProcessor

    processor = PerspectiveProcessor(
        perspectives=perspectives,
        modifiers=SUPPORTED_MODIFIERS
    )

    positions_lf, lookthroughs_lf, metadata_map = processor.build_perspective_plan(
        positions_lf,
        lookthroughs_lf,
        perspective_configs,
        position_weights,
        lookthrough_weights
    )

    total_configs = sum(len(m) for m in metadata_map.values())
    log.info(f"  Built expressions for {total_configs} perspective configurations")

    # =========================================================================
    # STEP 8: Execute plan (materialize)
    # =========================================================================
    log.info("")
    log.info("=" * 60)
    log.info("STEP 8: Executing plan (materializing)")
    log.info("=" * 60)

    start = time.time()

    if lookthroughs_lf is not None:
        positions_df, lookthroughs_df = pl.collect_all([positions_lf, lookthroughs_lf])
    else:
        positions_df = positions_lf.collect()
        lookthroughs_df = pl.DataFrame()

    elapsed = time.time() - start
    log.info(f"  Collected in {elapsed:.3f}s")
    log.info(f"  Positions: {len(positions_df)} rows, {len(positions_df.columns)} columns")
    log.info(f"  Lookthroughs: {len(lookthroughs_df)} rows, {len(lookthroughs_df.columns)} columns")

    # =========================================================================
    # STEP 9: Format output
    # =========================================================================
    log.info("")
    log.info("=" * 60)
    log.info("STEP 9: Formatting output")
    log.info("=" * 60)

    from production_implementation.engine import OutputFormatter

    result = OutputFormatter.format_output(
        positions_df,
        lookthroughs_df,
        metadata_map,
        position_weights,
        lookthrough_weights,
        verbose_output
    )

    config_count = len(result.get('perspective_configurations', {}))
    log.info(f"  Output has {config_count} perspective configurations")

    # =========================================================================
    # DONE
    # =========================================================================
    total_elapsed = time.time() - total_start
    log.info("")
    log.info("=" * 60)
    log.info(f"PIPELINE COMPLETE in {total_elapsed:.3f}s")
    log.info("=" * 60)

    # Optionally write output to file
    output_path = request_path.replace('.json', '_output.json')
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    log.info(f"Output written to: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_pipeline.py <path_to_request.json>")
        print("")
        print("Example:")
        print("  python test_pipeline.py final_system_test/data.json")
        sys.exit(1)

    main(sys.argv[1])
