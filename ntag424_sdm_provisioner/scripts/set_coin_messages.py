#!/usr/bin/env python3
"""Set custom Heads/Tails display messages for a coin directly in the database.

Usage:
    python scripts/set_coin_messages.py COIN-NAME "HEADS TEXT" "TAILS TEXT" data/app.db

To clear messages for a coin, pass empty strings:
    python scripts/set_coin_messages.py COIN-NAME "" "" data/app.db
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ntag424_sdm_provisioner.server.coin_message_service import CoinMessageService


MAX_MESSAGE_LEN = 24


def validate_message(text: str, field: str) -> None:
    length = len([*text])  # grapheme clusters — matches server-side validation
    if length > MAX_MESSAGE_LEN:
        print(f"Error: {field} is {length} chars (max {MAX_MESSAGE_LEN}): {text!r}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set custom Heads/Tails messages for a coin in the app database.",
    )
    parser.add_argument("coin_name", help="Coin name (e.g. HAPPY-HAWK-001)")
    parser.add_argument("heads", help=f"Heads message (max {MAX_MESSAGE_LEN} chars, empty to clear)")
    parser.add_argument("tails", help=f"Tails message (max {MAX_MESSAGE_LEN} chars, empty to clear)")
    parser.add_argument("db", help="Path to app.db SQLite file")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: database not found: {db_path}")
        sys.exit(1)

    validate_message(args.heads, "heads")
    validate_message(args.tails, "tails")

    svc = CoinMessageService(db_path=str(db_path))

    before_heads, before_tails = svc.get_messages(args.coin_name)
    print(f"Coin:   {args.coin_name}")
    print(f"Before: heads={before_heads!r}  tails={before_tails!r}")

    svc.set_messages(args.coin_name, args.heads, args.tails)

    after_heads, after_tails = svc.get_messages(args.coin_name)
    print(f"After:  heads={after_heads!r}  tails={after_tails!r}")
    print("Done.")


if __name__ == "__main__":
    main()
