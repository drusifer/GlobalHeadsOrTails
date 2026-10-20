"""Data models for tag keys and validation requests."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class TagSecret:
    """Represents a tag's cryptographic keys stored in k3s secrets.

    Stores Key 0 (PICC Master Key), Key 1 (App Read Key), and Key 3 (SDM MAC Key)
    per specification, with internal WORM status.
    """

    uid: str
    k3: str  # 32-character hex AES-128 key
    k0: str = "00000000000000000000000000000000"  # Key 0 (PICC Master Key)
    k1: str = "00000000000000000000000000000000"  # Key 1 (App Read Key)
    status: str = "active"  # "active" | "deleted"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    deleted_at: str | None = None

    def __post_init__(self) -> None:
        self.uid = self.uid.strip().replace(":", "").replace("-", "").upper()
        self.k3 = self.k3.strip().replace(" ", "").upper()
        self.k0 = self.k0.strip().replace(" ", "").upper()
        self.k1 = self.k1.strip().replace(" ", "").upper()
        if len(self.uid) != 14:
            raise ValueError(f"UID must be 14 hex characters, got '{self.uid}'")
        if len(self.k3) != 32:
            raise ValueError(f"K3 must be 32 hex characters (16 bytes), got '{self.k3}'")
        if len(self.k0) != 32:
            raise ValueError(f"K0 must be 32 hex characters (16 bytes), got '{self.k0}'")
        if len(self.k1) != 32:
            raise ValueError(f"K1 must be 32 hex characters (16 bytes), got '{self.k1}'")

    @property
    def secret_name(self) -> str:
        """RFC 1123 compliant secret name for Kubernetes/k3s."""
        return f"tag-key-{self.uid.lower()}"

    def masked_k3(self) -> str:
        """Masked representation of K3 for safe display/logging."""
        if len(self.k3) == 32:
            return f"{self.k3[:4]}...{self.k3[-4:]}"
        return "..."

    def masked_k0(self) -> str:
        """Masked representation of K0 for safe display/logging."""
        if len(self.k0) == 32:
            return f"{self.k0[:4]}...{self.k0[-4:]}"
        return "..."

    def masked_k1(self) -> str:
        """Masked representation of K1 for safe display/logging."""
        if len(self.k1) == 32:
            return f"{self.k1[:4]}...{self.k1[-4:]}"
        return "..."

    def to_k8s_secret_data(self) -> dict[str, str]:
        """Encodes values for Kubernetes Secret .data dictionary (base64 string values)."""
        data = {
            "uid": base64.b64encode(self.uid.encode("utf-8")).decode("utf-8"),
            "k0": base64.b64encode(self.k0.encode("utf-8")).decode("utf-8"),
            "k1": base64.b64encode(self.k1.encode("utf-8")).decode("utf-8"),
            "k3": base64.b64encode(self.k3.encode("utf-8")).decode("utf-8"),
            "status": base64.b64encode(self.status.encode("utf-8")).decode("utf-8"),
            "created_at": base64.b64encode(self.created_at.encode("utf-8")).decode("utf-8"),
        }
        if self.deleted_at:
            data["deleted_at"] = base64.b64encode(self.deleted_at.encode("utf-8")).decode("utf-8")
        return data

    @classmethod
    def from_k8s_secret_data(cls, secret_data: dict[str, Any]) -> TagSecret:
        """Decodes values from Kubernetes Secret dictionary."""
        def _decode(val: Any) -> str:
            if isinstance(val, bytes):
                return val.decode("utf-8")
            if isinstance(val, str):
                try:
                    # In k8s client, .data may be pre-decoded or raw base64
                    decoded = base64.b64decode(val.encode("utf-8")).decode("utf-8")
                    return decoded
                except Exception:
                    return val
            return str(val)

        uid = _decode(secret_data.get("uid", ""))
        k3 = _decode(secret_data.get("k3", "") or secret_data.get("sdm_mac_key", ""))
        k0 = _decode(secret_data.get("k0", "") or secret_data.get("picc_master_key", "")) or "00000000000000000000000000000000"
        k1 = _decode(secret_data.get("k1", "") or secret_data.get("app_read_key", "")) or "00000000000000000000000000000000"
        status = _decode(secret_data.get("status", "active"))
        created_at = _decode(secret_data.get("created_at", ""))
        raw_deleted_at = secret_data.get("deleted_at")
        deleted_at = _decode(raw_deleted_at) if raw_deleted_at else None

        return cls(
            uid=uid,
            k3=k3,
            k0=k0,
            k1=k1,
            status=status,
            created_at=created_at or datetime.now(timezone.utc).isoformat(),
            deleted_at=deleted_at,
        )

    def to_dict(self, include_secret: bool = False) -> dict[str, Any]:
        """Dictionary representation for JSON serialization."""
        data: dict[str, Any] = {
            "uid": self.uid,
            "secret_name": self.secret_name,
            "status": self.status,
            "created_at": self.created_at,
            "k0_masked": self.masked_k0(),
            "k1_masked": self.masked_k1(),
            "k3_masked": self.masked_k3(),
        }
        if self.deleted_at:
            data["deleted_at"] = self.deleted_at
        if include_secret:
            data["k0"] = self.k0
            data["k1"] = self.k1
            data["k3"] = self.k3
        return data


@dataclass
class ValidationResult:
    """Result of an SDM CMAC validation request."""

    valid: bool
    uid: str
    counter: int
    cmac_received: str
    cmac_calculated: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {
            "valid": self.valid,
            "uid": self.uid,
            "counter": self.counter,
            "cmac_received": self.cmac_received,
        }
        if self.cmac_calculated:
            res["cmac_calculated"] = self.cmac_calculated
        if self.error:
            res["error"] = self.error
        return res
