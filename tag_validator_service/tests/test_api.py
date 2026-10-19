"""Integration and functional tests for Tag Validator REST API."""

import io
import json
from typing import Any

import pytest

from tag_validator.api.app import TagValidatorApp, create_app
from tag_validator.crypto.cmac_engine import calculate_sdm_cmac
from tag_validator.models import TagSecret
from tag_validator.store.memory_store import MemorySecretStore

TEST_UID = "043F13E2151990"
TEST_K3 = "99E88808ADC7885BC7065D739A25E1D0"


class WsgiTestClient:
    """Helper client to invoke WSGI app in tests without live network sockets."""

    def __init__(self, app: TagValidatorApp) -> None:
        self.app = app

    def request(
        self,
        method: str,
        path: str,
        body: Any | None = None,
        query_string: str = "",
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        headers = headers or {}
        body_bytes = b""
        if body is not None:
            if isinstance(body, (dict, list)):
                body_bytes = json.dumps(body).encode("utf-8")
                headers.setdefault("Content-Type", "application/json")
            elif isinstance(body, str):
                body_bytes = body.encode("utf-8")
            elif isinstance(body, bytes):
                body_bytes = body

        environ: dict[str, Any] = {
            "REQUEST_METHOD": method.upper(),
            "PATH_INFO": path,
            "QUERY_STRING": query_string,
            "CONTENT_LENGTH": str(len(body_bytes)),
            "wsgi.input": io.BytesIO(body_bytes),
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "8080",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.errors": io.StringIO(),
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
        }

        for k, v in headers.items():
            cgi_key = "HTTP_" + k.upper().replace("-", "_")
            if k.lower() == "content-type":
                environ["CONTENT_TYPE"] = v
            else:
                environ[cgi_key] = v

        response_status = [200]

        def start_response(status_line: str, resp_headers: Any) -> None:
            response_status[0] = int(status_line.split()[0])

        result_chunks = self.app(environ, start_response)
        raw_response = b"".join(result_chunks).decode("utf-8")

        parsed_json: dict[str, Any] = {}
        if raw_response.strip():
            try:
                parsed_json = json.loads(raw_response)
            except Exception:
                parsed_json = {"_raw": raw_response}

        return response_status[0], parsed_json

    def get(self, path: str, query_string: str = "") -> tuple[int, dict[str, Any]]:
        return self.request("GET", path, query_string=query_string)

    def post(self, path: str, json_body: Any) -> tuple[int, dict[str, Any]]:
        return self.request("POST", path, body=json_body)


@pytest.fixture
def test_client() -> WsgiTestClient:
    store = MemorySecretStore()
    # Seed known key
    store.save_key(TagSecret(uid=TEST_UID, k3=TEST_K3))
    app = create_app(store=store)
    return WsgiTestClient(app)


def test_health_endpoints(test_client: WsgiTestClient):
    status, body = test_client.get("/healthz")
    assert status == 200
    assert body["status"] == "ok"
    assert body["stateless"] is True

    status, body = test_client.get("/readyz")
    assert status == 200
    assert body["status"] == "ready"


def test_validate_post_success(test_client: WsgiTestClient):
    ctr = 5
    expected_cmac = calculate_sdm_cmac(TEST_UID, ctr, TEST_K3)

    status, body = test_client.post(
        "/api/v1/validate",
        {"uid": TEST_UID, "counter": ctr, "cmac": expected_cmac},
    )
    assert status == 200
    assert body["valid"] is True
    assert body["cmac_calculated"] == expected_cmac
    assert body["cmac_received"] == expected_cmac


def test_validate_post_cmac_mismatch(test_client: WsgiTestClient):
    status, body = test_client.post(
        "/api/v1/validate",
        {"uid": TEST_UID, "counter": 5, "cmac": "0000000000000000"},
    )
    assert status == 200
    assert body["valid"] is False
    assert body["error"] == "CMAC mismatch"


def test_validate_post_missing_key(test_client: WsgiTestClient):
    status, body = test_client.post(
        "/api/v1/validate",
        {"uid": "04AABBCCDDEEFF", "counter": 5, "cmac": "0000000000000000"},
    )
    assert status == 404
    assert body["valid"] is False
    assert "not found" in body["error"]


def test_validate_post_invalid_inputs(test_client: WsgiTestClient):
    # Short UID
    status, body = test_client.post(
        "/api/v1/validate",
        {"uid": "04AABB", "counter": 5, "cmac": "A1B2C3D4E5F67890"},
    )
    assert status == 400
    assert "UID must be 14 hex" in body["error"]

    # Negative counter
    status, body = test_client.post(
        "/api/v1/validate",
        {"uid": TEST_UID, "counter": -1, "cmac": "A1B2C3D4E5F67890"},
    )
    assert status == 400
    assert "Counter must be integer" in body["error"]

    # Short CMAC
    status, body = test_client.post(
        "/api/v1/validate",
        {"uid": TEST_UID, "counter": 1, "cmac": "SHORT"},
    )
    assert status == 400
    assert "CMAC must be 16 hex" in body["error"]


def test_validate_get_success(test_client: WsgiTestClient):
    ctr = 10
    expected_cmac = calculate_sdm_cmac(TEST_UID, ctr, TEST_K3)
    query = f"uid={TEST_UID}&ctr={ctr}&cmac={expected_cmac}"

    status, body = test_client.get("/api/v1/validate", query_string=query)
    assert status == 200
    assert body["valid"] is True
    assert body["cmac_calculated"] == expected_cmac


def test_atomic_key_generation_and_worm(test_client: WsgiTestClient):
    gen_uid = "04998877665544"

    # Generate key atomically via CSPRNG
    status, body = test_client.post("/api/v1/keys/generate", {"uid": gen_uid})
    assert status == 201
    assert body["status"] == "created"
    assert body["uid"] == gen_uid
    assert len(body["k3"]) == 32
    generated_k3 = body["k3"]

    # WORM check 1: cannot regenerate existing key
    status, body = test_client.post("/api/v1/keys/generate", {"uid": gen_uid})
    assert status == 409
    assert "already exists" in body["error"]

    # WORM check 2: cannot overwrite with a different key
    status, body = test_client.post(
        "/api/v1/keys",
        {"uid": gen_uid, "k3": "00001111222233334444555566667777"},
    )
    assert status == 409
    assert "immutable" in body["error"]

    # Validate using the freshly generated key works
    expected_cmac = calculate_sdm_cmac(gen_uid, 1, generated_k3)
    status, body = test_client.post(
        "/api/v1/validate",
        {"uid": gen_uid, "counter": 1, "cmac": expected_cmac},
    )
    assert status == 200
    assert body["valid"] is True


def test_key_management_soft_delete_and_undelete(test_client: WsgiTestClient):
    new_uid = "04112233445566"
    new_k3 = "A1A2A3A4A5A6A7A8B1B2B3B4B5B6B7B8"

    # Create key
    status, body = test_client.post(
        "/api/v1/keys",
        {"uid": new_uid, "k3": new_k3},
    )
    assert status == 201
    assert body["status"] == "created"
    assert body["secret"]["uid"] == new_uid
    assert "k3" not in body["secret"]  # Secret unexposed in metadata
    assert body["secret"]["k3_masked"] == "A1A2...B7B8"
    assert "coin_name" not in body["secret"]  # Decoupled domain

    # Get key metadata
    status, body = test_client.get(f"/api/v1/keys/{new_uid}")
    assert status == 200
    assert body["uid"] == new_uid
    assert body["status"] == "active"

    # List keys
    status, body = test_client.get("/api/v1/keys")
    assert status == 200
    assert new_uid in body["uids"]

    # Soft-delete key
    status, body = test_client.request("DELETE", f"/api/v1/keys/{new_uid}")
    assert status == 200
    assert body["status"] == "deleted"

    # Verify filtered out by default
    status, body = test_client.get(f"/api/v1/keys/{new_uid}")
    assert status == 404

    # Validation against soft-deleted key must fail
    cmac_val = calculate_sdm_cmac(new_uid, 1, new_k3)
    status, body = test_client.post(
        "/api/v1/validate",
        {"uid": new_uid, "counter": 1, "cmac": cmac_val},
    )
    assert status == 404
    assert body["valid"] is False

    # List with include_deleted=true includes it
    status, body = test_client.get("/api/v1/keys", query_string="include_deleted=true")
    assert status == 200
    assert new_uid in body["uids"]

    # Undelete key
    status, body = test_client.post(f"/api/v1/keys/{new_uid}/undelete", {})
    assert status == 200
    assert body["status"] == "restored"

    # Validation succeeds again
    status, body = test_client.post(
        "/api/v1/validate",
        {"uid": new_uid, "counter": 1, "cmac": cmac_val},
    )
    assert status == 200
    assert body["valid"] is True

