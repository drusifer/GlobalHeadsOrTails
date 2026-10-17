"""Coin-owned collectibles and transactional evolution."""
import json
import math
import random
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional
from uuid import uuid4


class StickerService:
    """Persist drop decisions so retries never reroll a validated tap."""

    def __init__(self, db_path: str, rng=None, catalog_path: Optional[str] = None, registry_path: Optional[str] = None):
        self.db_path = Path(db_path)
        self.rng = rng or random.SystemRandom()
        self._catalog = None
        self.catalog_path = Path(catalog_path) if catalog_path else Path(__file__).with_name('sticker_catalog.json')
        self.registry_path = Path(registry_path) if registry_path else (None if catalog_path else Path(__file__).with_name('sticker_packs.json'))
        self._families = {}
        self._forms = {}
        self._pack_families = {}
        self._selections = {}
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
        """Cache immutable catalogs and indexes without per-request network or image scans."""
        if self._catalog is None:
            self._load_catalogs()
        return self._catalog

    def _load_catalogs(self) -> None:
        if self.registry_path is None:
            data = json.loads(self.catalog_path.read_text())
            pack_id = data.get('id', 'twelve-clans')
            registry = {'active_pack_id': pack_id, 'packs': [{'id': pack_id, 'selection': data.get('selection', {'type': 'legacy_tiers'})}]}
            sources = [(registry['packs'][0], data)]
        else:
            registry = json.loads(self.registry_path.read_text())
            sources = [(entry, json.loads((self.registry_path.parent / entry['catalog']).read_text())) for entry in registry['packs']]
        if not sources:
            raise ValueError('Sticker registry must contain at least one pack.')
        families, forms, pack_families, selections, headers = {}, {}, {}, {}, []
        catalogs = {}
        for entry, data in sources:
            pack_id = entry['id']
            if not isinstance(pack_id, str) or not pack_id or pack_id in catalogs:
                raise ValueError('Sticker pack IDs must be unique nonempty strings.')
            if data.get('id', pack_id) != pack_id:
                raise ValueError('Catalog ID must match its registry entry.')
            selection = entry.get('selection', data.get('selection', {'type': 'legacy_tiers'}))
            weights = selection.get('weights', {})
            if selection.get('type') == 'player_weights':
                if set(weights) != {'common', 'uncommon', 'rare', 'legendary'} or any(
                    isinstance(w, bool) or not isinstance(w, (int, float)) or not math.isfinite(w) or w <= 0 for w in weights.values()
                ):
                    raise ValueError('Player rarity weights must be finite positive numbers for all four tiers.')
            elif selection.get('type') != 'legacy_tiers':
                raise ValueError('Unknown sticker selection policy.')
            selected = []
            counts = dict.fromkeys(('common', 'uncommon', 'rare', 'legendary'), 0)
            for source in data['families']:
                identity = source['id']
                if not isinstance(identity, str) or not identity or identity in families:
                    raise ValueError('Sticker family IDs must be globally unique nonempty strings.')
                if source.get('pack_id', pack_id) != pack_id:
                    raise ValueError('Family pack ID must match its catalog.')
                rarity = source['rarity'].lower()
                if rarity not in counts:
                    raise ValueError('Unknown sticker rarity.')
                levels = [form['level'] for form in source['forms']]
                if len(levels) != 3 or any(type(level) is not int for level in levels) or set(levels) != {1, 2, 3}:
                    raise ValueError('Each sticker family must have exactly levels 1, 2 and 3.')
                family = {**source, 'pack_id': pack_id}
                families[identity] = family
                forms.update({(identity, form['level']): form for form in family['forms']})
                selected.append(family)
                counts[rarity] += 1
            if not selected or (selection['type'] == 'legacy_tiers' and not all(counts.values())):
                raise ValueError('Sticker pack must contain families for its draw policy.')
            total_weight = sum(counts[rarity] * weights[rarity] for rarity in counts) if weights else None
            header = {key: data[key] for key in ('pack_name', 'narrative', 'snapshot', 'rarity_policy') if key in data}
            header.update({'id': pack_id, 'pack_name': header.get('pack_name', pack_id),
                           'total_families': len(selected), 'total_forms': len(selected)*3,
                           'rarity_counts': counts, 'selection': selection})
            if total_weight is not None:
                header.update({'total_player_weight': total_weight,
                               'tier_probabilities': {rarity: counts[rarity]*weights[rarity]/total_weight for rarity in counts}})
            pack_families[pack_id], selections[pack_id], catalogs[pack_id] = selected, selection, data
            headers.append(header)
        active = registry['active_pack_id']
        if active not in catalogs:
            raise ValueError('Active sticker pack must exist in registry.')
        # Publish only after all packs validate, so a failed load cannot leave partial indexes.
        self._families, self._forms = families, forms
        self._pack_families, self._selections = pack_families, selections
        self._catalog = {**catalogs[active], 'active_pack_id': active, 'packs': headers, 'families': list(families.values())}

    @staticmethod
    def _public_family(family: dict) -> dict:
        return {key: value for key, value in family.items() if key not in ('forms', 'art_prompt')}

    @staticmethod
    def _public_form(family: dict, form: dict) -> dict:
        public = {key: value for key, value in form.items() if key != 'art_prompt'}
        public['image'] = form.get('image') or f"/static/stickers/{family['id']}-{form['level']}.webp"
        return public

    def public_catalog(self, collection: list) -> dict:
        """Send compact season headers and metadata only for owned families."""
        catalog = self.catalog
        owned_ids = {sticker['family_id'] for sticker in collection}
        headers = catalog['packs']
        active = next(header for header in headers if header['id'] == catalog['active_pack_id'])
        return {**active, 'active_pack_id': catalog['active_pack_id'], 'packs': headers,
                'families': [{**self._public_family(self._families[identity]),
                              'forms': [self._public_form(self._families[identity], form) for form in self._families[identity]['forms']]}
                             for identity in sorted(owned_ids)]}

    def decorate(self, sticker: dict) -> dict:
        """Attach catalog details to an owned sticker or historical wager snapshot."""
        self.catalog  # Initialize immutable indexes once.
        family = self._families[sticker['family_id']]
        form = self._forms[(sticker['family_id'], sticker['level'])]
        return {**sticker, 'pack_id': family['pack_id'], 'family': self._public_family(family),
                'form': self._public_form(family, form), 'rarity': family['rarity']}

    def _draw_family(self) -> dict:
        active = self.catalog['active_pack_id']
        selection = self._selections[active]
        families = self._pack_families[active]
        if selection['type'] == 'player_weights':
            weights = selection['weights']
            total = sum(weights[family['rarity'].lower()] for family in families)
            roll = self.rng.random() * total
            for family in families:
                roll -= weights[family['rarity'].lower()]
                if roll < 0:
                    return family
            return families[-1]  # Floating-point rounding at the upper boundary.
        roll = self.rng.random() * 100
        rarity = 'legendary'
        for name, edge in [('common', 60), ('uncommon', 85), ('rare', 97)]:
            if roll < edge:
                rarity = name
                break
        return self.rng.choice([family for family in families if family['rarity'].lower() == rarity])

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

    def award_flip(self, coin_name: str, uid: str, counter: int, conn: Optional[sqlite3.Connection] = None, odds: Optional[dict] = None) -> dict:
        """Award once, borrowing a scan transaction when supplied by the caller."""
        if conn is not None:
            return self._award_flip(conn, coin_name, uid, counter, odds)
        with self._get_conn() as owned_conn:
            owned_conn.execute('BEGIN IMMEDIATE')
            return self._award_flip(owned_conn, coin_name, uid, counter, odds)

    def _award_flip(self, conn: sqlite3.Connection, coin_name: str, uid: str, counter: int, odds: Optional[dict] = None) -> dict:
        prior = conn.execute('SELECT coin_name,result FROM sticker_awards WHERE uid=? AND counter=?', (uid, counter)).fetchone()
        if prior:
            if prior[0] != coin_name:
                raise ValueError('Tap identity already belongs to another coin.')
            return json.loads(prior[1])
        drop = None
        if self.rng.random() < (odds['drop_chance'] if odds is not None else .5):
            family = self._draw_family()
            drop = self.decorate(self._insert(conn, coin_name, family['id'], 1))
        result = {'drop': drop, 'evolutions': self.evolve(conn, coin_name)}
        if odds is not None:
            result['odds'] = odds
        conn.execute('INSERT INTO sticker_awards VALUES (?,?,?,?)', (uid, counter, coin_name, json.dumps(result)))
        return result
