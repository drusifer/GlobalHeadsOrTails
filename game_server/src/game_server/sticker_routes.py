"""Collection reads and coin-authenticated wager actions."""

from collections.abc import Mapping
from contextlib import closing
import sqlite3

from game_server.sticker_odds import coin_sticker_odds

from flask import Flask, current_app, request

from game_server.csv_key_manager import UID
from game_server.flip_off_service import FlipOffError


def authenticated_coin(data, expected: str = "") -> tuple:
    """Bind a wager action to the coin behind a genuine signed tag tap."""
    try:
        uid = UID(str(data.get("uid", "")))
        counter = int(str(data.get("ctr", "")), 16)
        cmac = str(data.get("cmac", ""))
        if not 0 <= counter <= 0xFFFFFF or not cmac:
            raise ValueError("Missing tap credentials")
        keys = current_app.key_manager.get_tag_keys(uid)
        valid = current_app.key_manager.validate_sdm_url(uid, counter, cmac)["valid"]
        if not valid or not keys.coin_name:
            raise ValueError("Invalid tap")
    except (ValueError, TypeError, KeyError):
        return None, ({"error": "Tap your coin to authorize this sticker wager."}, 401)
    if expected and keys.coin_name != expected:
        return None, ({"error": "This tap belongs to a different coin."}, 403)
    return keys.coin_name, None


def register_sticker_routes(app: Flask) -> None:
    """Attach public album reads and signed, ownership-checked wager mutations."""

    @app.get("/api/stickers")
    def stickers():
        coin = request.args.get("coin_name", "").strip()
        service = current_app.flip_off_service
        service.expire_stale_challenges()
        with closing(sqlite3.connect(current_app.sticker_service.db_path)) as conn:
            odds = coin_sticker_odds(conn, coin, include_test=bool(request.args.get("drew_test_outcome"))) if coin else None
        collection = current_app.sticker_service.collection(coin) if coin else []
        return {
            "odds": odds,
            "catalog": current_app.sticker_service.public_catalog(collection),
            "coin_name": coin,
            "stickers": collection,
            "challenge": service.get_latest_challenge(coin, include_expired=True) if coin else None,
            "active_challenges": service.get_all_active_challenges(),
            "recent_completed": service.get_recent_completed(3),
        }

    def wager_action(action: str):
        json_data = request.get_json(silent=True)
        data = request.form if json_data is None else json_data
        if not isinstance(data, Mapping):
            return {"error": "Submit a wager object."}, 400
        coin, error = authenticated_coin(data)
        if error:
            return error
        try:
            challenge_id = int(data.get("challenge_id", ""))
            service = current_app.flip_off_service
            service.expire_stale_challenges()
            if action == "accept":
                challenge = service.accept_challenge(challenge_id, coin, str(data.get("sticker_id", "")))
            else:
                challenge = service.cancel_challenge(challenge_id, coin)
        except (ValueError, TypeError, FlipOffError) as exc:
            return {"error": str(exc) or "Choose a valid challenge and sticker."}, 400
        return {"challenge": challenge, "stickers": current_app.sticker_service.collection(coin)}

    @app.post("/challenge/accept")
    def accept():
        return wager_action("accept")

    @app.post("/challenge/cancel")
    def cancel():
        return wager_action("cancel")
