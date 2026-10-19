"""Drop retries, rarity boundaries and locked evolution invariants."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from game_server.sticker_service import StickerService


class FixedRandom:
    def __init__(self, drop=0, rarity=0):
        self.values = (drop, rarity)
        self.index = 0

    def random(self):
        value = self.values[self.index % 2]
        self.index += 1
        return value

    def choice(self, values):
        return values[0]


@pytest.fixture
def stickers(tmp_path):
    catalog = {'families': [{'id': rarity.lower(), 'rarity': rarity, 'forms': [{'level': level, 'name': f'{rarity}{level}'} for level in (1, 2, 3)]} for rarity in ('Common', 'Uncommon', 'Rare', 'Legendary')]}
    path = tmp_path / 'catalog.json'
    path.write_text(json.dumps(catalog))
    return StickerService(str(tmp_path / 'game.db'), rng=FixedRandom(), catalog_path=str(path))


def test_award_retry_cannot_reroll_or_duplicate(stickers):
    first = stickers.award_flip('A', 'uid', 1)
    assert stickers.award_flip('A', 'uid', 1) == first
    assert len(stickers.collection('A')) == 1
    with pytest.raises(ValueError):
        stickers.award_flip('B', 'uid', 1)


def test_no_drop_is_persisted(stickers):
    stickers.rng = FixedRandom(0.5)
    assert stickers.award_flip('A', 'uid', 1)['drop'] is None
    stickers.rng = FixedRandom()
    assert stickers.award_flip('A', 'uid', 1)['drop'] is None
    assert stickers.collection('A') == []


@pytest.mark.parametrize('roll,rarity', [(0, 'Common'), (.6, 'Uncommon'), (.85, 'Rare'), (.97, 'Legendary')])
def test_rarity_boundaries(stickers, roll, rarity):
    stickers.rng = FixedRandom(0, roll)
    drop = stickers.award_flip('A', 'uid', 1)['drop']
    assert drop['rarity'] == rarity
    assert drop['level'] == 1


def test_nine_copies_cascade_to_level_three_and_stop(stickers):
    for counter in range(27):
        stickers.award_flip('A', 'uid', counter)
    owned = stickers.collection('A')
    assert len(owned) == 3
    assert {s['level'] for s in owned} == {3}
    assert {s['rarity'] for s in owned} == {'Common'}


def test_locked_copy_does_not_evolve(stickers):
    first = stickers.award_flip('A', 'uid', 0)['drop']
    with sqlite3.connect(stickers.db_path) as conn:
        conn.execute('UPDATE stickers SET locked_challenge_id=1 WHERE id=?', (first['id'],))
    for counter in (1, 2):
        stickers.award_flip('A', 'uid', counter)
    assert len(stickers.collection('A')) == 3


def test_concurrent_retry_has_one_drop(stickers):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: stickers.award_flip('A', 'uid', 1), range(8)))
    assert all(r == results[0] for r in results)
    assert len(stickers.collection('A')) == 1


def test_borrowed_transaction_rolls_back_drop_and_decision(stickers):
    with pytest.raises(RuntimeError), sqlite3.connect(stickers.db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        stickers.award_flip('A', 'uid', 1, conn=conn)
        raise RuntimeError('Scan persistence failed')
    assert stickers.collection('A') == []
    with sqlite3.connect(stickers.db_path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM sticker_awards').fetchone()[0] == 0
    assert stickers.award_flip('A', 'uid', 1)['drop'] is not None
