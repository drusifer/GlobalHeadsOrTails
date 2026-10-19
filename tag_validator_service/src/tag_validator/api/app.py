"""Stateless REST API for NTAG 424 DNA SDM CMAC Validation and Tag Key Secrets.

Pure Python WSGI application with zero external framework dependencies.
Compatible with Gunicorn, uWSGI, wsgiref, and modern serverless runtimes.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs

from ..config import get_config
from ..crypto.cmac_engine import verify_sdm_cmac
from ..models import TagSecret, ValidationResult
from ..store import TagKeyStore, create_secret_store

log = logging.getLogger(__name__)


class TagValidatorApp:
    """WSGI Application for stateless tag validation and k3s secret management."""

    def __init__(self, store: TagKeyStore | None = None) -> None:
        if store is not None:
            self.store = store
        else:
            cfg = get_config()
            self.store = create_secret_store(
                backend=cfg.secret_store_backend,
                namespace=cfg.tag_secrets_namespace,
                kubeconfig_path=cfg.kubeconfig_path or None,
            )

    def __call__(
        self,
        environ: dict[str, Any],
        start_response: Callable[[str, list[tuple[str, str]]], Any],
    ) -> list[bytes]:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/").rstrip("/") or "/"

        # Handle CORS Preflight
        if method == "OPTIONS":
            return self._cors_response(start_response)

        try:
            # Route matching
            if path in ("/healthz", "/health"):
                return self._handle_healthz(start_response)
            if path in ("/readyz", "/ready"):
                return self._handle_readyz(start_response)
            if path == "/api/v1/validate":
                if method == "POST":
                    return self._handle_validate_post(environ, start_response)
                elif method == "GET":
                    return self._handle_validate_get(environ, start_response)
                else:
                    return self._json_response(start_response, 405, {"error": "Method Not Allowed"})
            if path == "/api/v1/keys":
                if method == "POST":
                    return self._handle_save_key(environ, start_response)
                elif method == "GET":
                    return self._handle_list_keys(start_response)
                else:
                    return self._json_response(start_response, 405, {"error": "Method Not Allowed"})
            if path.startswith("/api/v1/keys/"):
                subpath = path[len("/api/v1/keys/"):]
                if subpath == "import-csv" and method == "POST":
                    return self._handle_import_csv(environ, start_response)
                if method == "GET":
                    return self._handle_get_key(subpath, start_response)
                elif method == "DELETE":
                    return self._handle_delete_key(subpath, start_response)
                else:
                    return self._json_response(start_response, 405, {"error": "Method Not Allowed"})

            return self._json_response(start_response, 404, {"error": "Endpoint Not Found", "path": path})

        except Exception as e:
            log.exception(f"Unhandled exception during {method} {path}: {e}")
            return self._json_response(start_response, 500, {"error": "Internal Server Error", "detail": str(e)})

    # ── Route Handlers ────────────────────────────────────────────────────────

    def _handle_healthz(self, start_response: Callable) -> list[bytes]:
        return self._json_response(start_response, 200, {
            "status": "ok",
            "service": "tag-validator-service",
            "stateless": True,
        })

    def _handle_readyz(self, start_response: Callable) -> list[bytes]:
        healthy = self.store.is_healthy()
        status_code = 200 if healthy else 503
        return self._json_response(start_response, status_code, {
            "status": "ready" if healthy else "not_ready",
            "store_healthy": healthy,
        })

    def _handle_validate_post(self, environ: dict[str, Any], start_response: Callable) -> list[bytes]:
        body = self._read_json_body(environ)
        if body is None:
            return self._json_response(start_response, 400, {"error": "Invalid or missing JSON body"})

        uid = body.get("uid")
        counter = body.get("counter") if "counter" in body else body.get("ctr")
        cmac = body.get("cmac")

        return self._execute_validation(uid, counter, cmac, start_response)

    def _handle_validate_get(self, environ: dict[str, Any], start_response: Callable) -> list[bytes]:
        qs = parse_qs(environ.get("QUERY_STRING", ""))
        uid = qs.get("uid", [None])[0]
        counter = qs.get("counter", [None])[0] or qs.get("ctr", [None])[0]
        cmac = qs.get("cmac", [None])[0]

        return self._execute_validation(uid, counter, cmac, start_response)

    def _execute_validation(
        self,
        uid_raw: Any,
        counter_raw: Any,
        cmac_raw: Any,
        start_response: Callable,
    ) -> list[bytes]:
        if not uid_raw or counter_raw is None or not cmac_raw:
            return self._json_response(
                start_response,
                400,
                {"valid": False, "error": "Missing required fields: uid, counter (or ctr), cmac"},
            )

        uid_str = str(uid_raw).strip().replace(":", "").replace("-", "").upper()
        if len(uid_str) != 14:
            return self._json_response(
                start_response,
                400,
                {"valid": False, "error": f"UID must be 14 hex characters, got '{uid_raw}'"},
            )

        try:
            counter = int(counter_raw)
            if counter < 0 or counter > 0xFFFFFF:
                raise ValueError()
        except ValueError:
            return self._json_response(
                start_response,
                400,
                {"valid": False, "error": f"Counter must be integer between 0 and 16777215, got '{counter_raw}'"},
            )

        cmac_str = str(cmac_raw).strip().replace(" ", "").upper()
        if len(cmac_str) != 16:
            return self._json_response(
                start_response,
                400,
                {"valid": False, "error": f"CMAC must be 16 hex characters (8 bytes), got '{cmac_raw}'"},
            )

        # Lookup Tag Secret (Key 3 / SDM MAC Key)
        secret = self.store.get_key(uid_str)
        if not secret:
            return self._json_response(
                start_response,
                404,
                {
                    "valid": False,
                    "uid": uid_str,
                    "counter": counter,
                    "cmac_received": cmac_str,
                    "error": "Tag key secret not found in k3s store",
                },
            )

        # Compute CMAC and constant-time verify
        try:
            is_valid, cmac_calc = verify_sdm_cmac(
                uid=uid_str,
                counter=counter,
                k3_hex=secret.k3,
                received_cmac=cmac_str,
            )
        except Exception as e:
            log.error(f"Error computing SDM CMAC for UID {uid_str}: {e}")
            return self._json_response(
                start_response,
                500,
                {"valid": False, "error": "Cryptographic verification failure", "detail": str(e)},
            )

        result = ValidationResult(
            valid=is_valid,
            uid=uid_str,
            counter=counter,
            cmac_received=cmac_str,
            cmac_calculated=cmac_calc,
            error=None if is_valid else "CMAC mismatch",
        )
        return self._json_response(start_response, 200, result.to_dict())

    def _handle_save_key(self, environ: dict[str, Any], start_response: Callable) -> list[bytes]:
        body = self._read_json_body(environ)
        if not body:
            return self._json_response(start_response, 400, {"error": "Invalid JSON body"})

        uid = body.get("uid")
        k3 = body.get("k3") or body.get("sdm_mac_key")
        coin_name = body.get("coin_name", "")
        status = body.get("status", "active")

        if not uid or not k3:
            return self._json_response(start_response, 400, {"error": "Missing uid or k3 (sdm_mac_key)"})

        try:
            secret = TagSecret(uid=uid, k3=k3, coin_name=coin_name, status=status)
        except ValueError as e:
            return self._json_response(start_response, 400, {"error": str(e)})

        success = self.store.save_key(secret)
        if not success:
            return self._json_response(start_response, 500, {"error": "Failed to persist secret to store"})

        return self._json_response(
            start_response,
            201,
            {"status": "created", "secret": secret.to_dict(include_secret=False)},
        )

    def _handle_get_key(self, uid: str, start_response: Callable) -> list[bytes]:
        secret = self.store.get_key(uid)
        if not secret:
            return self._json_response(start_response, 404, {"error": f"Tag key not found for UID '{uid}'"})
        return self._json_response(start_response, 200, secret.to_dict(include_secret=False))

    def _handle_delete_key(self, uid: str, start_response: Callable) -> list[bytes]:
        deleted = self.store.delete_key(uid)
        if not deleted:
            return self._json_response(start_response, 404, {"error": f"Tag key not found for UID '{uid}'"})
        return self._json_response(start_response, 200, {"status": "deleted", "uid": uid.upper()})

    def _handle_list_keys(self, start_response: Callable) -> list[bytes]:
        uids = self.store.list_uids()
        return self._json_response(start_response, 200, {"count": len(uids), "uids": uids})

    def _handle_import_csv(self, environ: dict[str, Any], start_response: Callable) -> list[bytes]:
        raw_text = self._read_text_body(environ)
        if not raw_text.strip():
            return self._json_response(start_response, 400, {"error": "Empty CSV content"})

        imported = 0
        skipped = 0
        errors = []

        try:
            f = io.StringIO(raw_text)
            reader = csv.reader(f)
            for row_idx, row in enumerate(reader, start=1):
                if not row or not row[0].strip() or row[0].strip().startswith("#"):
                    continue

                # Header detection
                first_col = row[0].strip().lower()
                if first_col in ("uid", "tag_uid", "asset_tag"):
                    continue

                try:
                    uid = row[0].strip()
                    # Determine column layout:
                    # Layout A (standard tag_keys.csv): uid, picc_master_key, app_read_key, sdm_mac_key, outcome, coin_name...
                    # Layout B (uid, k3, coin_name)
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
                    if self.store.save_key(secret):
                        imported += 1
                    else:
                        errors.append(f"Row {row_idx}: Storage failure for UID {uid}")
                except Exception as e:
                    errors.append(f"Row {row_idx}: {e}")
                    skipped += 1

            return self._json_response(start_response, 200, {
                "status": "complete",
                "imported": imported,
                "skipped": skipped,
                "errors": errors,
            })
        except Exception as e:
            return self._json_response(start_response, 400, {"error": f"CSV parse error: {e}"})

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _read_json_body(self, environ: dict[str, Any]) -> dict[str, Any] | None:
        raw = self._read_text_body(environ)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    def _read_text_body(self, environ: dict[str, Any]) -> str:
        try:
            length = int(environ.get("CONTENT_LENGTH", 0) or 0)
        except ValueError:
            length = 0
        if length > 0:
            stream = environ.get("wsgi.input")
            if stream:
                return stream.read(length).decode("utf-8", errors="replace")
        return ""

    def _json_response(
        self,
        start_response: Callable,
        status_code: int,
        payload: dict[str, Any],
    ) -> list[bytes]:
        data = json.dumps(payload, indent=2).encode("utf-8")
        status_text = f"{status_code} " + {
            200: "OK",
            201: "Created",
            400: "Bad Request",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error",
            503: "Service Unavailable",
        }.get(status_code, "Status")

        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(data))),
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type, Authorization"),
        ]
        start_response(status_text, headers)
        return [data]

    def _cors_response(self, start_response: Callable) -> list[bytes]:
        headers = [
            ("Content-Type", "text/plain"),
            ("Content-Length", "0"),
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type, Authorization"),
        ]
        start_response("204 No Content", headers)
        return [b""]


def create_app(store: TagKeyStore | None = None) -> TagValidatorApp:
    """Factory creating configured TagValidatorApp WSGI application."""
    return TagValidatorApp(store=store)
