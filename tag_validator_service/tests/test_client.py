"""Unit tests for official TagValidatorClient SDK."""

from unittest.mock import patch
import pytest

from tag_validator.client import TagValidatorClient, validate_tag_remotely


def test_client_init():
    client = TagValidatorClient(service_url="http://custom-url:8080")
    assert client.service_url == "http://custom-url:8080"


def test_client_init_invalid_scheme():
    with pytest.raises(ValueError, match="Invalid service_url"):
        TagValidatorClient(service_url="tcp://invalid")


def test_validate_tag():
    client = TagValidatorClient(service_url="http://mock-service")
    with patch.object(client, "_http_request") as mock_req:
        mock_req.return_value = (200, {
            "valid": True,
            "uid": "04AE664A2F7080",
            "counter": 10,
            "cmac_calculated": "1122334455667788",
        })
        res = client.validate_tag("04AE664A2F7080", 10, "1122334455667788")
        assert res["valid"] is True
        assert res["counter"] == 10


def test_generate_and_get_key():
    client = TagValidatorClient(service_url="http://mock-service")
    with patch.object(client, "_http_request") as mock_req:
        mock_req.return_value = (201, {
            "status": "created",
            "uid": "04AE664A2F7080",
            "k3": "0123456789ABCDEF0123456789ABCDEF",
        })
        created = client.generate_key("04AE664A2F7080")
        assert created["k3"] == "0123456789ABCDEF0123456789ABCDEF"

        mock_req.return_value = (200, {
            "uid": "04AE664A2F7080",
            "status": "active",
            "k3_masked": "0123...CDEF",
        })
        got = client.get_key("04AE664A2F7080")
        assert got["k3_masked"] == "0123...CDEF"


def test_delete_and_undelete():
    client = TagValidatorClient(service_url="http://mock-service")
    with patch.object(client, "_http_request") as mock_req:
        mock_req.return_value = (200, {"status": "deleted"})
        assert client.delete_key("04AE664A2F7080") is True

        mock_req.return_value = (200, {"status": "restored"})
        assert client.undelete_key("04AE664A2F7080") is True


def test_convenience_function():
    with patch("tag_validator.client.TagValidatorClient.validate_tag") as mock_val:
        mock_val.return_value = {"valid": True}
        res = validate_tag_remotely("04AE664A2F7080", 5, "CMAC123", service_url="http://test")
        assert res["valid"] is True
