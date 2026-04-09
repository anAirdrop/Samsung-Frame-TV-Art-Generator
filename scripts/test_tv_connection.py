#!/usr/bin/env python3
"""Test connectivity to all configured Samsung Frame TVs.

Usage:
    python scripts/test_tv_connection.py
    python scripts/test_tv_connection.py --config path/to/config.yaml
"""

import argparse
import sys

from frame_art.config import load_config
from frame_art.services.tv_controller import TVController


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test connectivity to configured Samsung Frame TVs"
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Path to config.yaml"
    )
    args = parser.parse_args()

    config = load_config(args.config)

    if not config.tvs:
        print("No TVs configured in config.yaml")
        sys.exit(1)

    all_ok = True
    for tv_key, tv_config in config.tvs.items():
        display_name = tv_key.replace("_", " ").title()
        controller = TVController(tv_config)

        print(f"Testing {display_name} ({tv_config.host})...", end=" ")
        if controller.is_reachable():
            print("OK")
        else:
            print("UNREACHABLE")
            all_ok = False

    if not all_ok:
        print(
            "\nSome TVs are unreachable. Ensure they are powered on, "
            "in Art Mode, and on the same network."
        )
        sys.exit(1)
    else:
        print("\nAll TVs are reachable!")


if __name__ == "__main__":
    main()
