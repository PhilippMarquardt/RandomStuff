"""Test script for database perspective loading."""
import logging
import sys

# Setup logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from config import load_config
from database import PerspectiveLoader


def main():
    print("=" * 60)
    print("Perspective Database Loader Test")
    print("=" * 60)

    # Load config
    print("\n1. Loading configuration from .env...")
    config = load_config()
    print(f"   Server: {config.server}")
    print(f"   Database: {config.database}")
    print(f"   Driver: {config.driver}")
    print(f"   Trusted Connection: {config.trusted_connection}")

    if not config.server or not config.database:
        print("\n   ERROR: DB_SERVER and DB_DATABASE must be set in .env file")
        sys.exit(1)

    # Load perspectives
    print("\n2. Connecting to database and loading perspectives...")
    try:
        loader = PerspectiveLoader(config)
        perspectives = loader.load_perspectives()
    except Exception as e:
        print(f"\n   ERROR: Failed to load perspectives: {e}")
        sys.exit(1)

    # Display results
    print(f"\n3. Loaded {len(perspectives)} perspectives:")
    print("-" * 60)

    for pid, perspective in sorted(perspectives.items()):
        status = []
        if not perspective.is_active:
            status.append("INACTIVE")
        if not perspective.is_supported:
            status.append("UNSUPPORTED")
        status_str = f" [{', '.join(status)}]" if status else ""

        print(f"\n   ID {pid}: {perspective.name}{status_str}")
        print(f"   Rules: {len(perspective.rules)}")

        # Show first few rules
        for i, rule in enumerate(perspective.rules[:3]):
            print(f"      - {rule.name or '(unnamed)'} -> {rule.apply_to}")
            if rule.criteria:
                # Show a snippet of criteria
                criteria_str = str(rule.criteria)[:80]
                if len(str(rule.criteria)) > 80:
                    criteria_str += "..."
                print(f"        criteria: {criteria_str}")

        if len(perspective.rules) > 3:
            print(f"      ... and {len(perspective.rules) - 3} more rules")

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
