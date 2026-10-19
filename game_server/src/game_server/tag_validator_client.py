"""HTTP Client Adapter for tag_validator_service."""

from __future__ import annotations

import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)

DEFAULT_SERVICE_URL = "http://localhost:8080"


def validate_tag_remotely(
    uid: str,
    counter: int,
    cmac: str,
    service_url: str | None = None,
    timeout_sec: float = 3.0,
) -> dict:
    """Validates an SDM tap CMAC via the standalone tag_validator_service.

    Args:
        uid: 14-hex character tag UID.
        counter: SDM read counter integer.
        cmac: 16-hex character truncated CMAC.
        service_url: Base URL of tag_validator_service (e.g. http://localhost:8080).
        timeout_sec: HTTP request timeout in seconds.

    Returns:
        Dict with keys: valid (bool), uid (str), counter (int), error (str | None).
    """
    raw_url = service_url or os.environ.get("TAG_VALIDATOR_URL", DEFAULT_SERVICE_URL)
    base_url = raw_url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        raise ValueError(f"Invalid service_url scheme: {base_url}. Must start with http:// or https://")

    endpoint = f"{base_url}/api/v1/validate"

    payload = json.dumps({
        "uid": uid.strip().replace(":", "").replace("-", "").upper(),
        "counter": counter,
        "cmac": cmac.strip().replace(" ", "").upper(),
    }).encode("utf-8")

    req = Request(  # noqa: S310
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout_sec) as resp:  # noqa: S310
            data = resp.read()
            return json.loads(data.decode("utf-8"))
    except HTTPError as e:
        try:
            err_data = e.read()
            parsed = json.loads(err_data.decode("utf-8"))
            return parsed
        except Exception:
            return {
                "valid": False,
                "uid": uid,
                "counter": counter,
                "error": f"HTTP {e.code}: {e.reason}",
            }
    except URLError as e:
        log.warning(f"Could not reach tag_validator_service at {endpoint}: {e}")
        return {
            "valid": False,
            "uid": uid,
            "counter": counter,
            "error": f"Connection failed to key service: {e.reason}",
        }
    except Exception as e:
        log.error(f"Unexpected error validating tag with key service: {e}")
        return {
            "valid": False,
            "uid": uid,
            "counter": counter,
            "error": f"Validation client error: {e}",
        }
