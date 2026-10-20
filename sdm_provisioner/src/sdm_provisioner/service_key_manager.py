"""Service-based Key Manager for sdm_provisioner using tag_validator_service and SQLite app.db.

Decouples cryptographic key custody (held as k3s/memory WORM secrets in tag_validator_service)
from coin domain data (held in SQLite data/app.db).
Operates in strict mode: requires tag_validator_service to be reachable.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import logging
import os
from pathlib import Path
import secrets
import sqlite3
from typing import Any

import coolname

from sdm_provisioner.key_manager import KeyManager
from sdm_provisioner.uid_utils import UID
from shared.outcome import Outcome
from shared.models import TagKeys
from tag_validator.client import TagValidatorClient

log = logging.getLogger(__name__)

DEFAULT_SERVICE_URL = "http://localhost:8080"


def generate_coin_name() -> str:
    """Generate a unique memorable coin name."""
    try:
        name = coolname.generate_slug(2)
    except Exception:
        name = "COIN"
    suffix = secrets.randbelow(1000)
    return f"{name}-{suffix}".upper()


class SqliteCoinStore:
    """Thread-safe SQLite store for coin identities in data/app.db."""

    def __init__(self, db_path: str = "data/app.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    @contextmanager
    def _get_conn(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coins (
                    uid TEXT PRIMARY KEY,
                    coin_name TEXT NOT NULL,
                    outcome TEXT DEFAULT '',
                    clan TEXT DEFAULT '',
                    rarity TEXT DEFAULT 'common',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def set_coin(
        self,
        uid: str,
        coin_name: str,
        outcome: str = "",
        clan: str = "",
        rarity: str = "common",
    ) -> None:
        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO coins (uid, coin_name, outcome, clan, rarity)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(uid) DO UPDATE SET
                    coin_name=excluded.coin_name,
                    outcome=CASE WHEN excluded.outcome != '' THEN excluded.outcome ELSE outcome END,
                    clan=CASE WHEN excluded.clan != '' THEN excluded.clan ELSE clan END,
                    rarity=CASE WHEN excluded.rarity != '' THEN excluded.rarity ELSE rarity END
            """, (clean_uid, coin_name, outcome, clan, rarity))

    def get_coin(self, uid: str) -> dict[str, Any] | None:
        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT uid, coin_name, outcome, clan, rarity, created_at FROM coins WHERE uid = ?",
                (clean_uid,),
            )
            row = cur.fetchone()
            if row:
                return {
                    "uid": row[0],
                    "coin_name": row[1],
                    "outcome": row[2],
                    "clan": row[3],
                    "rarity": row[4],
                    "created_at": row[5],
                }
            return None

    def list_all_coins(self) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            cur = conn.execute("SELECT uid, coin_name, outcome, clan, rarity, created_at FROM coins")
            return [
                {
                    "uid": r[0],
                    "coin_name": r[1],
                    "outcome": r[2],
                    "clan": r[3],
                    "rarity": r[4],
                    "created_at": r[5],
                }
                for r in cur.fetchall()
            ]


class ServiceKeyManager(KeyManager):
    """Key Manager delegating cryptographic key custody to tag_validator_service.

    In strict mode (default), checks connection on startup and fails fast
    with actionable operator instructions if tag_validator_service is unreachable.
    Persists coin identity records in SQLite data/app.db.
    """

    def __init__(
        self,
        service_url: str | None = None,
        db_path: str = "data/app.db",
        timeout_sec: float = 3.0,
        strict: bool = True,
        client: TagValidatorClient | None = None,
    ) -> None:
        raw_url = (
            service_url
            or os.environ.get("TAG_VALIDATOR_URL")
            or os.environ.get("KEY_SERVICE_URL")
            or DEFAULT_SERVICE_URL
        )
        self.service_url = raw_url.rstrip("/")
        if not self.service_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid service_url: '{self.service_url}'. Must start with http:// or https://")

        self.timeout_sec = timeout_sec
        self.strict = strict
        self.client = client or TagValidatorClient(service_url=self.service_url, timeout_sec=timeout_sec)
        self.coin_store = SqliteCoinStore(db_path=db_path)

        if self.strict and not self.client.is_healthy():
            raise ConnectionError(
                f"Cannot connect to tag_validator_service at {self.service_url}.\n"
                "sdm_provisioner operates in strict key-vault mode.\n"
                "Please start the key service:\n"
                "    make run-tag-validator"
            )

    @property
    def csv_path(self) -> str:
        """Compatibility property for legacy loggers expecting csv_path."""
        return f"{self.service_url} (SQLite: {self.coin_store.db_path})"

    # ── KeyManager Protocol ──────────────────────────────────────────────────

    def get_key_for_uid(self, uid: bytes, key_no: int) -> bytes:
        """KeyManager abstract interface compatibility."""
        return self.get_key(uid, key_no)

    def get_key(self, uid: UID | bytes | str, key_no: int) -> bytes:
        """Retrieve raw key bytes for APDU operations.

        For Key 0 (PICC Master), Key 1 (App Read), and Key 3 (SDM MAC), fetches
        raw key from tag_validator_service via authorized ?raw=true endpoint.
        """
        if key_no < 0 or key_no > 4:
            raise ValueError(f"Key number must be 0-4, got {key_no}")

        if key_no in (2, 4):
            return b"\x00" * 16

        uid_str = (
            uid.hex().upper()
            if isinstance(uid, (bytes, bytearray))
            else (uid.uid if isinstance(uid, UID) else str(uid).upper())
        )

        try:
            secret = self.client.get_key(uid_str, raw=True)
        except Exception as e:
            log.warning(f"Could not retrieve raw key for UID {uid_str}: {e}")
            secret = None

        if secret:
            if key_no == 0 and secret.get("k0"):
                return bytes.fromhex(secret["k0"])
            elif key_no == 1 and secret.get("k1"):
                return bytes.fromhex(secret["k1"])
            elif key_no == 3 and secret.get("k3"):
                return bytes.fromhex(secret["k3"])

        return b"\x00" * 16

    def get_tag_keys(self, uid: UID | str) -> TagKeys:
        """Retrieve tag keys and coin metadata."""
        uid_obj = uid if isinstance(uid, UID) else UID(str(uid))
        clean_uid = uid_obj.uid

        # 1. Coin metadata from SQLite app.db
        coin_record = self.coin_store.get_coin(clean_uid)
        coin_name = coin_record.get("coin_name", "") if coin_record else ""
        raw_outcome = coin_record.get("outcome", "") if coin_record else ""

        outcome = Outcome.INVALID
        if raw_outcome:
            out_str = raw_outcome.lower()
            if out_str == "heads":
                outcome = Outcome.HEADS
            elif out_str == "tails":
                outcome = Outcome.TAILS

        # 2. Key material from tag_validator_service (raw=True for provisioner)
        try:
            secret = self.client.get_key(clean_uid, raw=True)
        except Exception as e:
            log.warning(f"Could not retrieve secret for UID {clean_uid}: {e}")
            secret = None
        if secret:
            return TagKeys(
                uid=uid_obj,
                picc_master_key=secret.get("k0", "0" * 32),
                app_read_key=secret.get("k1", "0" * 32),
                sdm_mac_key=secret.get("k3", "0" * 32),
                outcome=outcome,
                coin_name=coin_name,
                provisioned_date=secret.get("created_at", datetime.now(UTC).isoformat()),
                status=secret.get("status", "provisioned"),
                notes="Vaulted in tag_validator_service",
            )

        # Tag not yet registered in vault -> return factory keys with coin assignment
        factory = TagKeys.from_factory_keys(uid_obj)
        factory.coin_name = coin_name
        factory.outcome = outcome
        return factory

    def save_tag_keys(self, tag_keys: TagKeys) -> bool:
        """Persist coin metadata in app.db and vaulted keys in tag_validator_service."""
        clean_uid = tag_keys.uid.uid

        # 1. Update coin identity in SQLite
        if tag_keys.coin_name or (tag_keys.outcome and tag_keys.outcome != Outcome.INVALID):
            outcome_val = tag_keys.outcome.value if tag_keys.outcome != Outcome.INVALID else ""
            self.coin_store.set_coin(clean_uid, tag_keys.coin_name, outcome=outcome_val)

        # 2. If non-factory keys are provided, save to tag_validator_service
        k3 = tag_keys.sdm_mac_key
        if k3 and k3 != "0" * 32 and "..." not in k3:
            k0 = tag_keys.picc_master_key or "0" * 32
            k1 = tag_keys.app_read_key or "0" * 32
            status = tag_keys.status or "active"
            return self.client.save_key(clean_uid, k3=k3, k0=k0, k1=k1, status=status)

        return True

    def generate_random_keys(
        self,
        uid: UID | str,
        coin_name: str = "",
        outcome: Outcome = Outcome.INVALID,
    ) -> TagKeys:
        """Atomically generate fresh CSPRNG keys in tag_validator_service."""
        uid_obj = uid if isinstance(uid, UID) else UID(str(uid))
        clean_uid = uid_obj.uid

        body = self.client.generate_key(clean_uid)
        k0 = body.get("k0", "0" * 32)
        k1 = body.get("k1", "0" * 32)
        k3 = body.get("k3", "0" * 32)

        if coin_name or outcome != Outcome.INVALID:
            outcome_val = outcome.value if outcome != Outcome.INVALID else ""
            self.coin_store.set_coin(clean_uid, coin_name, outcome=outcome_val)

        return TagKeys(
            uid=uid_obj,
            picc_master_key=k0,
            app_read_key=k1,
            sdm_mac_key=k3,
            outcome=outcome,
            coin_name=coin_name,
            provisioned_date=datetime.now(UTC).isoformat(),
            status="provisioned",
            notes="Atomically generated and vaulted in tag_validator_service",
        )

    # ── Two-Phase Provisioning & URL Context Managers ────────────────────────

    @contextmanager
    def provision_tag(
        self,
        uid: UID | str,
        url: str | None = None,
        coin_name: str = "",
        outcome: Outcome = Outcome.INVALID,
    ):
        """Context manager for two-phase commit of tag provisioning.

        Phase 1 (Keys): provision_tag(uid, url=None) -> status='keys_configured'
        Phase 2 (URL): provision_tag(uid, url="...") -> status='provisioned'
        """
        uid_obj = uid if isinstance(uid, UID) else UID(str(uid))
        clean_uid = uid_obj.uid

        # Check if keys already exist in vault, otherwise generate them
        existing_secret = self.client.get_key(clean_uid, raw=True)
        if existing_secret:
            staged_keys = TagKeys(
                uid=uid_obj,
                picc_master_key=existing_secret.get("k0", "0" * 32),
                app_read_key=existing_secret.get("k1", "0" * 32),
                sdm_mac_key=existing_secret.get("k3", "0" * 32),
                outcome=outcome,
                coin_name=coin_name,
                provisioned_date=datetime.now(UTC).isoformat(),
                status="pending",
                notes="Provisioning in progress...",
            )
        else:
            staged_keys = self.generate_random_keys(uid_obj, coin_name=coin_name, outcome=outcome)
            staged_keys.status = "pending"
            staged_keys.notes = "Provisioning in progress..."

        success = False
        try:
            yield staged_keys
            success = True
        except Exception as e:
            log.error(f"Provisioning failed for UID {clean_uid}: {e}")
            raise
        finally:
            if success:
                staged_keys.status = "keys_configured" if url is None else "provisioned"
                staged_keys.notes = url or "Keys configured, ready for URL provisioning"
                self.save_tag_keys(staged_keys)

    @contextmanager
    def update_url(self, uid: UID | str, url: str):
        """Context manager for updating NDEF URL on an existing provisioned tag."""
        uid_obj = uid if isinstance(uid, UID) else UID(str(uid))
        tag_keys = self.get_tag_keys(uid_obj)
        success = False
        try:
            yield tag_keys
            success = True
        finally:
            if success:
                tag_keys.status = "provisioned"
                tag_keys.notes = url
                self.save_tag_keys(tag_keys)

    # ── SDM Validation ───────────────────────────────────────────────────────

    def validate_sdm_url(self, uid: UID | str, counter: int, cmac: str) -> dict[str, Any]:
        """Validate SDM URL tap against tag_validator_service."""
        uid_obj = uid if isinstance(uid, UID) else UID(str(uid))
        resp = self.client.validate_tag(uid_obj.uid, counter=counter, cmac=cmac)
        return {
            "valid": resp.get("valid", False),
            "uid": uid_obj,
            "counter": counter,
            "cmac_received": cmac,
            "cmac_calculated": resp.get("cmac_calculated"),
            "error": resp.get("error"),
        }

    # ── Coin Management API ──────────────────────────────────────────────────

    def assign_coin_name(self, uid: UID | str, coin_name: str, outcome: Outcome) -> None:
        """Assign coin name and outcome to tag in app.db with duplicate validation."""
        uid_obj = uid if isinstance(uid, UID) else UID(str(uid))
        clean_uid = uid_obj.uid

        if not coin_name:
            raise ValueError("coin_name cannot be empty")
        if outcome not in (Outcome.HEADS, Outcome.TAILS):
            raise ValueError(f"outcome must be HEADS or TAILS, got {outcome}")

        # Check for duplicate outcome for same coin_name
        existing_tags = self.list_tags()
        for tag in existing_tags:
            if tag.coin_name == coin_name and tag.outcome == outcome and tag.uid.uid != clean_uid:
                raise ValueError(
                    f"Coin '{coin_name}' already has a {outcome.value} tag "
                    f"(UID: {tag.uid.uid}). Cannot assign duplicate outcome."
                )

        self.coin_store.set_coin(clean_uid, coin_name, outcome=outcome.value)

    def list_tags(self) -> list[TagKeys]:
        """List all tags in key vault and SQLite coin database in a single batch query."""
        vault_keys_map: dict[str, dict[str, Any]] = {}
        try:
            raw_keys = self.client.list_keys(include_deleted=True, raw=True)
            for item in raw_keys:
                if isinstance(item, dict) and "uid" in item:
                    vault_keys_map[item["uid"]] = item
                elif isinstance(item, str):
                    vault_keys_map[item] = {"uid": item}
        except Exception as e:
            log.warning(f"Could not batch list keys from service: {e}")

        # Combine with coins from SQLite
        coins = self.coin_store.list_all_coins()
        coins_map = {c["uid"]: c for c in coins}
        all_uids = sorted(list(set(vault_keys_map.keys()) | set(coins_map.keys())))

        result: list[TagKeys] = []
        for u in all_uids:
            coin = coins_map.get(u, {})
            coin_name = coin.get("coin_name", "")
            raw_outcome = coin.get("outcome", "")
            outcome = Outcome.INVALID
            if raw_outcome:
                out_str = raw_outcome.lower()
                if out_str == "heads":
                    outcome = Outcome.HEADS
                elif out_str == "tails":
                    outcome = Outcome.TAILS

            secret = vault_keys_map.get(u)
            if secret and (secret.get("k0") or secret.get("k3")):
                tag = TagKeys(
                    uid=UID(u),
                    picc_master_key=secret.get("k0", "0" * 32),
                    app_read_key=secret.get("k1", "0" * 32),
                    sdm_mac_key=secret.get("k3", "0" * 32),
                    outcome=outcome,
                    coin_name=coin_name,
                    provisioned_date=secret.get("created_at", datetime.now(UTC).isoformat()),
                    status=secret.get("status", "provisioned"),
                    notes="Vaulted in tag_validator_service",
                )
            else:
                tag = TagKeys.from_factory_keys(UID(u))
                tag.coin_name = coin_name
                tag.outcome = outcome

            result.append(tag)

        return result

    def get_coin_tags(self, coin_name: str) -> dict[str, TagKeys | None]:
        """Get heads and tails tags for a coin."""
        result: dict[str, TagKeys | None] = {"heads": None, "tails": None}
        for tag in self.list_tags():
            if tag.coin_name == coin_name:
                if tag.outcome == Outcome.HEADS:
                    result["heads"] = tag
                elif tag.outcome == Outcome.TAILS:
                    result["tails"] = tag
        return result

    def validate_coin(self, coin_name: str) -> dict[str, Any]:
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

    def list_coins(self) -> dict[str, dict[str, Any]]:
        """List all coins and their completeness status."""
        coins: dict[str, dict[str, Any]] = {}
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

    def get_next_coin_assignment(self) -> tuple[str, Outcome]:
        """Determine coin_name and outcome for the next tag."""
        tags = self.list_tags()
        if len(tags) < 2:
            new_name = generate_coin_name()
            return (new_name, Outcome.HEADS)

        last_tag = tags[-1]
        second_last_tag = tags[-2]

        if last_tag.coin_name == second_last_tag.coin_name:
            new_name = generate_coin_name()
            return (new_name, Outcome.HEADS)
        else:
            return (last_tag.coin_name, Outcome.TAILS)

    def delete_key(self, uid: UID | str) -> bool:
        """Soft-delete a key in tag_validator_service."""
        clean_uid = uid.uid if isinstance(uid, UID) else str(uid)
        return self.client.delete_key(clean_uid)

    def undelete_key(self, uid: UID | str) -> bool:
        """Restore a soft-deleted key in tag_validator_service."""
        clean_uid = uid.uid if isinstance(uid, UID) else str(uid)
        return self.client.undelete_key(clean_uid)

    def get_backup_entries(self, uid: UID) -> list[TagKeys]:
        """Compatibility: returns empty list as backups are handled by WORM storage."""
        return []

    def restore_from_backup(self, uid: UID) -> TagKeys | None:
        """Compatibility: returns None as backups are handled by WORM storage."""
        return None

    def is_healthy(self) -> bool:
        """Check if remote key service is reachable."""
        return self.client.is_healthy()
