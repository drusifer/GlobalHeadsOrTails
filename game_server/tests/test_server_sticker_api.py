"""Independent signed-tap boundary checks for collectibles and wager APIs."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from game_server.csv_key_manager import Outcome
from game_server.app import create_app
from game_server.flip_off_service import FlipOffService
from test_server_stickers import FixedRandom
from scripts.sticker_pack_fixtures import select_fixture_pack

UID_A = '0401000000001A'
UID_B = '0402000000002A'
UID_C = '0403000000003A'


class SignedKeys:
    """Small deterministic validation seam; production crypto has its own tests."""
    def get_tag_keys(self, uid):
        coin = {UID_A: 'A', UID_B: 'B', UID_C: 'C'}.get(uid.uid)
        if not coin:
            raise ValueError('Unknown tag')
        return SimpleNamespace(coin_name=coin, outcome=getattr(self, 'outcomes', {}).get(uid.uid, Outcome.HEADS))

    def validate_sdm_url(self, uid, counter, cmac):
        return {'valid': cmac == f'signed-{uid.uid}-{counter}'}


def signed(uid=UID_A, counter=1):
    return {'uid': uid, 'ctr': f'{counter:08x}', 'cmac': f'signed-{uid}-{counter}'}


@pytest.fixture
def api(tmp_path):
    app = create_app(str(tmp_path / 'keys.csv'), str(tmp_path / 'game.db'))
    app.config['TESTING'] = True
    app.key_manager = SignedKeys()
    select_fixture_pack(app.sticker_service, tmp_path, 'twelve-clans')
    app.sticker_service.rng = FixedRandom()
    return app


def seed_wager(app):
    a = app.sticker_service.award_flip('A', 'seed-a', 1)['drop']['id']
    b = app.sticker_service.award_flip('B', 'seed-b', 1)['drop']['id']
    return a, b


def test_signed_flip_awards_and_replay_does_not(api):
    with api.test_client() as client:
        result = client.get('/api/flip', query_string=signed())
        assert result.status_code == 200
        assert result.json['sticker_award']['drop']['coin_name'] == 'A'
        assert client.get('/api/flip', query_string=signed()).status_code == 409
    assert len(api.sticker_service.collection('A')) == 1


@pytest.mark.parametrize('params,status', [({**signed(), 'cmac': 'forged'}, 401), ({**signed(), 'drew_test_outcome': 'invalid'}, 200)])
def test_invalid_flips_never_award(api, params, status):
    with api.test_client() as client:
        response = client.get('/api/flip', query_string=params)
        assert response.status_code == status
    assert api.sticker_service.collection('A') == []
    with sqlite3.connect(api.sticker_service.db_path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM sticker_awards').fetchone()[0] == 0


@pytest.mark.parametrize('credentials,status', [({}, 401), ({**signed(), 'cmac':'forged'},401), (signed(UID_B),403)])
def test_wager_create_requires_matching_signed_coin(api, credentials, status):
    a, _ = seed_wager(api)
    with api.test_client() as client:
        response = client.post('/challenge/create', data={'challenger_coin':'A','challenged_coin':'B','flip_count':10,'sticker_id':a,**credentials})
    assert response.status_code == status
    assert api.flip_off_service.get_active_challenge('A') is None


def test_create_rejects_foreign_copy(api):
    _, b = seed_wager(api)
    with api.test_client() as client:
        response = client.post('/challenge/create', data={'challenger_coin':'A','challenged_coin':'B','flip_count':10,'sticker_id':b,**signed()})
    assert response.status_code == 400
    assert api.sticker_service.collection('B')[0]['locked_challenge_id'] is None


@pytest.mark.parametrize('action', ['accept','cancel','yield'])
def test_wager_mutations_reject_unsigned_and_unrelated_coin(api, action):
    a, b = seed_wager(api)
    cid = api.flip_off_service.create_challenge('A','B',10,a)
    with api.test_client() as client:
        body = {'challenge_id':cid,'coin_name':'B','sticker_id':b}
        assert client.post(f'/challenge/{action}', data=body).status_code == 401
        response = client.post(f'/challenge/{action}', data={**body,**signed(UID_C)})
        assert response.status_code in (400,403)
    assert api.flip_off_service.get_challenge(cid)['wager_status'] == 'awaiting_acceptance'


def test_forged_coin_field_cannot_accept_with_wrong_signature(api):
    a, b = seed_wager(api)
    cid = api.flip_off_service.create_challenge('A','B',10,a)
    with api.test_client() as client:
        response = client.post('/challenge/accept', json={'challenge_id':cid,'coin_name':'B','sticker_id':b,**signed(UID_A)})
        assert response.status_code == 400
        accepted = client.post('/challenge/accept', json={'challenge_id':cid,'sticker_id':b,**signed(UID_B)})
        assert accepted.status_code == 200
        yielded = client.post('/challenge/yield', data={'coin_name':'B',**signed(UID_B)})
        assert yielded.status_code == 200
        assert client.post('/challenge/yield', data={'coin_name':'B',**signed(UID_B)}).status_code == 400
    assert {s['id'] for s in api.sticker_service.collection('A')} == {a,b}


def test_signed_concurrent_flip_counts_and_awards_once(api):
    cid = api.flip_off_service.create_challenge('A','B',10)
    def flip(_):
        with api.test_client() as client:
            return client.get('/api/flip', query_string=signed()).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(flip, range(2)))
    assert sorted(statuses) == [200,409]
    assert api.flip_off_service.get_challenge(cid)['challenger_flips_done'] == 1
    assert len(api.sticker_service.collection('A')) == 1


def test_legacy_challenge_database_migrates_without_losing_rows(tmp_path):
    db = str(tmp_path/'legacy.db')
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE flip_off_challenges (id INTEGER PRIMARY KEY, created_at TEXT, baseline_scan_id INTEGER, challenger_coin_name TEXT, challenged_coin_name TEXT, flip_count INTEGER, status TEXT, challenger_flips_done INTEGER, challenged_flips_done INTEGER, challenger_entropy REAL, challenged_entropy REAL, winner_coin_name TEXT, completed_at TEXT)")
        conn.execute("INSERT INTO flip_off_challenges VALUES (1,'2026-01-01',0,'A','B',10,'complete',10,10,1,0,'A','2026-01-01')")
    service = FlipOffService(db)
    challenge = service.get_challenge(1)
    assert challenge['winner_coin_name'] == 'A'
    assert challenge['wagered'] is False
    assert challenge['stakes'] == []


def test_award_failure_rolls_back_logged_scan_and_allows_retry(api):
    class BrokenRandom:
        def random(self):
            raise RuntimeError('Simulated interruption')
    api.sticker_service.rng = BrokenRandom()
    with api.test_client() as client:
        with pytest.raises(RuntimeError, match='Simulated interruption'):
            client.get('/api/flip', query_string=signed())
        api.sticker_service.rng = FixedRandom()
        retry = client.get('/api/flip', query_string=signed())
        assert retry.status_code == 200
    with sqlite3.connect(api.sticker_service.db_path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM scan_logs WHERE is_test IS FALSE').fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM sticker_awards').fetchone()[0] == 1


def test_uid_case_variant_cannot_replay_for_second_award(api):
    with api.test_client() as client:
        assert client.get('/api/flip', query_string=signed()).status_code == 200
        params = signed()
        params['uid'] = UID_A.lower()
        assert client.get('/api/flip', query_string=params).status_code == 409
    assert len(api.sticker_service.collection('A')) == 1


@pytest.mark.parametrize('path', ['/challenge/accept','/challenge/cancel'])
def test_malformed_json_wager_payload_rejected(api, path):
    with api.test_client() as client:
        assert client.post(path, json=['bad']).status_code == 400


def test_inventory_omits_generation_prompts(api):
    seed_wager(api)
    with api.test_client() as client:
        response = client.get('/api/stickers?coin_name=A')
    assert response.status_code == 200
    copy = response.json['stickers'][0]
    assert 'forms' not in copy['family']
    assert 'art_prompt' not in copy['form']


def test_progress_failure_rolls_back_scan_award_and_progress(api):
    class InterruptedFlipOff(FlipOffService):
        def record_flip(self, coin_name, conn=None):
            super().record_flip(coin_name, conn=conn)
            raise RuntimeError('Interrupted progress')
    cid = api.flip_off_service.create_challenge('A','B',10)
    api.flip_off_service = InterruptedFlipOff(str(api.sticker_service.db_path), api.sticker_service)
    with api.test_client() as client:
        with pytest.raises(RuntimeError, match='Interrupted progress'):
            client.get('/api/flip', query_string=signed())
    assert api.flip_off_service.get_challenge(cid)['challenger_flips_done'] == 0
    assert api.sticker_service.collection('A') == []
    with sqlite3.connect(api.sticker_service.db_path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM scan_logs WHERE is_test IS FALSE').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM sticker_awards').fetchone()[0] == 0


def test_existing_wager_table_adds_empty_evolution_history(tmp_path):
    db = str(tmp_path/'wager-migration.db')
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE flip_off_wagers (challenge_id INTEGER PRIMARY KEY,status TEXT NOT NULL,challenger_stake TEXT NOT NULL,challenged_stake TEXT)')
        conn.execute("INSERT INTO flip_off_wagers VALUES (1,'returned','{}',NULL)")
    FlipOffService(db)
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT evolution_events FROM flip_off_wagers WHERE challenge_id=1').fetchone()[0] == '[]'


def test_final_uncommitted_flip_determines_wager_winner(api):
    a, b = seed_wager(api)
    cid = api.flip_off_service.create_challenge('A','B',10,a)
    api.flip_off_service.accept_challenge(cid,'B',b)
    api.key_manager.outcomes = {UID_A:Outcome.TAILS, UID_B:Outcome.TAILS}
    with api.test_client() as client:
        for counter in range(1,11):
            assert client.get('/api/flip', query_string=signed(UID_B,counter)).status_code == 200
        for counter in range(1,10):
            assert client.get('/api/flip', query_string=signed(UID_A,counter)).status_code == 200
        api.key_manager.outcomes[UID_A] = Outcome.HEADS
        final = client.get('/api/flip', query_string=signed(UID_A,10))
        assert final.status_code == 200
    challenge = api.flip_off_service.get_challenge(cid)
    assert challenge['status'] == 'complete'
    assert challenge['winner_coin_name'] == 'A'
    assert challenge['challenger_entropy'] > challenge['challenged_entropy']
    assert challenge['wager_status'] == 'settled'
    assert all(s['locked_challenge_id'] is None for coin in ('A','B') for s in api.sticker_service.collection(coin))


@pytest.mark.parametrize('accepted', [False, True])
def test_yield_rechecks_current_wager_authorization_inside_transaction(api, accepted):
    """A stale precheck cannot authorize a replacement wager's cancellation/loss."""
    a, b = seed_wager(api)
    cid = api.flip_off_service.create_challenge('A', 'B', 10, a)
    if accepted:
        api.flip_off_service.accept_challenge(cid, 'B', b)

    class StalePrecheck(FlipOffService):
        def get_active_challenge(self, coin_name):
            return None

    api.flip_off_service = StalePrecheck(str(api.sticker_service.db_path), api.sticker_service)
    with api.test_client() as client:
        response = client.post('/challenge/yield', data={'coin_name': 'B'})
    assert response.status_code == 400
    challenge = api.flip_off_service.get_challenge(cid)
    assert challenge['status'] == 'pending'
    assert challenge['wager_status'] == ('accepted' if accepted else 'awaiting_acceptance')
    assert api.sticker_service.collection('A')[0]['locked_challenge_id'] == cid
    assert api.sticker_service.collection('B')[0]['coin_name'] == 'B'


@pytest.mark.parametrize('outcome', ['heads', 'tails'])
def test_test_flips_award_evolve_and_do_not_reroll(api, outcome):
    with api.test_client() as client:
        for counter in range(1, 10):
            params = {**signed(counter=counter), 'cmac': 'dummy', 'drew_test_outcome': outcome}
            result = client.get('/api/flip', query_string=params)
            assert result.status_code == 200
            assert result.json['sticker_award']['drop']['coin_name'] == 'A'
        copies = api.sticker_service.collection('A')
        assert len(copies) == 1 and copies[0]['level'] == 3
        repeated = client.get('/api/flip', query_string=params)
        assert repeated.json['sticker_award'] == result.json['sticker_award']
        assert api.sticker_service.collection('A') == copies
        # Test counters do not consume the signed-tap award identity.
        assert api.sticker_service.award_flip('A', UID_A, 9)['drop']
