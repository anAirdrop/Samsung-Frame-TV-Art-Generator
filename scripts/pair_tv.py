#!/usr/bin/env python3
"""One-time Samsung Frame TV pairing script.

Usage:
    python scripts/pair_tv.py --host 192.168.1.100 --token-file tokens/living_room_token.txt

The TV will display a pairing popup on screen. Accept it with your TV remote
within 30 seconds. The pairing token is saved to the token file for future use.
"""

import argparse
import sys

from frame_art.services.tv_controller import pair_tv


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pair with a Samsung Frame TV"
    )
    parser.add_argument(
        "--host", required=True, help="TV IP address (e.g. 192.168.1.100)"
    )
    parser.add_argument(
        "--port", type=int, default=8002, help="TV port (default: 8002)"
    )
    parser.add_argument(
        "--token-file",
        required=True,
        help="Path to save the pairing token (e.g. tokens/living_room.txt)",
    )
    args = parser.parse_args()

    print(f"Connecting to TV at {args.host}:{args.port}...")
    print(">>> LOOK AT YOUR TV and ACCEPT the pairing prompt <<<")
    print()

    try:
        info = pair_tv(args.host, args.port, args.token_file)
        device = info.get("device", {})
        print(f"Paired successfully!")
        print(f"  TV Name:  {device.get('name', 'Unknown')}")
        print(f"  Model:    {device.get('modelName', 'Unknown')}")
        print(f"  Token:    saved to {args.token_file}")
    except Exception as e:
        print(f"Pairing failed: {e}", file=sys.stderr)
        print(
            "\nMake sure the TV is powered on, in Art Mode, "
            "and on the same network.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
