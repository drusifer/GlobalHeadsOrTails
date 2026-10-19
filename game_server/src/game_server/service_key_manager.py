"""Service-based Key Manager using tag_validator_service over HTTP and SQLite app.db.

Decouples cryptographic key custody (held as k3s WORM secrets in tag_validator_service)
from gameplay and coin domain data (held in app.db).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from game_server.csv_key_manager import UID, Outcome, TagKeys
from game_server.game_state_manager import SqliteGameStateManager
from tag_validator.client import validate_tag_remotely


log = logging.getLogger(__name__)

DEFAULT_SERVICE_URL = "http://localhost:8080"


class ServiceKeyManager:
    """Key Manager implementation delegating key custody and validation to tag_validator_service.

    Features:
    - Cryptographic validation via remote stateless REST API (/api/v1/validate).
    - Coin identities (coin_name, clan, rarity) managed locally in SQLite app.db.
    - Atomic key generation and WORM custody via (/api/v1/keys/generate).
    - Soft-delete and undelete operations.
    """

    def __init__(
        self,
        service_url: str | None = None,
        db_path: str = "data/app.db",
        timeout_sec: float = 3.0,
    ) -> None:
        raw_url = service_url or os.environ.get("TAG_VALIDATOR_URL") or os.environ.get("KEY_SERVICE_URL") or DEFAULT_SERVICE_URL
        self.service_url = raw_url.rstrip("/")
        if not self.service_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid service_url: '{self.service_url}'. Must start with http:// or https://")

        self.db_path = Path(db_path)
        self.timeout_sec = timeout_sec
        self.game_manager = SqliteGameStateManager(db_path=str(db_path))

    # ── HTTP Request Helper ───────────────────────────────────────────────────

    def _http_request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        endpoint = f"{self.service_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}

        req = Request(  # noqa: S310
            endpoint,
            data=data,
            headers=headers,
            method=method.upper(),
        )
        try:
            with urlopen(req, timeout=self.timeout_sec) as resp:  # noqa: S310
                raw = resp.read()
                return resp.status, json.loads(raw.decode("utf-8")) if raw else {}
        except HTTPError as e:
            err_raw = e.read()
            try:
                err_json = json.loads(err_raw.decode("utf-8"))
            except Exception:
                err_json = {"error": f"HTTP {e.code}: {e.reason}"}
            return e.code, err_json
        except URLError as e:
            log.warning(f"Failed to connect to key service at {endpoint}: {e}")
            return 503, {"error": f"Connection to key service failed: {e.reason}"}
        except Exception as e:
            log.error(f"Unexpected error communicating with key service: {e}")
            return 500, {"error": str(e)}

    # ── KeyManager Protocol & SDM Validation ──────────────────────────────────

    def get_key(self, uid: UID | bytes | str, key_no: int) -> bytes:
        """Retrieves raw key bytes if available or factory default.

        Note: SDM MAC keys (k3) are vaulted securely in tag_validator_service.
        """
        if key_no < 0 or key_no > 4:
            raise ValueError(f"Key number must be 0-4, got {key_no}")
        if key_no in (0, 1):
            return b"\x00" * 16

        uid_str = (
            uid.hex().upper()
            if isinstance(uid, (bytes, bytearray))
            else (uid.uid if isinstance(uid, UID) else str(uid).upper())
        )
        if hasattr(self, "_cached_keys") and uid_str in self._cached_keys:
            return bytes.fromhex(self._cached_keys[uid_str])

        raise KeyError(
            f"SDM MAC key (Key {key_no}) for UID '{uid_str}' is vaulted in tag_validator_service and cannot be exported."
        )

    def get_outcome(self, uid: UID | str) -> Outcome:
        """Retrieves the assigned coin side (heads/tails) for a tag."""
        return self.get_tag_keys(uid).outcome

    def validate_sdm_url(self, uid: UID | str, counter: int, cmac: str) -> dict:
        """Validates an SDM URL CMAC via the standalone key service.

        Returns:
            dict compatible with CsvKeyManager:
            {
                "valid": bool,
                "uid": UID,
                "counter": int,
                "cmac_received": str,
                "cmac_calculated": str | None,
                "error": str | None,
            }
        """
        uid_obj = uid if isinstance(uid, UID) else UID(str(uid))
        resp = validate_tag_remotely(
            uid=uid_obj.uid,
            counter=counter,
            cmac=cmac,
            service_url=self.service_url,
            timeout_sec=self.timeout_sec,
        )

        return {
            "valid": resp.get("valid", False),
            "uid": uid_obj,
            "counter": counter,
            "cmac_received": cmac,
            "cmac_calculated": resp.get("cmac_calculated"),
            "error": resp.get("error"),
        }

    def get_tag_keys(self, uid: UID | str) -> TagKeys:
        """Retrieves tag metadata, resolving key status remotely and coin metadata from app.db."""
        uid_obj = uid if isinstance(uid, UID) else UID(str(uid))

        # 1. Fetch coin identity and outcome from app.db
        coin_record = self.game_manager.get_coin(uid_obj.uid)
        state_record = self.game_manager.get_state(uid_obj.uid)

        coin_name = ""
        raw_outcome = ""
        if coin_record:
            coin_name = coin_record.get("coin_name", "")
            raw_outcome = coin_record.get("outcome", "")
        if not coin_name and state_record and state_record.coin_name:
            coin_name = state_record.coin_name
        if not raw_outcome and state_record and state_record.outcome:
            raw_outcome = state_record.outcome

        outcome = Outcome.INVALID
        if raw_outcome:
            out_str = raw_outcome.lower()
            if out_str == "heads":
                outcome = Outcome.HEADS
            elif out_str == "tails":
                outcome = Outcome.TAILS

        # 2. Fetch key secret metadata from tag_validator_service
        status_code, body = self._http_request("GET", f"/api/v1/keys/{uid_obj.uid}")
        if status_code == 200:
            key_status = body.get("status", "provisioned")
            masked_k3 = body.get("k3_masked", "0" * 32)
        elif status_code == 404:
            key_status = "factory"
            masked_k3 = "0" * 32
        else:
            key_status = "error"
            masked_k3 = "0" * 32

        return TagKeys(
            uid=uid_obj,
            picc_master_key="0" * 32,
            app_read_key="0" * 32,
            sdm_mac_key=masked_k3,
            outcome=outcome,
            coin_name=coin_name,
            provisioned_date=datetime.now(UTC).isoformat(),
            status=key_status,
            notes=f"Remote key service at {self.service_url}",
        )

    def generate_random_keys(
        self,
        uid: UID | str,
        coin_name: str = "",
        outcome: Outcome = Outcome.INVALID,
    ) -> TagKeys:
        """Atomically generates a fresh AES-128 key in the key service and associates coin_name in app.db."""
        uid_obj = uid if isinstance(uid, UID) else UID(str(uid))

        status_code, body = self._http_request("POST", "/api/v1/keys/generate", {"uid": uid_obj.uid})
        if status_code == 201:
            k3 = body.get("k3", "0" * 32)
            if not hasattr(self, "_cached_keys"):
                self._cached_keys = {}
            self._cached_keys[uid_obj.uid] = k3

            if coin_name or outcome != Outcome.INVALID:
                outcome_str = outcome.value if outcome != Outcome.INVALID else ""
                self.game_manager.set_coin(uid_obj.uid, coin_name, outcome=outcome_str)

            return TagKeys(
                uid=uid_obj,
                picc_master_key="0" * 32,
                app_read_key="0" * 32,
                sdm_mac_key=k3,
                outcome=outcome,
                coin_name=coin_name,
                provisioned_date=datetime.now(UTC).isoformat(),
                status="provisioned",
                notes="Atomically generated and stored in key service",
            )
        else:
            raise RuntimeError(f"Failed to generate key in remote service: {body.get('error', 'Unknown error')}")

    def save_tag_keys(self, tag_keys: TagKeys) -> bool:
        """Saves key secret to key service and coin metadata to app.db."""
        uid_str = tag_keys.uid.uid

        # Persist coin identity in app.db
        if tag_keys.coin_name or (tag_keys.outcome and tag_keys.outcome != Outcome.INVALID):
            outcome_str = tag_keys.outcome.value if tag_keys.outcome != Outcome.INVALID else ""
            self.game_manager.set_coin(uid_str, tag_keys.coin_name, outcome=outcome_str)

        # If sdm_mac_key is provided and not masked/zeros, push to key service
        if tag_keys.sdm_mac_key and tag_keys.sdm_mac_key != "0" * 32 and "..." not in tag_keys.sdm_mac_key:
            status_code, _ = self._http_request("POST", "/api/v1/keys", {
                "uid": uid_str,
                "k3": tag_keys.sdm_mac_key,
                "status": tag_keys.status or "active",
            })
            return status_code in (200, 201)

        return True

    def delete_key(self, uid: UID | str) -> bool:
        """Soft-deletes a key in the remote key service."""
        uid_obj = uid if isinstance(uid, UID) else UID(str(uid))
        status_code, _ = self._http_request("DELETE", f"/api/v1/keys/{uid_obj.uid}")
        return status_code == 200

    def undelete_key(self, uid: UID | str) -> bool:
        """Restores a soft-deleted key in the remote key service."""
        uid_obj = uid if isinstance(uid, UID) else UID(str(uid))
        status_code, _ = self._http_request("POST", f"/api/v1/keys/{uid_obj.uid}/undelete", {})
        return status_code == 200

    def assign_coin_name(self, uid: UID | str, coin_name: str, outcome: Outcome) -> None:
        """Assigns coin name and outcome to tag in app.db."""
        uid_obj = uid if isinstance(uid, UID) else UID(str(uid))
        if not coin_name:
            raise ValueError("coin_name cannot be empty")
        if outcome not in (Outcome.HEADS, Outcome.TAILS):
            raise ValueError(f"outcome must be HEADS or TAILS, got {outcome}")

        # Check for duplicate outcome in the same coin
        existing_tags = self.list_tags()
        for tag in existing_tags:
            if tag.coin_name == coin_name and tag.outcome == outcome and tag.uid.uid != uid_obj.uid:
                raise ValueError(
                    f"Coin '{coin_name}' already has a {outcome.value} tag "
                    f"(UID: {tag.uid.uid}). Cannot assign duplicate outcome."
                )

        self.game_manager.set_coin(uid_obj.uid, coin_name, outcome=outcome.value)

    def list_tags(self) -> list[TagKeys]:
        """Lists tags from key service with metadata resolved from app.db."""
        status_code, body = self._http_request("GET", "/api/v1/keys")
        if status_code != 200:
            return []

        uids = body.get("uids", [])
        return [self.get_tag_keys(u) for u in uids]

    def get_coin_tags(self, coin_name: str) -> dict[str, TagKeys | None]:
        """Get both tags for a coin."""
        result: dict[str, TagKeys | None] = {"heads": None, "tails": None}
        for tag in self.list_tags():
            if tag.coin_name == coin_name:
                if tag.outcome == Outcome.HEADS:
                    result["heads"] = tag
                elif tag.outcome == Outcome.TAILS:
                    result["tails"] = tag
        return result

    def validate_coin(self, coin_name: str) -> dict:
        """Validate coin completeness."""
        tags = self.get_coin_tags(coin_name)
        heads = tags["heads"]
        tails = tags["tails"]
        issues = []
        if heads is None:
            issues.append("Missing heads tag")
        if tails is None:
            issues.append("Missing tails tag")
        return {
            "complete": len(issues) == 0,
            "heads": heads,
            "tails": tails,
            "issues": issues,
        }

    def list_coins(self) -> dict[str, dict]:
        """List all coins and their completeness status."""
        coins: dict[str, dict] = {}
        tags = self.list_tags()
        for tag in tags:
            cname = tag.coin_name or ""
            if cname not in coins:
                coins[cname] = {
                    "complete": False,
                    "heads_uid": None,
                    "tails_uid": None,
                }
            if tag.outcome == Outcome.HEADS:
                coins[cname]["heads_uid"] = tag.uid.uid
            elif tag.outcome == Outcome.TAILS:
                coins[cname]["tails_uid"] = tag.uid.uid

        for cname, data in coins.items():
            if cname == "":
                data["unassigned_count"] = sum(1 for t in tags if not t.coin_name)
            else:
                data["complete"] = (data["heads_uid"] is not None and data["tails_uid"] is not None)
        return coins

    def is_healthy(self) -> bool:
        """Checks if the remote key service is reachable and healthy."""
        status_code, body = self._http_request("GET", "/healthz")
        return status_code == 200 and body.get("status") == "ok"
