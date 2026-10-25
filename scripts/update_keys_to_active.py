"""Script to update all keys in tag_validator_service with status 'provisioned' to 'active'."""

import argparse
import json
import sys
import urllib.error
import urllib.request


def update_service_keys(base_url: str = "http://192.168.86.17:8080") -> None:
    base_url = base_url.rstrip("/")
    print(f"Connecting to tag_validator_service at {base_url}...")

    # 1. Fetch all keys with raw=true
    url = f"{base_url}/api/v1/keys?raw=true"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching keys from {url}: {e}", file=sys.stderr)
        sys.exit(1)

    keys = data.get("keys", [])
    print(f"Found {len(keys)} total key(s) in service.\n")

    updated_count = 0
    already_active = 0
    skipped = 0

    for item in keys:
        uid = item.get("uid")
        current_status = item.get("status")
        k0 = item.get("k0", "0" * 32)
        k1 = item.get("k1", "0" * 32)
        k3 = item.get("k3", "0" * 32)

        if current_status == "provisioned":
            payload = {
                "uid": uid,
                "k0": k0,
                "k1": k1,
                "k3": k3,
                "status": "active",
            }
            post_req = urllib.request.Request(
                f"{base_url}/api/v1/keys",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(post_req, timeout=10) as post_resp:
                    res = json.loads(post_resp.read().decode("utf-8"))
                    print(f"  [✓ UPDATED] {uid}: provisioned -> active")
                    updated_count += 1
            except Exception as e:
                print(f"  [✗ ERROR] Failed to update {uid}: {e}", file=sys.stderr)
        elif current_status == "active":
            print(f"  [-] {uid}: already active")
            already_active += 1
        else:
            print(f"  [-] {uid}: status={current_status} (skipped)")
            skipped += 1

    print(f"\nSummary:")
    print(f"  Updated to active: {updated_count}")
    print(f"  Already active:    {already_active}")
    print(f"  Skipped (other):   {skipped}")
    print(f"  Total keys:        {len(keys)}")


def main():
    parser = argparse.ArgumentParser(description="Update provisioned keys to active in tag_validator_service.")
    parser.add_argument(
        "--url",
        default="http://192.168.86.17:8080",
        help="Base URL of tag_validator_service (default: http://192.168.86.17:8080)",
    )
    args = parser.parse_args()
    update_service_keys(args.url)


if __name__ == "__main__":
    main()
