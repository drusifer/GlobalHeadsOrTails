"""Explicit pack selection shared by isolated server and browser test fixtures."""
import json
from pathlib import Path


def select_fixture_pack(service, directory, active_pack_id):
    """Bind the existing service to a temporary registry without changing production."""
    source = Path(__file__).resolve().parents[1]/'src/ntag424_sdm_provisioner/server/sticker_packs.json'
    registry = json.loads(source.read_text())
    for entry in registry['packs']:
        entry['catalog'] = str(source.parent/entry['catalog'])
    registry['active_pack_id'] = active_pack_id
    target = Path(directory)/f'fixture-{active_pack_id}.json'
    target.write_text(json.dumps(registry))
    service.registry_path = target
    service._catalog = None
    assert service.catalog['active_pack_id'] == active_pack_id
