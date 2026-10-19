import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional

from game_server.crypto.crypto_primitives import calculate_entropy

from game_server.sticker_service import StickerService

log = logging.getLogger(__name__)

VALID_FLIP_COUNTS = (10, 25, 50, 100)


class FlipOffError(ValueError):
    """Raised for invalid challenge operations."""


class FlipOffService:
    """Manages Flip Off challenge lifecycle.

    Shares the same SQLite database as SqliteGameStateManager so it can
    query scan_logs for post-challenge flip entropy calculations.
    """

    def __init__(self, db_path: str, sticker_service=None):
        self.db_path = Path(db_path)
        self.stickers = sticker_service or StickerService(db_path)
        self._init_db()

    @contextmanager
    def _get_conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=30)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS flip_off_challenges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    baseline_scan_id INTEGER NOT NULL DEFAULT 0,
                    challenger_coin_name TEXT NOT NULL,
                    challenged_coin_name TEXT NOT NULL,
                    flip_count INTEGER NOT NULL CHECK(flip_count IN (10, 25, 50, 100)),
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending', 'in_progress', 'complete', 'expired')),
                    challenger_flips_done INTEGER NOT NULL DEFAULT 0,
                    challenged_flips_done INTEGER NOT NULL DEFAULT 0,
                    challenger_entropy REAL,
                    challenged_entropy REAL,
                    winner_coin_name TEXT,
                    completed_at DATETIME,
                    end_condition TEXT CHECK(end_condition IN ('win','draw','yield','expired'))
                )
            """)
            conn.execute("""CREATE TABLE IF NOT EXISTS flip_off_wagers (
                challenge_id INTEGER PRIMARY KEY, status TEXT NOT NULL,
                challenger_stake TEXT NOT NULL, challenged_stake TEXT
            )""")
            wager_columns = {row[1] for row in conn.execute('PRAGMA table_info(flip_off_wagers)')}
            if 'evolution_events' not in wager_columns:
                conn.execute("ALTER TABLE flip_off_wagers ADD COLUMN evolution_events TEXT NOT NULL DEFAULT '[]'")
            conn.commit()
            try:
                conn.execute(
                    "ALTER TABLE flip_off_challenges ADD COLUMN end_condition TEXT"
                    " CHECK(end_condition IN ('win','draw','yield','expired'))"
                )
                conn.commit()
            except Exception:
                pass  # column already exists

    def create_challenge(
        self, challenger_coin: str, challenged_coin: str, flip_count: int, sticker_id: Optional[str] = None
    ) -> int:
        """Creates a new Flip Off challenge.

        Args:
            challenger_coin: coin_name of the initiating coin.
            challenged_coin: coin_name of the target coin.
            flip_count: number of flips each coin must complete (10/25/50/100).

        Returns:
            The new challenge ID.

        Raises:
            FlipOffError: if inputs are invalid or either coin has an active challenge.
        """
        if flip_count not in VALID_FLIP_COUNTS:
            raise FlipOffError(f"flip_count must be one of {VALID_FLIP_COUNTS}")
        if challenger_coin == challenged_coin:
            raise FlipOffError("A coin cannot challenge itself.")

        with self._get_conn() as conn:
            conn.execute('BEGIN IMMEDIATE')
            # Check + insert in one connection so the constraint is atomic.
            # Multiple concurrent flip-offs are allowed; each coin may only
            # appear in one active challenge at a time (either role).
            active_sql = """
                SELECT id FROM flip_off_challenges
                WHERE status IN ('pending', 'in_progress')
                  AND (challenger_coin_name = ? OR challenged_coin_name = ?)
                LIMIT 1"""
            if conn.execute(active_sql, (challenger_coin, challenger_coin)).fetchone():
                raise FlipOffError(f"{challenger_coin} already has an active challenge.")
            if conn.execute(active_sql, (challenged_coin, challenged_coin)).fetchone():
                raise FlipOffError(f"{challenged_coin} already has an active challenge.")

            # Capture scan baseline so only flips after this point count
            result = conn.execute("SELECT COALESCE(MAX(id), 0) FROM scan_logs").fetchone()
            baseline_scan_id = result[0] if result else 0

            cursor = conn.execute(
                """INSERT INTO flip_off_challenges
                   (challenger_coin_name, challenged_coin_name, flip_count, baseline_scan_id)
                   VALUES (?, ?, ?, ?)""",
                (challenger_coin, challenged_coin, flip_count, baseline_scan_id),
            )
            challenge_id = cursor.lastrowid
            if sticker_id:
                stake = self._lock(conn, sticker_id, challenger_coin, challenge_id)
                conn.execute("INSERT INTO flip_off_wagers (challenge_id,status,challenger_stake,challenged_stake) VALUES (?, 'awaiting_acceptance', ?, NULL)", (challenge_id, json.dumps(stake)))
            conn.commit()

        log.info(
            "[FLIP OFF] Challenge %d created: %s vs %s (%d flips)",
            challenge_id, challenger_coin, challenged_coin, flip_count,
        )
        return challenge_id

    def get_active_challenge(self, coin_name: str) -> Optional[dict]:
        """Returns the active (pending/in_progress) challenge for a coin, or None."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """SELECT id, created_at, baseline_scan_id, challenger_coin_name, challenged_coin_name,
                          flip_count, status, challenger_flips_done, challenged_flips_done,
                          challenger_entropy, challenged_entropy, winner_coin_name, completed_at, end_condition
                   FROM flip_off_challenges
                   WHERE status IN ('pending', 'in_progress')
                     AND (challenger_coin_name = ? OR challenged_coin_name = ?)
                   ORDER BY id DESC LIMIT 1""",
                (coin_name, coin_name),
            )
            row = cursor.fetchone()
        return self._row_to_dict(row) if row else None

    def get_challenge(self, challenge_id: int) -> Optional[dict]:
        """Returns a challenge record by ID, or None."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """SELECT id, created_at, baseline_scan_id, challenger_coin_name, challenged_coin_name,
                          flip_count, status, challenger_flips_done, challenged_flips_done,
                          challenger_entropy, challenged_entropy, winner_coin_name, completed_at, end_condition
                   FROM flip_off_challenges WHERE id = ?""",
                (challenge_id,),
            )
            row = cursor.fetchone()
        return self._row_to_dict(row) if row else None

    def record_flip(self, coin_name: str, conn: Optional[sqlite3.Connection] = None) -> None:
        """Count progress in the validated scan transaction when supplied."""
        if conn is not None:
            self._record_flip(conn, coin_name)
            return
        with self._get_conn() as owned_conn:
            owned_conn.execute('BEGIN IMMEDIATE')
            self._record_flip(owned_conn, coin_name)

    def _record_flip(self, conn: sqlite3.Connection, coin_name: str) -> None:
        row = conn.execute("SELECT id,challenger_coin_name,challenger_flips_done,challenged_flips_done,flip_count FROM flip_off_challenges WHERE status IN ('pending','in_progress') AND (challenger_coin_name=? OR challenged_coin_name=?)", (coin_name, coin_name)).fetchone()
        if not row:
            return
        wager = conn.execute('SELECT status FROM flip_off_wagers WHERE challenge_id=?', (row[0],)).fetchone()
        if wager and wager[0] != 'accepted':
            return
        col = 'challenger_flips_done' if row[1] == coin_name else 'challenged_flips_done'
        conn.execute(f"UPDATE flip_off_challenges SET {col}=MIN({col}+1,flip_count),status='in_progress' WHERE id=?", (row[0],))  # noqa: S608
        progress = conn.execute('SELECT challenger_flips_done,challenged_flips_done,flip_count FROM flip_off_challenges WHERE id=?', (row[0],)).fetchone()
        if progress[0] >= progress[2] and progress[1] >= progress[2]:
            self._finish(conn, row[0])

    def _calculate_winner(self, challenge_id: int) -> None:
        """Finalize once, atomically with stake ownership."""
        with self._get_conn() as conn:
            conn.execute('BEGIN IMMEDIATE')
            self._finish(conn, challenge_id)

    def _finish(self, conn: sqlite3.Connection, challenge_id: int, yielding: Optional[str] = None) -> None:
        row = conn.execute("SELECT challenger_coin_name,challenged_coin_name,baseline_scan_id,flip_count,status FROM flip_off_challenges WHERE id=?", (challenge_id,)).fetchone()
        if not row or row[4] not in ('pending', 'in_progress'):
            return
        a, b, baseline, n, _ = row
        ea = round(self._coin_challenge_entropy(a, baseline, n, conn), 4)
        eb = round(self._coin_challenge_entropy(b, baseline, n, conn), 4)
        winner = (b if yielding == a else a) if yielding else (a if ea > eb else b if eb > ea else 'DRAW')
        end = 'yield' if yielding else 'draw' if winner == 'DRAW' else 'win'
        conn.execute("UPDATE flip_off_challenges SET status='complete',challenger_entropy=?,challenged_entropy=?,winner_coin_name=?,completed_at=CURRENT_TIMESTAMP,end_condition=? WHERE id=?", (ea, eb, winner, end, challenge_id))
        self._settle(conn, challenge_id, None if winner == 'DRAW' else winner)

    def _coin_challenge_entropy(self, coin_name: str, baseline_scan_id: int, n: int, conn: Optional[sqlite3.Connection] = None) -> float:
        """Read the same scan snapshot used by settlement, including the final tap."""
        if conn is None:
            with self._get_conn() as owned_conn:
                return self._coin_challenge_entropy(coin_name, baseline_scan_id, n, owned_conn)
        rows = conn.execute("""SELECT LOWER(outcome) FROM scan_logs
            WHERE coin_name=? AND id>? AND is_test IS FALSE
              AND LOWER(outcome) IN ('heads','tails') ORDER BY id ASC LIMIT ?""",
            (coin_name, baseline_scan_id, n)).fetchall()
        if not rows:
            return 0.0
        bits = ''.join('1' if row[0] == 'heads' else '0' for row in rows)
        bits += '0' * ((-len(bits)) % 8)
        return calculate_entropy(int(bits, 2).to_bytes(len(bits) // 8, byteorder='big'))

    def get_latest_challenge(self, coin_name: str, include_expired: bool = False) -> Optional[dict]:
        """Returns the most recent non-expired challenge for a coin (any status except expired)."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """SELECT id, created_at, baseline_scan_id, challenger_coin_name, challenged_coin_name,
                          flip_count, status, challenger_flips_done, challenged_flips_done,
                          challenger_entropy, challenged_entropy, winner_coin_name, completed_at, end_condition
                   FROM flip_off_challenges
                   WHERE (status != 'expired' OR ?)
                     AND (challenger_coin_name = ? OR challenged_coin_name = ?)
                   ORDER BY id DESC LIMIT 1""",
                (include_expired, coin_name, coin_name),
            )
            row = cursor.fetchone()
        return self._row_to_dict(row) if row else None

    def yield_challenge(self, coin_name: str, allow_wager: bool = True) -> dict:
        """Yield accepted matches; pending wagers return their stakes."""
        with self._get_conn() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("SELECT id FROM flip_off_challenges WHERE status IN ('pending','in_progress') AND (challenger_coin_name=? OR challenged_coin_name=?)", (coin_name, coin_name)).fetchone()
            if not row:
                raise FlipOffError(f'{coin_name} has no active challenge to yield.')
            wager = conn.execute('SELECT status FROM flip_off_wagers WHERE challenge_id=?', (row[0],)).fetchone()
            if wager and not allow_wager:
                raise FlipOffError('Tap your coin to authorize this sticker wager.')
            if wager and wager[0] == 'awaiting_acceptance':
                self._cancel(conn, row[0])
            else:
                self._finish(conn, row[0], coin_name)
        return self.get_challenge(row[0])

    def accept_challenge(self, challenge_id: int, coin_name: str, sticker_id: str) -> dict:
        """Lock the opponent's chosen stake and start a fresh scan baseline."""
        with self._get_conn() as conn:
            conn.execute('BEGIN IMMEDIATE')
            challenge = conn.execute("SELECT challenged_coin_name,status FROM flip_off_challenges WHERE id=?", (challenge_id,)).fetchone()
            wager = conn.execute('SELECT status FROM flip_off_wagers WHERE challenge_id=?', (challenge_id,)).fetchone()
            if not challenge or challenge[0] != coin_name or challenge[1] != 'pending' or not wager or wager[0] != 'awaiting_acceptance':
                raise FlipOffError('This wager cannot be accepted by this coin.')
            stake = self._lock(conn, sticker_id, coin_name, challenge_id)
            conn.execute("UPDATE flip_off_wagers SET status='accepted',challenged_stake=? WHERE challenge_id=?", (json.dumps(stake), challenge_id))
            baseline = conn.execute('SELECT COALESCE(MAX(id),0) FROM scan_logs').fetchone()[0]
            conn.execute('UPDATE flip_off_challenges SET baseline_scan_id=? WHERE id=?', (baseline, challenge_id))
        return self.get_challenge(challenge_id)

    def cancel_challenge(self, challenge_id: int, coin_name: str) -> dict:
        """Either participant may decline an unaccepted wager."""
        with self._get_conn() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("SELECT challenger_coin_name,challenged_coin_name,status FROM flip_off_challenges WHERE id=?", (challenge_id,)).fetchone()
            wager = conn.execute('SELECT status FROM flip_off_wagers WHERE challenge_id=?', (challenge_id,)).fetchone()
            if not row or coin_name not in row[:2] or row[2] != 'pending' or not wager or wager[0] != 'awaiting_acceptance':
                raise FlipOffError('Only an unaccepted wager can be cancelled.')
            self._cancel(conn, challenge_id)
        return self.get_challenge(challenge_id)

    def _cancel(self, conn: sqlite3.Connection, challenge_id: int) -> None:
        conn.execute("UPDATE flip_off_challenges SET status='expired',end_condition='expired',completed_at=CURRENT_TIMESTAMP WHERE id=?", (challenge_id,))
        self._settle(conn, challenge_id, None)

    def _lock(self, conn: sqlite3.Connection, sticker_id: str, coin: str, challenge_id: int) -> dict:
        row = conn.execute('SELECT id,coin_name,family_id,level FROM stickers WHERE id=? AND coin_name=? AND locked_challenge_id IS NULL', (sticker_id, coin)).fetchone()
        if not row:
            raise FlipOffError('Sticker is unavailable or belongs to another coin.')
        conn.execute('UPDATE stickers SET locked_challenge_id=? WHERE id=?', (challenge_id, sticker_id))
        return dict(zip(('id','coin_name','family_id','level'), row))

    def _settle(self, conn: sqlite3.Connection, challenge_id: int, winner: Optional[str]) -> None:
        row = conn.execute('SELECT status,challenger_stake,challenged_stake FROM flip_off_wagers WHERE challenge_id=?', (challenge_id,)).fetchone()
        if not row or row[0] in ('settled','returned'):
            return
        stakes = [json.loads(value) for value in row[1:] if value]
        for stake in stakes:
            owner = winner or stake['coin_name']
            conn.execute('UPDATE stickers SET coin_name=?,locked_challenge_id=NULL WHERE id=? AND locked_challenge_id=?', (owner, stake['id'], challenge_id))
        conn.execute('UPDATE flip_off_wagers SET status=? WHERE challenge_id=?', ('settled' if winner else 'returned', challenge_id))
        events = []
        for owner in sorted({winner or stake['coin_name'] for stake in stakes}):
            events.extend(self.stickers.evolve(conn, owner))
        conn.execute('UPDATE flip_off_wagers SET evolution_events=? WHERE challenge_id=?', (json.dumps(events), challenge_id))

    def get_recent_completed(self, limit: int = 3) -> list:
        """Returns the most recently completed challenges."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """SELECT id, created_at, baseline_scan_id, challenger_coin_name, challenged_coin_name,
                          flip_count, status, challenger_flips_done, challenged_flips_done,
                          challenger_entropy, challenged_entropy, winner_coin_name, completed_at, end_condition
                   FROM flip_off_challenges
                   WHERE status = 'complete'
                   ORDER BY completed_at DESC LIMIT ?""",
                (limit,),
            )
            rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def has_completed_since(self, ts: str) -> bool:
        """Returns True if any challenge was completed after the given ISO timestamp."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT 1 FROM flip_off_challenges WHERE status = 'complete' AND completed_at > ? LIMIT 1",
                (ts,),
            ).fetchall()
        return bool(rows)

    def get_completed_since(self, ts: str) -> list:
        """Returns challenges completed after the given ISO timestamp."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """SELECT id, created_at, baseline_scan_id, challenger_coin_name, challenged_coin_name,
                          flip_count, status, challenger_flips_done, challenged_flips_done,
                          challenger_entropy, challenged_entropy, winner_coin_name, completed_at, end_condition
                   FROM flip_off_challenges
                   WHERE status = 'complete' AND completed_at > ?
                   ORDER BY completed_at ASC""",
                (ts,),
            )
            rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_all_coin_stats(self) -> dict:
        """Returns flip-off W/L/D stats per coin for completed challenges."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT coin_name,
                       SUM(CASE WHEN winner_coin_name = coin_name THEN 1 ELSE 0 END) as wins,
                       SUM(CASE WHEN winner_coin_name != coin_name AND winner_coin_name != 'DRAW' THEN 1 ELSE 0 END) as losses,
                       SUM(CASE WHEN winner_coin_name = 'DRAW' THEN 1 ELSE 0 END) as draws
                FROM (
                    SELECT challenger_coin_name AS coin_name, winner_coin_name
                    FROM flip_off_challenges WHERE status = 'complete'
                    UNION ALL
                    SELECT challenged_coin_name AS coin_name, winner_coin_name
                    FROM flip_off_challenges WHERE status = 'complete'
                )
                GROUP BY coin_name
            """)
            rows = cursor.fetchall()
        return {row[0]: {"wins": row[1], "losses": row[2], "draws": row[3]} for row in rows}

    def get_all_active_challenges(self) -> list:
        """Returns all active (pending/in_progress) challenges."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """SELECT id, created_at, baseline_scan_id, challenger_coin_name, challenged_coin_name,
                          flip_count, status, challenger_flips_done, challenged_flips_done,
                          challenger_entropy, challenged_entropy, winner_coin_name, completed_at, end_condition
                   FROM flip_off_challenges
                   WHERE status IN ('pending', 'in_progress')
                   ORDER BY id DESC""",
            )
            rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def expire_stale_challenges(self, hours: int = 24) -> list:
        """Marks challenges older than `hours` hours as 'expired'.

        Returns:
            List of expired challenge dicts (for SSE notification).
        """
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        with self._get_conn() as conn:
            conn.execute('BEGIN IMMEDIATE')
            rows = conn.execute(
                """SELECT id FROM flip_off_challenges
                   WHERE status IN ('pending', 'in_progress') AND julianday(created_at) < julianday(?)""",
                (cutoff,),
            ).fetchall()
            if not rows:
                return []
            ids = [r[0] for r in rows]
            placeholders = ",".join("?" * len(ids))
            conn.execute(
                f"UPDATE flip_off_challenges SET status = 'expired', end_condition = 'expired', completed_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders})",  # noqa: S608
                ids,
            )
            for cid in ids:
                self._settle(conn, cid, None)
            conn.commit()

        log.info("[FLIP OFF] Expired %d challenge(s)", len(ids))
        return [self.get_challenge(cid) for cid in ids]

    def _row_to_dict(self, row: tuple) -> dict:
        keys = [
            "id", "created_at", "baseline_scan_id", "challenger_coin_name", "challenged_coin_name",
            "flip_count", "status", "challenger_flips_done", "challenged_flips_done",
            "challenger_entropy", "challenged_entropy", "winner_coin_name", "completed_at", "end_condition",
        ]
        result = dict(zip(keys, row))
        with self._get_conn() as conn:
            wager = conn.execute('SELECT status,challenger_stake,challenged_stake,evolution_events FROM flip_off_wagers WHERE challenge_id=?', (result['id'],)).fetchone()
        result.update(wagered=bool(wager), wager_status=wager[0] if wager else None, stakes=[], wager_evolutions=[])
        if wager:
            result['stakes'] = [self.stickers.decorate(json.loads(value)) for value in wager[1:3] if value]
            result['wager_evolutions'] = json.loads(wager[3])
        return result
