"""Tests for CSV importer utility and import endpoint."""

from pathlib import Path

from tag_validator.api.app import create_app
from tag_validator.cli.importer import import_csv_to_store
from tag_validator.store.memory_store import MemorySecretStore

from .test_api import WsgiTestClient

SAMPLE_CSV = """# Sample tag keys backup
uid,picc_master_key,app_read_key,sdm_mac_key,outcome,coin_name,provisioned_date,status
04B7664A2F7080,825F8399CF2CACF92232B79C406170AF,3865245E4C5E4E8B0158FFED3A13539C,C099B6D1E57E1F4F1A2491A919CFA2B1,heads,SWIFT-FALCON-42,2025-11-08T17:24:07,provisioned
04AE664A2F7080,11111111111111111111111111111111,22222222222222222222222222222222,33333333333333333333333333333333,tails,BRAVE-EAGLE-99,2025-11-08T17:25:00,provisioned
INVALID_ROW,short_key
"""


def test_import_csv_to_store(tmp_path: Path):
    csv_file = tmp_path / "test_tag_keys.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")

    imported, skipped, errors = import_csv_to_store(
        csv_path=csv_file,
        backend="memory",
        dry_run=False,
    )
    assert imported == 2
    assert skipped >= 1


def test_import_csv_dry_run(tmp_path: Path):
    csv_file = tmp_path / "test_tag_keys.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")

    imported, skipped, errors = import_csv_to_store(
        csv_path=csv_file,
        dry_run=True,
    )
    assert imported == 2


def test_api_import_csv():
    store = MemorySecretStore()
    app = create_app(store=store)
    client = WsgiTestClient(app)

    status, body = client.request(
        "POST",
        "/api/v1/keys/import-csv",
        body=SAMPLE_CSV,
        headers={"Content-Type": "text/csv"},
    )
    assert status == 200
    assert body["status"] == "complete"
    assert body["imported"] == 2

    # Verify keys are now present in store
    sec = store.get_key("04B7664A2F7080")
    assert sec is not None
    assert sec.k3 == "C099B6D1E57E1F4F1A2491A919CFA2B1"
    assert sec.status == "active"

