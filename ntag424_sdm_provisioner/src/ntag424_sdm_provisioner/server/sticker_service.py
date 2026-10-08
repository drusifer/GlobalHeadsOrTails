"""Coin-owned collectibles and transactional evolution."""
import json
import random
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional
from uuid import uuid4


class StickerService:
    """Persist drop decisions so retries never reroll a validated tap."""

    def __init__(self, db_path: str, rng=None, catalog_path: Optional[str] = None):
        self.db_path = Path(db_path)
        self.rng = rng or random.SystemRandom()
        self._catalog = None
        self.catalog_path = Path(catalog_path) if catalog_path else Path(__file__).with_name('sticker_catalog.json')
        with self._get_conn() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS stickers (
                    id TEXT PRIMARY KEY, coin_name TEXT NOT NULL, family_id TEXT NOT NULL,
                    level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 3), locked_challenge_id INTEGER
                );
                CREATE INDEX IF NOT EXISTS stickers_owner ON stickers(coin_name);
                CREATE TABLE IF NOT EXISTS sticker_awards (
                    uid TEXT NOT NULL, counter INTEGER NOT NULL, coin_name TEXT NOT NULL,
                    result TEXT NOT NULL, PRIMARY KEY(uid, counter)
                );
            ''')

    @contextmanager
    def _get_conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=30)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @property
    def catalog(self) -> dict:
        """Read immutable pack metadata, allowing deployment before artwork exists."""
        if self._catalog is None:
            self._catalog = json.loads(self.catalog_path.read_text())
        return self._catalog

    def decorate(self, sticker: dict) -> dict:
        """Attach catalog details to an owned sticker or historical wager snapshot."""
        family = next(f for f in self.catalog['families'] if f['id'] == sticker['family_id'])
        form = next(f for f in family['forms'] if f['level'] == sticker['level'])
        public_family = {key: family.get(key, family['id'] if key == 'name' else '') for key in ('id', 'name', 'rarity')}
        public_form = {key: form.get(key, '') for key in ('level', 'name', 'quote')}
        return {**sticker, 'family': public_family, 'form': public_form, 'rarity': family['rarity']}

    def collection(self, coin_name: str) -> list:
        """Return individual copies, including locked stakes."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('SELECT * FROM stickers WHERE coin_name = ? ORDER BY family_id, level, id', (coin_name,)).fetchall()
        return [self.decorate(dict(row)) for row in rows]

    def _insert(self, conn: sqlite3.Connection, coin: str, family: str, level: int) -> dict:
        sticker = {'id': uuid4().hex, 'coin_name': coin, 'family_id': family, 'level': level, 'locked_challenge_id': None}
        conn.execute('INSERT INTO stickers VALUES (:id,:coin_name,:family_id,:level,:locked_challenge_id)', sticker)
        return sticker

    def evolve(self, conn: sqlite3.Connection, coin: str) -> list:
        """Combine unlocked triples under the caller's write transaction."""
        events = []
        for level in (1, 2):
            groups = conn.execute('SELECT family_id FROM stickers WHERE coin_name=? AND level=? AND locked_challenge_id IS NULL GROUP BY family_id HAVING COUNT(*)>=3', (coin, level)).fetchall()
            for (family,) in groups:
                ids = [r[0] for r in conn.execute('SELECT id FROM stickers WHERE coin_name=? AND family_id=? AND level=? AND locked_challenge_id IS NULL ORDER BY id', (coin, family, level))]
                for start in range(0, len(ids) - 2, 3):
                    consumed = ids[start:start + 3]
                    conn.executemany('DELETE FROM stickers WHERE id=?', [(sid,) for sid in consumed])
                    result = self._insert(conn, coin, family, level + 1)
                    events.append({'consumed_ids': consumed, 'sticker': self.decorate(result)})
        return events

    def award_flip(self, coin_name: str, uid: str, counter: int, conn: Optional[sqlite3.Connection] = None) -> dict:
        """Award once, borrowing a scan transaction when supplied by the caller."""
        if conn is not None:
            return self._award_flip(conn, coin_name, uid, counter)
        with self._get_conn() as owned_conn:
            owned_conn.execute('BEGIN IMMEDIATE')
            return self._award_flip(owned_conn, coin_name, uid, counter)

    def _award_flip(self, conn: sqlite3.Connection, coin_name: str, uid: str, counter: int) -> dict:
        prior = conn.execute('SELECT coin_name,result FROM sticker_awards WHERE uid=? AND counter=?', (uid, counter)).fetchone()
        if prior:
            if prior[0] != coin_name:
                raise ValueError('Tap identity already belongs to another coin.')
            return json.loads(prior[1])
        drop = None
        if self.rng.random() < 0.5:
            roll = self.rng.random() * 100
            rarity = 'Legendary'
            for name, edge in [('Common', 60), ('Uncommon', 85), ('Rare', 97)]:
                if roll < edge:
                    rarity = name
                    break
            families = [f for f in self.catalog['families'] if f['rarity'].lower() == rarity.lower()]
            family = self.rng.choice(families)
            drop = self.decorate(self._insert(conn, coin_name, family['id'], 1))
        result = {'drop': drop, 'evolutions': self.evolve(conn, coin_name)}
        conn.execute('INSERT INTO sticker_awards VALUES (?,?,?,?)', (uid, counter, coin_name, json.dumps(result)))
        return result
