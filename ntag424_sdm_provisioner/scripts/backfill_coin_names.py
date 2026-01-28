#!/usr/bin/env python3
"""Backfill coin names for existing production tag_keys.csv data.

This script:
1. Reads tag_keys.csv
2. Adds coin_name column if missing
3. Filters rows where outcome is 'heads' or 'tails'
4. Processes them in pairs (2 consecutive rows = 1 coin)
5. Generates unique coin names for each pair
6. Updates ONLY the coin_name field (preserves all keys)
7. Saves updated CSV

CRITICAL: Does NOT modify any cryptographic keys.
"""

import argparse
import csv
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ntag424_sdm_provisioner.csv_key_manager import (
    Outcome,
    generate_coin_name,
)


def ensure_coin_name_column(csv_path: Path) -> None:
    """Add coin_name column if it doesn't exist.

    Args:
        csv_path: Path to tag_keys.csv
    """
    # Read existing data
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Check if coin_name column exists
    if "coin_name" in fieldnames:
        print("✓ coin_name column already exists")
        return

    print("Adding coin_name column...")

    # Add coin_name to fieldnames (after outcome)
    new_fieldnames = list(fieldnames)
    outcome_idx = new_fieldnames.index("outcome")
    new_fieldnames.insert(outcome_idx + 1, "coin_name")

    # Add empty coin_name to all rows
    for row in rows:
        row["coin_name"] = ""

    # Write back with new column
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ Added coin_name column to {len(rows)} rows")


def backfill_coin_names(csv_path: str, dry_run: bool = True) -> None:
    """Backfill coin names for production data.

    Args:
        csv_path: Path to tag_keys.csv
        dry_run: If True, show changes without saving
    """
    csv_path_obj = Path(csv_path)
    print(f"Loading data from: {csv_path}")

    # Ensure coin_name column exists
    ensure_coin_name_column(csv_path_obj)

    # Read CSV manually to get all rows
    with csv_path_obj.open(newline="") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    print(f"Total tags: {len(all_rows)}")

    # Filter for rows with outcomes (and no existing coin_name)
    rows_with_outcome = [
        row for row in all_rows
        if row.get("outcome") in ("heads", "tails") and not row.get("coin_name")
    ]
    print(f"Tags with outcomes (unassigned): {len(rows_with_outcome)}")

    if len(rows_with_outcome) == 0:
        print("No unassigned tags with outcomes found. Nothing to backfill.")
        return

    # Process in pairs (bottoms up: if odd count, first row is incomplete)
    pairs_to_assign = []
    start_index = 0

    # If odd number, first row is the incomplete coin
    if len(rows_with_outcome) % 2 == 1:
        row1 = rows_with_outcome[0]
        coin_name = generate_coin_name()
        print(f"\nIncomplete coin:")
        print(f"  Coin: {coin_name}")
        print(f"  UID: {row1['uid']} ({row1['outcome']})")
        print(f"  WARNING: Missing partner tag")
        pairs_to_assign.append((row1, None, coin_name))
        start_index = 1

    # Pair the remaining rows
    for i in range(start_index, len(rows_with_outcome), 2):
        row1 = rows_with_outcome[i]
        row2 = rows_with_outcome[i + 1]
        coin_name = generate_coin_name()
        pairs_to_assign.append((row1, row2, coin_name))
        print(f"\nPair {len(pairs_to_assign) - (1 if start_index == 1 else 0)}:")
        print(f"  Coin: {coin_name}")
        print(f"  UID 1: {row1['uid']} ({row1['outcome']})")
        print(f"  UID 2: {row2['uid']} ({row2['outcome']})")

    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN - No changes made")
        print(f"Would assign {len(pairs_to_assign)} coin names")
        print("Run with --apply to save changes")
        print("="*60)
        return

    # Apply changes
    print("\n" + "="*60)
    print("APPLYING CHANGES")
    print("="*60)

    # Update rows with coin names
    updates_made = 0
    for row1, row2, coin_name in pairs_to_assign:
        # CRITICAL: Only modify coin_name field, preserve all other fields
        row1["coin_name"] = coin_name
        updates_made += 1
        print(f"✓ Updated {row1['uid']} with coin_name={coin_name}")

        if row2:
            row2["coin_name"] = coin_name
            updates_made += 1
            print(f"✓ Updated {row2['uid']} with coin_name={coin_name}")

    # Write updated CSV
    fieldnames = list(all_rows[0].keys())
    with csv_path_obj.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print("\n" + "="*60)
    print(f"SUCCESS: Updated {updates_made} tags in {len(pairs_to_assign)} coins")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Backfill coin names for production tag_keys.csv"
    )
    parser.add_argument(
        "--csv",
        default="data/tag_keys.csv",
        help="Path to tag_keys.csv (default: data/tag_keys.csv)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run)",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        sys.exit(1)

    backfill_coin_names(str(csv_path), dry_run=not args.apply)


if __name__ == "__main__":
    main()
