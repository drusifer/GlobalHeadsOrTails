"""CLI utility to import tag keys from tag_keys.csv into k3s Secrets."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

from ..models import TagSecret
from ..store import create_secret_store

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def import_csv_to_store(
    csv_path: str | Path,
    backend: str = "k3s",
    namespace: str = "tag-secrets",
    dry_run: bool = False,
) -> tuple[int, int, list[str]]:
    """Imports tag keys from CSV file into the configured secret store.

    Returns:
        (imported_count, skipped_count, error_messages)
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    store = None if dry_run else create_secret_store(backend=backend, namespace=namespace)

    imported = 0
    skipped = 0
    errors = []

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row_idx, row in enumerate(reader, start=1):
            if not row or not row[0].strip() or row[0].strip().startswith("#"):
                continue

            first_col = row[0].strip().lower()
            if first_col in ("uid", "tag_uid", "asset_tag"):
                continue

            try:
                uid = row[0].strip()
                # Determine column structure
                if len(row) >= 4 and len(row[3].strip()) == 32:
                    k3 = row[3].strip()
                    coin_name = row[5].strip() if len(row) > 5 else ""
                elif len(row) >= 2 and len(row[1].strip()) == 32:
                    k3 = row[1].strip()
                    coin_name = row[2].strip() if len(row) > 2 else ""
                else:
                    skipped += 1
                    continue

                secret = TagSecret(uid=uid, k3=k3, coin_name=coin_name)
                if dry_run:
                    log.info(f"[DRY-RUN] Would save {secret.secret_name} (UID={secret.uid}, K3={secret.masked_k3()})")
                    imported += 1
                else:
                    assert store is not None
                    if store.save_key(secret):
                        log.info(f"Saved {secret.secret_name} -> {namespace}")
                        imported += 1
                    else:
                        errors.append(f"Row {row_idx}: Failed to save {secret.secret_name}")
            except Exception as e:
                errors.append(f"Row {row_idx}: {e}")
                skipped += 1

    return imported, skipped, errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import tag keys from CSV into Kubernetes/k3s Secrets",
    )
    parser.add_argument("csv_file", help="Path to tag_keys.csv")
    parser.add_argument(
        "--backend",
        "-b",
        default="k3s",
        choices=["k3s", "memory"],
        help="Target secret store backend (default: k3s)",
    )
    parser.add_argument(
        "--namespace",
        "-n",
        default="tag-secrets",
        help="Kubernetes namespace for secrets (default: tag-secrets)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate rows without writing to Kubernetes cluster",
    )

    args = parser.parse_args()

    try:
        imported, skipped, errors = import_csv_to_store(
            csv_path=args.csv_file,
            backend=args.backend,
            namespace=args.namespace,
            dry_run=args.dry_run,
        )
        print("\n=== Import Summary ===")
        print(f"Imported: {imported}")
        print(f"Skipped:  {skipped}")
        print(f"Errors:   {len(errors)}")
        if errors:
            print("\nError Details:")
            for err in errors[:10]:
                print(f"  - {err}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")
    except Exception as e:
        log.error(f"Fatal import error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
