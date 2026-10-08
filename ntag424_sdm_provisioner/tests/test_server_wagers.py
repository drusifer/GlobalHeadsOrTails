"""Wager agreement and atomic terminal ownership transitions."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from ntag424_sdm_provisioner.server.flip_off_service import FlipOffError, FlipOffService
from ntag424_sdm_provisioner.server.game_state_manager import SqliteGameStateManager
from tests.test_server_stickers import stickers  # noqa: F401


@pytest.fixture
def wager(stickers):
    SqliteGameStateManager(str(stickers.db_path))
    service = FlipOffService(str(stickers.db_path), stickers)
    a = stickers.award_flip('A', 'a', 1)['drop']['id']
    b = stickers.award_flip('B', 'b', 1)['drop']['id']
    return service, stickers, a, b


def test_agreement_gates_progress_and_locks_both(wager):
    service, stickers, a, b = wager
    cid = service.create_challenge('A', 'B', 10, a)
    service.record_flip('A')
    assert service.get_challenge(cid)['challenger_flips_done'] == 0
    with pytest.raises(FlipOffError):
        service.accept_challenge(cid, 'A', b)
    with pytest.raises(FlipOffError):
        service.accept_challenge(cid, 'B', a)
    service.accept_challenge(cid, 'B', b)
    assert stickers.collection('B')[0]['locked_challenge_id'] == cid
    service.record_flip('A')
    assert service.get_challenge(cid)['challenger_flips_done'] == 1


def test_failed_stake_rolls_back_challenge(wager):
    service, _, _, b = wager
    with pytest.raises(FlipOffError):
        service.create_challenge('A', 'B', 10, b)
    assert service.get_active_challenge('A') is None


def test_yield_awards_both_exactly_once(wager):
    service, stickers, a, b = wager
    cid = service.create_challenge('A', 'B', 10, a)
    service.accept_challenge(cid, 'B', b)
    service.yield_challenge('B')
    service._calculate_winner(cid)
    assert {s['id'] for s in stickers.collection('A')} == {a, b}
    assert stickers.collection('B') == []
    assert service.get_challenge(cid)['wager_status'] == 'settled'


@pytest.mark.parametrize('action', ['cancel', 'yield', 'expire', 'draw'])
def test_returns_original_stakes(wager, action):
    service, stickers, a, b = wager
    cid = service.create_challenge('A', 'B', 10, a)
    if action in ('expire', 'draw'):
        service.accept_challenge(cid, 'B', b)
    if action == 'cancel':
        service.cancel_challenge(cid, 'B')
    elif action == 'yield':
        service.yield_challenge('A')
    elif action == 'expire':
        with sqlite3.connect(stickers.db_path) as conn:
            conn.execute("UPDATE flip_off_challenges SET created_at='2000-01-01' WHERE id=?", (cid,))
        service.expire_stale_challenges()
    else:
        for _ in range(10):
            service.record_flip('A')
            service.record_flip('B')
    assert stickers.collection('A')[0]['id'] == a
    assert stickers.collection('B')[0]['id'] == b
    assert all(s['locked_challenge_id'] is None for c in ('A','B') for s in stickers.collection(c))
    assert service.get_challenge(cid)['wager_status'] == 'returned'


def test_settlement_triggers_evolution(wager):
    service, stickers, a, b = wager
    cid = service.create_challenge('A', 'B', 10, a)
    service.accept_challenge(cid, 'B', b)
    stickers.award_flip('A', 'a', 2)
    service.yield_challenge('B')
    assert [s['level'] for s in stickers.collection('A')] == [2]


def test_concurrent_challenge_creation_cannot_double_stake(wager):
    service, stickers, a, _ = wager
    def create(target):
        try:
            return service.create_challenge('A', target, 10, a)
        except FlipOffError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, ['B', 'C']))
    assert sum(result is not None for result in results) == 1
    assert len(service.get_all_active_challenges()) == 1


def test_concurrent_yield_and_expiry_never_duplicate_or_strand_stakes(wager):
    service, stickers, a, b = wager
    cid = service.create_challenge('A', 'B', 10, a)
    service.accept_challenge(cid, 'B', b)
    with sqlite3.connect(stickers.db_path) as conn:
        conn.execute("UPDATE flip_off_challenges SET created_at='2000-01-01' WHERE id=?", (cid,))
    def yield_match():
        try:
            service.yield_challenge('B')
        except FlipOffError:
            pass  # Expiry acquired the write lock first.
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(yield_match), pool.submit(service.expire_stale_challenges)]
        for future in futures:
            future.result()
    copies = stickers.collection('A') + stickers.collection('B')
    assert {s['id'] for s in copies} == {a, b}
    assert len(copies) == 2
    assert all(s['locked_challenge_id'] is None for s in copies)
    assert service.get_challenge(cid)['wager_status'] in ('settled', 'returned')


def test_borrowed_progress_transaction_rolls_back_terminal_settlement(wager):
    service, stickers, a, b = wager
    cid = service.create_challenge('A', 'B', 10, a)
    service.accept_challenge(cid, 'B', b)
    for _ in range(10):
        service.record_flip('A')
    for _ in range(9):
        service.record_flip('B')
    with pytest.raises(RuntimeError), sqlite3.connect(stickers.db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        service.record_flip('B', conn=conn)
        assert conn.execute('SELECT status FROM flip_off_challenges WHERE id=?', (cid,)).fetchone()[0] == 'complete'
        raise RuntimeError('Interrupted scan transaction')
    challenge = service.get_challenge(cid)
    assert challenge['status'] == 'in_progress'
    assert challenge['challenged_flips_done'] == 9
    assert challenge['wager_status'] == 'accepted'
    assert all(s['locked_challenge_id'] == cid for c in ('A','B') for s in stickers.collection(c))
    service.record_flip('B')
    assert service.get_challenge(cid)['wager_status'] == 'returned'


def test_terminal_evolution_events_persist_after_consumed_stakes(wager):
    service, stickers, a, b = wager
    cid = service.create_challenge('A', 'B', 10, a)
    service.accept_challenge(cid, 'B', b)
    stickers.award_flip('A', 'a', 2)
    service.yield_challenge('B')
    challenge = service.get_challenge(cid)
    assert len(challenge['wager_evolutions']) == 1
    assert challenge['wager_evolutions'][0]['sticker']['level'] == 2
    assert len(challenge['stakes']) == 2
    assert service.get_challenge(cid)['wager_evolutions'] == challenge['wager_evolutions']


def test_expired_latest_opt_in_shows_returned_state(wager):
    service, _, a, _ = wager
    cid = service.create_challenge('A','B',10,a)
    service.cancel_challenge(cid,'A')
    assert service.get_latest_challenge('A') is None
    assert service.get_latest_challenge('A', include_expired=True)['wager_status'] == 'returned'
