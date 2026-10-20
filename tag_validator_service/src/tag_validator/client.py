"""Official Python HTTP Client SDK for tag_validator_service."""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)

DEFAULT_SERVICE_URL = "http://localhost:8080"


class TagValidatorClient:
    """Client for communicating with the standalone tag_validator_service."""

    def __init__(self, service_url: str | None = None, timeout_sec: float = 3.0) -> None:
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

    def is_healthy(self) -> bool:
        """Check if service is reachable and reports healthy status."""
        status_code, body = self._http_request("GET", "/healthz")
        return status_code == 200 and body.get("status") == "ok"

    def is_ready(self) -> bool:
        """Check if service backend secret store is ready."""
        status_code, body = self._http_request("GET", "/readyz")
        return status_code == 200 and body.get("status") == "ready"

    def validate_tag(self, uid: str, counter: int, cmac: str) -> dict[str, Any]:
        """Validate an NTAG 424 DNA SDM tap against the vaulted key secret."""
        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        clean_cmac = cmac.strip().replace(" ", "").upper()

        status_code, body = self._http_request("POST", "/api/v1/validate", {
            "uid": clean_uid,
            "counter": counter,
            "cmac": clean_cmac,
        })

        if status_code == 200:
            return body

        return {
            "valid": False,
            "uid": clean_uid,
            "counter": counter,
            "cmac_received": clean_cmac,
            "error": body.get("error", f"Validation request failed (HTTP {status_code})"),
        }

    def generate_key(self, uid: str) -> dict[str, Any]:
        """Atomically generate fresh CSPRNG AES-128 keys (k0, k1, k3) and commit to WORM vault."""
        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        status_code, body = self._http_request("POST", "/api/v1/keys/generate", {"uid": clean_uid})
        if status_code == 201:
            return body
        raise RuntimeError(f"Failed to generate key (HTTP {status_code}): {body.get('error', 'Unknown error')}")

    def get_key(self, uid: str, raw: bool = False) -> dict[str, Any] | None:
        """Retrieve key status and metadata from service. If raw=True, returns raw k0, k1, k3."""
        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        qs = "?raw=true" if raw else ""
        status_code, body = self._http_request("GET", f"/api/v1/keys/{clean_uid}{qs}")
        if status_code == 200:
            return body
        if status_code == 404:
            return None
        raise RuntimeError(f"Failed to retrieve key (HTTP {status_code}): {body.get('error', 'Unknown error')}")

    def save_key(
        self,
        uid: str,
        k3: str,
        k0: str = "00000000000000000000000000000000",
        k1: str = "00000000000000000000000000000000",
        status: str = "active",
    ) -> bool:
        """Save existing AES-128 keys into the service."""
        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        payload = {
            "uid": clean_uid,
            "k3": k3.strip().upper(),
            "k0": k0.strip().upper(),
            "k1": k1.strip().upper(),
            "status": status,
        }
        status_code, _ = self._http_request("POST", "/api/v1/keys", payload)
        return status_code in (200, 201)

    def delete_key(self, uid: str) -> bool:
        """Soft-delete a key (tombstone)."""
        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        status_code, _ = self._http_request("DELETE", f"/api/v1/keys/{clean_uid}")
        return status_code == 200

    def undelete_key(self, uid: str) -> bool:
        """Restore a soft-deleted key back to active."""
        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        status_code, _ = self._http_request("POST", f"/api/v1/keys/{clean_uid}/undelete", {})
        return status_code == 200

    def list_keys(self, include_deleted: bool = False, raw: bool = False) -> list[Any]:
        """List tag keys known to the service.

        If raw=True, returns list of dicts with full raw key data.
        Otherwise, returns list of UID strings.
        """
        qs_parts = []
        if include_deleted:
            qs_parts.append("include_deleted=true")
        if raw:
            qs_parts.append("raw=true")
        qs = f"?{'&'.join(qs_parts)}" if qs_parts else ""
        status_code, body = self._http_request("GET", f"/api/v1/keys{qs}")
        if status_code == 200:
            if raw:
                return body.get("keys", [])
            return body.get("uids", [])
        return []


def validate_tag_remotely(
    uid: str,
    counter: int,
    cmac: str,
    service_url: str | None = None,
    timeout_sec: float = 3.0,
) -> dict[str, Any]:
    """Convenience helper to validate a tag tap against tag_validator_service."""
    client = TagValidatorClient(service_url=service_url, timeout_sec=timeout_sec)
    return client.validate_tag(uid, counter, cmac)
