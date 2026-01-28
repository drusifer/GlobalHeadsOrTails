#!/usr/bin/env python3
"""Manually specify coin pairings for backfill.

Create pairs.txt with manual pairing:
UID1,UID2
UID3,UID4
UID5  (incomplete coin)
"""

import argparse
import csv
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ntag424_sdm_provisioner.csv_key_manager import generate_coin_name


def read_manual_pairs(pairs_file: Path) -> list:
    """Read manual pairings from file.

    Format:
        UID1,UID2
        UID3,UID4
        UID5

    Returns list of tuples: [(uid1, uid2, coin_name), (uid3, None, coin_name)]
    """
    pairs = []
    with pairs_file.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            uids = [uid.strip() for uid in line.split(',')]
            coin_name = generate_coin_name()

            if len(uids) == 2:
                pairs.append((uids[0], uids[1], coin_name))
            elif len(uids) == 1:
                pairs.append((uids[0], None, coin_name))
            else:
                print(f"Warning: Invalid line: {line}")

    return pairs


def backfill_with_manual_pairs(csv_path: str, pairs_file: str, dry_run: bool = True):
    """Backfill using manual pairings."""
    csv_path_obj = Path(csv_path)
    pairs_file_obj = Path(pairs_file)

    if not pairs_file_obj.exists():
        print(f"Error: {pairs_file} not found")
        print("\nCreate pairs.txt with format:")
        print("UID1,UID2")
        print("UID3,UID4")
        print("UID5  (incomplete coin)")
        sys.exit(1)

    # Read manual pairs
    pairs = read_manual_pairs(pairs_file_obj)
    print(f"Loaded {len(pairs)} coin pairings from {pairs_file}")

    # Read CSV
    with csv_path_obj.open(newline='') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    # Create UID -> row mapping
    uid_to_row = {row['uid']: row for row in all_rows}

    # Apply pairings
    print("\nPairings:")
    print("-" * 80)

    updates = []
    for uid1, uid2, coin_name in pairs:
        row1 = uid_to_row.get(uid1)
        row2 = uid_to_row.get(uid2) if uid2 else None

        if not row1:
            print(f"Warning: UID {uid1} not found in CSV")
            continue

        if uid2 and not row2:
            print(f"Warning: UID {uid2} not found in CSV")
            continue

        print(f"\nCoin: {coin_name}")
        print(f"  {uid1} ({row1.get('outcome', 'N/A')})")
        if row2:
            print(f"  {uid2} ({row2.get('outcome', 'N/A')})")
        else:
            print(f"  (incomplete - missing partner)")

        updates.append((row1, row2, coin_name))

    if dry_run:
        print("\n" + "="*80)
        print("DRY RUN - No changes made")
        print(f"Would assign {len(updates)} coin names")
        print("Run with --apply to save changes")
        print("="*80)
        return

    # Apply updates
    print("\n" + "="*80)
    print("APPLYING CHANGES")
    print("="*80)

    updates_made = 0
    for row1, row2, coin_name in updates:
        row1['coin_name'] = coin_name
        updates_made += 1
        print(f"✓ Updated {row1['uid']} with coin_name={coin_name}")

        if row2:
            row2['coin_name'] = coin_name
            updates_made += 1
            print(f"✓ Updated {row2['uid']} with coin_name={coin_name}")

    # Write updated CSV
    fieldnames = list(all_rows[0].keys())
    with csv_path_obj.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print("\n" + "="*80)
    print(f"SUCCESS: Updated {updates_made} tags in {len(updates)} coins")
    print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description="Backfill coin names using manual pairing file"
    )
    parser.add_argument(
        "--csv",
        default="data/tag_keys.csv",
        help="Path to tag_keys.csv (default: data/tag_keys.csv)",
    )
    parser.add_argument(
        "--pairs",
        default="pairs.txt",
        help="Path to pairs file (default: pairs.txt)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run)",
    )

    args = parser.parse_args()
    backfill_with_manual_pairs(args.csv, args.pairs, dry_run=not args.apply)


if __name__ == "__main__":
    main()
