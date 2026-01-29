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
    CsvKeyManager,
    Outcome,
    generate_coin_name,
    UID,
)
from ntag424_sdm_provisioner.server.game_state_manager import SqliteGameStateManager


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


def backfill_csv_auto(csv_path: str, dry_run: bool = True) -> None:
    """Backfill coin names for production data.

    Args:
        csv_path: Path to tag_keys.csv
        dry_run: If True, show changes without saving
    """
    csv_path_obj = Path(csv_path)
    print(f"\n[MODE: AUTO] Loading data from: {csv_path}")

    # Ensure coin_name column exists
    ensure_coin_name_column(csv_path_obj)

    # Read CSV to get all rows
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


def backfill_scans_db(csv_path: Path, db_path: Path, dry_run: bool = True) -> None:
    """Backfill coin_name in the scan_logs table from the key manager.

    Args:
        csv_path: Path to the tag_keys.csv file to load keys.
        db_path: Path to the app.db SQLite database.
        dry_run: If True, show changes without saving.
    """
    print("\n" + "="*60)
    print("Backfilling Database (app.db)...")
    print("="*60)

    if not db_path.exists():
        print(f"Database not found at {db_path}. Skipping DB backfill.")
        return

    # 1. Load Key Manager to get UID -> coin_name mapping
    key_manager = CsvKeyManager(csv_path=str(csv_path))
    all_keys = key_manager.list_tags()
    uid_to_coin_name = {tag.uid.uid: tag.coin_name for tag in all_keys if tag.coin_name}

    if not uid_to_coin_name:
        print("No coin names found in key manager. Nothing to backfill in DB.")
        return

    # 2. Connect to DB and ensure 'coin_name' column exists
    # The SqliteGameStateManager constructor automatically handles migration
    game_manager = SqliteGameStateManager(db_path=str(db_path))
    print(f"✓ Database connection to {db_path} successful.")

    # 3. Get all scans that need updating
    scans_to_update = game_manager._query(
        "SELECT id, uid FROM scan_logs WHERE coin_name IS NULL OR coin_name = ''"
    )

    if not scans_to_update:
        print("✓ No scans in the database require backfilling.")
        return

    updates = []
    for scan_id, uid in scans_to_update:
        if uid in uid_to_coin_name:
            updates.append((uid_to_coin_name[uid], scan_id))

    if not updates:
        print("No matching UIDs found between DB and key manager. Nothing to update.")
        return

    print(f"Found {len(updates)} scan entries to update with coin names.")

    if dry_run:
        print("\n[DRY RUN] Would update the database as follows:")
        for coin_name, scan_id in updates[:5]:  # Show a sample
            print(f"  - Set coin_name='{coin_name}' for scan with id={scan_id}")
        if len(updates) > 5:
            print(f"  ... and {len(updates) - 5} more.")
        return

    # 4. Apply updates
    with game_manager._get_conn() as conn:
        conn.executemany("UPDATE scan_logs SET coin_name = ? WHERE id = ?", updates)
        conn.commit()
        print(f"\nSUCCESS: Updated {len(updates)} records in the database.")

def main():
    parser = argparse.ArgumentParser(
        description="Backfill coin_name in tag_keys.csv and app.db. Supports auto pairing."
    )
    parser.add_argument(
        "--csv", "-c",
        default="data/tag_keys.csv",
        help="Path to tag_keys.csv (default: data/tag_keys.csv)",
    )
    parser.add_argument(
        "--db",
        default="data/app.db",
        help="Path to app.db SQLite database (default: data/app.db)",
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

    db_path = Path(args.db)

    backfill_csv_auto(str(csv_path), dry_run=not args.apply)

    # Step 2: Backfill the database using the updated CSV data
    backfill_scans_db(csv_path, db_path, dry_run=not args.apply)


if __name__ == "__main__":
    main()
