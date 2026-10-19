"""Sticker game odds from exact coin outcome counts, without byte padding."""
import math
import sqlite3


def calculate_sticker_odds(heads: int, tails: int) -> dict:
    """Weight a 50% ceiling by balance scores, keeping a 5% starter floor."""
    count = heads + tails
    entropy = 0.0
    if heads and tails:
        ratio = heads / count
        entropy = -8 * (ratio * math.log2(ratio) + (1-ratio) * math.log2(1-ratio))
    p_value = math.erfc(abs(heads-tails) / math.sqrt(2*count)) if count >= 100 else None
    weight = entropy / 8 * (p_value if p_value is not None else 1)
    return {
        'drop_chance': min(.5, .5 * max(.1, weight)),
        'entropy': entropy, 'p_value': p_value, 'flip_count': count,
        'heads': heads, 'tails': tails, 'warmup': count < 100,
    }


def coin_sticker_odds(conn: sqlite3.Connection, coin_name: str, include_test: bool = False) -> dict:
    """Pool both face UIDs by coin name in the caller's current transaction."""
    query = "SELECT LOWER(outcome), COUNT(*) FROM scan_logs WHERE coin_name = ? AND LOWER(outcome) IN ('heads','tails')"
    if not include_test:
        query += ' AND is_test IS FALSE'
    counts = dict(conn.execute(query + ' GROUP BY LOWER(outcome)', (coin_name,)).fetchall())
    return {**calculate_sticker_odds(counts.get('heads',0), counts.get('tails',0)), 'includes_test': include_test}
