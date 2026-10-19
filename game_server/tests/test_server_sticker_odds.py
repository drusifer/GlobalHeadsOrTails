"""Exact-count weighting and transaction-level award history regressions."""
import math
import json
import sqlite3
from types import SimpleNamespace

import pytest

from game_server.sticker_odds import calculate_sticker_odds, coin_sticker_odds
from test_server_sticker_api import api, signed, UID_A, UID_B
from test_server_stickers import FixedRandom
from game_server.csv_key_manager import Outcome


@pytest.mark.parametrize('heads,tails,chance', [(0,0,.05),(1,0,.05),(0,99,.05),(1,1,.5),(50,50,.5),(100,0,.05)])
def test_odds_bounds_and_warmup(heads, tails, chance):
    odds = calculate_sticker_odds(heads, tails)
    assert odds['drop_chance'] == pytest.approx(chance)
    assert odds['warmup'] == (heads+tails < 100)
    assert (odds['p_value'] is None) == odds['warmup']


def test_both_entropy_and_p_value_lower_odds():
    warm = calculate_sticker_odds(6,4)
    assert .05 < warm['drop_chance'] < .5
    mature = calculate_sticker_odds(55,45)
    p = math.erfc(10 / math.sqrt(200))
    assert mature['p_value'] == pytest.approx(p)
    assert mature['drop_chance'] == pytest.approx(.5 * max(.1, mature['entropy']/8*p))
    assert .05 < mature['drop_chance'] < warm['drop_chance']


def test_exact_counts_do_not_pad_tail_bits():
    odds = calculate_sticker_odds(51,50)
    assert odds['p_value'] == pytest.approx(math.erfc(1/math.sqrt(202)))
    assert odds['entropy'] > 7.99


def test_per_coin_scores_pool_uids_and_exclude_tests(api):
    manager = api.game_manager
    manager.update_state(UID_A,1,'heads',coin_name='A')
    manager.update_state(UID_B,1,'tails',coin_name='A')
    manager.update_state('other',1,'heads',coin_name='B')
    manager.update_state(UID_A,2,'heads',coin_name='A',is_test=True)
    with sqlite3.connect(api.sticker_service.db_path) as conn:
        real = coin_sticker_odds(conn,'A')
        test = coin_sticker_odds(conn,'A',include_test=True)
    assert real['flip_count'] == 2 and real['drop_chance'] == .5
    assert test['flip_count'] == 3 and test['drop_chance'] < .5


def test_award_uses_current_uncommitted_flip_and_stores_odds(api):
    api.sticker_service.rng = FixedRandom(.2)
    with api.test_client() as client:
        first = client.get('/api/flip',query_string=signed()).json['sticker_award']
        assert first['odds']['drop_chance'] == .05 and first['drop'] is None
        api.key_manager.outcomes = {UID_A: Outcome.TAILS}
        second = client.get('/api/flip',query_string=signed(counter=2)).json['sticker_award']
        assert second['odds']['flip_count'] == 2
        assert second['odds']['drop_chance'] == .5 and second['drop'] is not None
    with sqlite3.connect(api.sticker_service.db_path) as conn:
        prior = api.sticker_service.award_flip('A',UID_A,1,conn=conn,odds=calculate_sticker_odds(50,50))
    assert prior == first


def test_test_retry_does_not_change_score_history(api):
    params = {**signed(), 'cmac':'dummy','drew_test_outcome':'heads'}
    with api.test_client() as client:
        first = client.get('/api/flip',query_string=params).json['sticker_award']
        repeat = client.get('/api/flip',query_string=params).json['sticker_award']
        assert first == repeat and first['odds']['drop_chance'] == .05
        real = client.get('/api/stickers?coin_name=A').json['odds']
        test = client.get('/api/stickers?coin_name=A&drew_test_outcome=heads').json['odds']
        assert real['flip_count'] == 0 and test['flip_count'] == 1
    with sqlite3.connect(api.sticker_service.db_path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM scan_logs').fetchone()[0] == 1


def test_monobit_activates_at_100_actual_observations():
    before = calculate_sticker_odds(59, 40)
    after = calculate_sticker_odds(60, 40)
    assert before['warmup'] and before['p_value'] is None
    assert before['drop_chance'] == pytest.approx(.5 * before['entropy'] / 8)
    assert not after['warmup']
    assert after['p_value'] == pytest.approx(math.erfc(20 / math.sqrt(200)))
    assert after['drop_chance'] < before['drop_chance']


def test_mature_balance_improves_odds_symmetrically():
    balanced = calculate_sticker_odds(50, 50)
    slight = calculate_sticker_odds(55, 45)
    biased = calculate_sticker_odds(60, 40)
    assert biased['drop_chance'] == .05
    assert biased['drop_chance'] < slight['drop_chance'] < balanced['drop_chance'] == .5
    assert calculate_sticker_odds(45, 55)['drop_chance'] == slight['drop_chance']


def test_signed_faces_share_coin_history_and_sticker_ownership(api):
    class TwoFaces:
        def get_tag_keys(self, uid):
            return SimpleNamespace(coin_name='A', outcome=Outcome.HEADS if uid.uid == UID_A else Outcome.TAILS)

        def validate_sdm_url(self, uid, counter, cmac):
            return {'valid': cmac == f'signed-{uid.uid}-{counter}'}

    api.key_manager = TwoFaces()
    api.sticker_service.rng = FixedRandom(.2)
    with api.test_client() as client:
        first = client.get('/api/flip', query_string=signed(UID_A)).json['sticker_award']
        second = client.get('/api/flip', query_string=signed(UID_B)).json['sticker_award']
        inventory = client.get('/api/stickers?coin_name=A').json
    assert first['drop'] is None and first['odds']['flip_count'] == 1
    assert second['drop']['coin_name'] == 'A'
    assert second['odds']['heads'] == second['odds']['tails'] == 1
    assert inventory['odds']['flip_count'] == 2
    assert {copy['id'] for copy in inventory['stickers']} == {second['drop']['id']}


def test_client_cannot_override_server_award_odds(api):
    api.sticker_service.rng = FixedRandom(.2)
    forged = {**signed(), 'drop_chance': '1', 'entropy': '8', 'p_value': '1', 'heads': '50', 'tails': '50'}
    with api.test_client() as client:
        result = client.get('/api/flip', query_string=forged)
    assert result.status_code == 200
    award = result.json['sticker_award']
    assert award['odds']['drop_chance'] == .05 and award['drop'] is None
    assert award['odds']['heads'] == 1 and award['odds']['tails'] == 0


def test_legacy_award_replay_preserves_original_result_without_odds(api):
    legacy = {'drop': None, 'evolutions': []}
    with sqlite3.connect(api.sticker_service.db_path) as conn:
        conn.execute('INSERT INTO sticker_awards VALUES (?,?,?,?)',
                     ('test:' + UID_A, 1, 'A', json.dumps(legacy)))
    with api.test_client() as client:
        response = client.get('/api/flip', query_string={**signed(), 'cmac': 'dummy', 'drew_test_outcome': 'heads'})
    assert response.status_code == 200
    assert response.json['sticker_award'] == legacy
    with sqlite3.connect(api.sticker_service.db_path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM scan_logs').fetchone()[0] == 0
