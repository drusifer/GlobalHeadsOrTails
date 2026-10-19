"""Multi-pack identity, immutable awards and direct player-weight boundaries."""
import json
import sqlite3

import pytest

from game_server.sticker_service import StickerService
from game_server.flip_off_service import FlipOffService
from game_server.game_state_manager import SqliteGameStateManager
from test_server_stickers import FixedRandom
from test_server_sticker_api import api  # noqa: F401
from test_server_sticker_api import signed
from scripts.sticker_pack_fixtures import select_fixture_pack


def family(identity, rarity, pack):
    return {'id': identity, 'name': identity, 'rarity': rarity, 'pack_id': pack,
            'player': {'name': identity, 'stats': {'regular_season': {'skater': {'gamesPlayed': 1}}}},
            'forms': [{'level': level, 'name': identity, 'image': f'/static/stickers/{identity}.webp',
                       'art_prompt': 'private prompt', 'treatment': str(level)} for level in (1, 2, 3)]}


@pytest.fixture
def packs(tmp_path):
    old = {'pack_name': 'Old', 'families': [family('old-'+r, r, 'old') for r in ('common', 'uncommon', 'rare', 'legendary')]}
    new = {'pack_name': 'New', 'snapshot': '2026-10-07', 'families': [family('new-'+r, r, 'new') for r in ('common', 'uncommon', 'rare', 'legendary')]}
    for name, value in [('old.json', old), ('new.json', new)]:
        (tmp_path/name).write_text(json.dumps(value))
    registry = {'active_pack_id': 'new', 'packs': [
        {'id': 'old', 'catalog': 'old.json', 'selection': {'type': 'legacy_tiers'}},
        {'id': 'new', 'catalog': 'new.json', 'selection': {'type': 'player_weights', 'weights': {'common': 8, 'uncommon': 4, 'rare': 2, 'legendary': 1}}}]}
    path = tmp_path/'packs.json'
    path.write_text(json.dumps(registry))
    return tmp_path, path, registry


def service(packs, roll=0):
    folder, path, _ = packs
    return StickerService(str(folder/'game.db'), rng=FixedRandom(0, roll), registry_path=str(path))


@pytest.mark.parametrize('roll,expected', [(0, 'common'), (8/15, 'uncommon'), (12/15, 'rare'), (14/15, 'legendary'), (.99999, 'legendary')])
def test_direct_player_weights_boundaries(packs, roll, expected):
    stickers = service(packs, roll)
    drop = stickers.award_flip('A', 'a', 1)['drop']
    assert drop['family_id'] == 'new-'+expected
    assert drop['family']['pack_id'] == 'new'
    assert drop['form']['image'] == f'/static/stickers/new-{expected}.webp'
    assert 'art_prompt' not in json.dumps(drop)


def test_activation_keeps_old_awards_and_no_drop_decisions(packs):
    _, path, registry = packs
    registry['active_pack_id'] = 'old'
    path.write_text(json.dumps(registry))
    old = service(packs)
    award = old.award_flip('A', 'a', 1)
    old.rng = FixedRandom(.9)
    no_drop = old.award_flip('A', 'a', 2)
    registry['active_pack_id'] = 'new'
    path.write_text(json.dumps(registry))
    new = service(packs)
    assert new.award_flip('A', 'a', 1) == award
    assert new.award_flip('A', 'a', 2) == no_drop
    assert new.collection('A')[0]['family']['pack_id'] == 'old'
    assert new.award_flip('A', 'a', 3)['drop']['family']['pack_id'] == 'new'


def test_evolution_does_not_cross_pack_and_historical_stakes_survive(packs):
    stickers = service(packs)
    SqliteGameStateManager(str(stickers.db_path))
    flipoff = FlipOffService(str(stickers.db_path), stickers)
    with sqlite3.connect(stickers.db_path) as conn:
        a = stickers._insert(conn, 'A', 'old-common', 1)
        b = stickers._insert(conn, 'B', 'old-common', 1)
        stickers._insert(conn, 'A', 'old-common', 1)
        stickers._insert(conn, 'A', 'new-common', 1)
    challenge = flipoff.create_challenge('A', 'B', 10, a['id'])
    flipoff.accept_challenge(challenge, 'B', b['id'])
    flipoff.yield_challenge('B')
    owned = stickers.collection('A')
    assert {(s['family_id'], s['level']) for s in owned} == {('old-common', 2), ('new-common', 1)}
    historical = flipoff.get_challenge(challenge)
    assert all(s['family']['pack_id'] == 'old' for s in historical['stakes'])
    assert historical['wager_evolutions'][0]['sticker']['family']['pack_id'] == 'old'


@pytest.mark.parametrize('mutation', ['duplicate', 'levels', 'weight', 'active', 'policy', 'empty'])
def test_malformed_registry_rejected_without_fallback(packs, mutation):
    folder, path, registry = packs
    if mutation == 'duplicate':
        new = json.loads((folder/'new.json').read_text())
        new['families'][0]['id'] = 'old-common'
        (folder/'new.json').write_text(json.dumps(new))
    elif mutation == 'levels':
        new = json.loads((folder/'new.json').read_text())
        new['families'][0]['forms'][1]['level'] = 1
        (folder/'new.json').write_text(json.dumps(new))
    elif mutation == 'weight':
        registry['packs'][1]['selection']['weights']['rare'] = 0
    elif mutation == 'active':
        registry['active_pack_id'] = 'missing'
    elif mutation == 'policy':
        registry['packs'][1]['selection']['type'] = 'unknown'
    else:
        registry['packs'] = []
    path.write_text(json.dumps(registry))
    with pytest.raises(ValueError):
        service(packs).catalog


def test_polling_only_sends_owned_family_metadata_and_small_pack_headers(api):
    stickers = api.sticker_service
    assert stickers.catalog['active_pack_id'] == 'twelve-clans'
    assert len(stickers.catalog['families']) == 1174
    with api.test_client() as client:
        empty = client.get('/api/stickers').json
        assert empty['catalog']['families'] == []
        assert empty['stickers'] == []
        assert len(empty['catalog']['packs']) == 2
        assert len(json.dumps(empty)) < 12000
        stickers.award_flip('A', 'a', 1)
        with sqlite3.connect(stickers.db_path) as conn:
            stickers._insert(conn, 'A', 'nyr-8447400', 1)
        owned = client.get('/api/stickers?coin_name=A').json
    assert {f['id'] for f in owned['catalog']['families']} == {'hearthshield-compact', 'nyr-8447400'}
    assert 'art_prompt' not in json.dumps(owned)
    assert next(f for f in owned['catalog']['families'] if f['id']=='nyr-8447400')['player']['stats']['regular_season']['skater']['points'] == 249
    rangers = next(p for p in owned['catalog']['packs'] if p['id']=='rangers-history')
    assert rangers['total_families'] == 1162
    assert rangers['total_forms'] == 3486
    assert rangers['total_player_weight'] == 8197


def test_real_roster_activation_weighted_award_and_archive_behavior(api, tmp_path):
    """Activate the real roster in a temp registry, preserving old decisions and copies."""
    service = api.sticker_service
    old_award = service.award_flip('A','legacy-seed',1)
    service.rng = FixedRandom(.9)
    old_no_drop = service.award_flip('A','legacy-seed',2)
    select_fixture_pack(service, tmp_path, 'rangers-history')
    players = [f for f in service.catalog['families'] if f['pack_id']=='rangers-history']
    # An independent cumulative interval using the reviewed fixed weight contract.
    weights = {'common':8,'uncommon':4,'rare':2,'legendary':1}
    total = sum(weights[f['rarity']] for f in players)
    assert total == 8197
    gretzky_index = next(i for i,f in enumerate(players) if f['id']=='nyr-8447400')
    before = sum(weights[f['rarity']] for f in players[:gretzky_index])
    service.rng = FixedRandom(0,(before+.5)/total)
    with api.test_client() as client:
        fresh = client.get('/api/flip',query_string=signed()).json['sticker_award']
        assert fresh['odds']['drop_chance'] == .05  # Activation leaves entropy policy intact.
        assert fresh['drop']['family_id'] == 'nyr-8447400'
        assert fresh['drop']['rarity'] == 'legendary'
        assert fresh['drop']['family']['player']['stats']['regular_season']['skater']['points'] == 249
        assert fresh['drop']['form']['image'] == '/static/stickers/rangers-history/nyr-8447400.webp'
        empty = client.get('/api/stickers').json
        assert empty['catalog']['active_pack_id'] == 'rangers-history'
        assert empty['catalog']['families'] == [] and empty['stickers'] == []
        assert empty['catalog']['pack_name'].startswith('Broadway Blueshirts')
        owned = client.get('/api/stickers?coin_name=A').json
    assert {f['pack_id'] for f in owned['catalog']['families']} == {'twelve-clans','rangers-history'}
    assert service.award_flip('A','legacy-seed',1) == old_award
    assert service.award_flip('A','legacy-seed',2) == old_no_drop
    assert len(service.collection('A')) == 2
