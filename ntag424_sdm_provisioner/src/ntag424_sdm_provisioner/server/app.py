import logging
from os import getenv
from pathlib import Path
from flask import Flask, current_app, render_template, request

# Import from sibling modules in the same package
from ntag424_sdm_provisioner.csv_key_manager import UID, CsvKeyManager
from ntag424_sdm_provisioner.log_utils import mask_key
from ntag424_sdm_provisioner.server.coin_message_service import CoinMessageService
from ntag424_sdm_provisioner.server.flip_off_service import FlipOffError, FlipOffService
from ntag424_sdm_provisioner.server.game_state_manager import SqliteGameStateManager
from ntag424_sdm_provisioner.server.jokes import get_random_joke

# Configure Logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


def _check_expired(flip_off_service) -> None:
    """Expire stale challenges (>24h). Called on every mutating request."""
    flip_off_service.expire_stale_challenges()


def init_managers(app, key_csv_path, db_path):
    """Initializes and attaches the key and game managers to the app instance."""
    app.key_manager = CsvKeyManager(csv_path=key_csv_path)
    app.game_manager = SqliteGameStateManager(db_path=db_path)
    app.flip_off_service = FlipOffService(db_path=db_path)
    app.coin_message_service = CoinMessageService(db_path=db_path)

def parse_params(uid_str: str, ctr_str: str):
    uid = UID(uid_str)
    ctr_int = int(ctr_str, 16)
    return uid, ctr_int

def create_app(key_csv_path="data/tag_keys.csv", db_path="data/app.db"):
    """Application factory for the Flask app."""
    app = Flask(__name__)

    with app.app_context():
        Path("data").mkdir(exist_ok=True)
        init_managers(current_app, key_csv_path, db_path)

    @app.route("/")
    def index():
        """Render the page. No flip recorded here — JS calls /api/flip after load."""
        key_manager = current_app.key_manager
        game_manager = current_app.game_manager
        flip_off_service = current_app.flip_off_service
        _check_expired(flip_off_service)

        is_test_mode = bool(request.args.get("drew_test_outcome", ""))
        uid_str = request.args.get("uid", "")
        ctr = request.args.get("ctr", "")
        cmac = request.args.get("cmac", "")

        totals = game_manager.get_totals(include_test=is_test_mode)
        recent_flips = game_manager.get_recent_flips()
        randomness_stats = game_manager.analyze_flip_sequence_randomness(include_test=is_test_mode)
        leaderboard_stats = game_manager.get_leaderboard_stats(include_test=is_test_mode)
        active_challenges = flip_off_service.get_all_active_challenges()
        recent_completed = flip_off_service.get_recent_completed(3)
        flip_off_stats = flip_off_service.get_all_coin_stats()

        params_display = None
        challenge = None
        coin_name = None
        heads_message = ""
        tails_message = ""
        if uid_str and ctr:
            try:
                uid, ctr_int = parse_params(uid_str, ctr)
                tag_keys = key_manager.get_tag_keys(uid)
                params_display = {"Coin Name": tag_keys.coin_name, "Asset Tag": uid.asset_tag}
                if is_test_mode:
                    params_display["TEST"] = "YES"
                last_counter = game_manager.get_state(uid_str).last_counter
                tap_valid = is_test_mode or (
                    bool(cmac)
                    and ctr_int > last_counter
                    and key_manager.validate_sdm_url(uid, ctr_int, cmac)["valid"]
                )
                if tap_valid:
                    coin_name = tag_keys.coin_name
                    challenge = flip_off_service.get_latest_challenge(coin_name) if coin_name else None
                    if coin_name:
                        heads_message, tails_message = current_app.coin_message_service.get_messages(coin_name)
            except ValueError:
                params_display = {"Coin Name": "INVALID"}

        my_coin = params_display.get("Coin Name") if params_display and params_display.get("Coin Name") != "INVALID" else None
        recent_opponents: list = []
        other_opponents: list = []
        if my_coin:
            all_opp = [c for c in leaderboard_stats if c["coin_name"] != my_coin]
            by_recency = sorted(all_opp, key=lambda x: x.get("last_flip_timestamp", ""), reverse=True)
            recent_opponents = by_recency[:3]
            recent_names = {c["coin_name"] for c in recent_opponents}
            other_opponents = sorted(
                [c for c in all_opp if c["coin_name"] not in recent_names],
                key=lambda x: x["coin_name"],
            )

        return render_template(
            "index.html",
            params=params_display,
            totals=totals,
            recent_flips=recent_flips,
            randomness_stats=randomness_stats,
            leaderboard_stats=leaderboard_stats,
            challenge=challenge,
            active_challenges=active_challenges,
            recent_completed=recent_completed,
            flip_off_stats=flip_off_stats,
            coin_name=coin_name,
            uid=uid_str,
            cmac=cmac,
            ctr=ctr,
            heads_message=heads_message,
            tails_message=tails_message,
            recent_opponents=recent_opponents,
            other_opponents=other_opponents,
        )

    @app.route("/api/flip")
    def api_flip():
        """Validate and record a coin flip."""
        log.info("[FLIP] /api/flip called from ip=%s uid=%s ctr=%s",
                 request.remote_addr, request.args.get("uid", ""), request.args.get("ctr", ""))
        key_manager = current_app.key_manager
        game_manager = current_app.game_manager
        flip_off_service = current_app.flip_off_service
        _check_expired(flip_off_service)

        drew_test_outcome = request.args.get("drew_test_outcome", "").lower()
        is_test_mode = bool(drew_test_outcome)
        uid_str = request.args.get("uid", "")
        ctr = request.args.get("ctr", "")
        cmac = request.args.get("cmac", "")

        if not uid_str or not ctr or not cmac:
            return {"error": "Missing parameters"}, 400

        try:
            uid, ctr_int = parse_params(uid_str, ctr)
        except ValueError:
            return {"error": "Invalid counter format"}, 400

        tag_keys = key_manager.get_tag_keys(uid)
        coin_name = tag_keys.coin_name

        if is_test_mode:
            if drew_test_outcome not in ["heads", "tails", "invalid"]:
                return {"error": "Invalid test outcome"}, 400
            validation_result = {"valid": True}
            new_outcome_str = drew_test_outcome
        else:
            validation_result = key_manager.validate_sdm_url(uid, ctr_int, cmac)
            safe = {k: (mask_key(v) if k in ("session_key", "full_cmac") else v)
                    for k, v in validation_result.items()}
            log.debug("[VALIDATION] UID: %s, CTR: %s, Result: %s", uid, ctr_int, safe)
            new_outcome_str = tag_keys.outcome.value

        if not validation_result["valid"]:
            return {"error": "CMAC verification failed"}, 401

        state = game_manager.get_state(uid_str)
        if not is_test_mode and ctr_int <= state.last_counter:
            log.warning("[REPLAY] Illegal replay detected for %s", uid_str)
            return {"error": "Replay detected"}, 409

        # Snapshot active challenge before recording to detect completions
        active_before = flip_off_service.get_active_challenge(coin_name) if coin_name else None

        game_manager.update_state(
            uid_str, ctr_int, new_outcome_str, coin_name=coin_name, cmac=cmac, is_test=is_test_mode
        )

        if not is_test_mode and coin_name:
            flip_off_service.record_flip(coin_name)

        active_challenges = flip_off_service.get_all_active_challenges()
        challenge = flip_off_service.get_latest_challenge(coin_name) if coin_name else None

        just_completed = []
        if active_before:
            updated = flip_off_service.get_challenge(active_before["id"])
            if updated and updated["status"] == "complete":
                just_completed = [updated]

        recent_flips = game_manager.get_recent_flips()
        latest_flip = recent_flips[0] if recent_flips else None
        msgs = current_app.coin_message_service.get_messages(coin_name) if coin_name else ("", "")
        joke = get_random_joke() if new_outcome_str.lower() in ("heads", "tails") else None
        return {
            "outcome": new_outcome_str.upper(),
            "coin_name": coin_name,
            "joke": joke,
            "challenge": challenge,
            "flip": latest_flip,
            "active_challenges": active_challenges,
            "just_completed": just_completed,
            "heads_message": msgs[0],
            "tails_message": msgs[1],
            "totals": game_manager.get_totals(include_test=is_test_mode),
        }, 200

    @app.route("/api/flips/since")
    def api_flips_since():
        """Cheap poll check: returns {"has_new": bool} if any flip newer than `ts` exists.

        The client passes the ISO timestamp of its last observed flip.
        Also triggers stale-challenge expiry so expiry fires regularly without SSE.
        """
        game_manager = current_app.game_manager
        flip_off_service = current_app.flip_off_service
        _check_expired(flip_off_service)
        ts = request.args.get("ts", "")
        if not ts:
            has_new = True
        else:
            has_new = game_manager.has_flip_since(ts) or flip_off_service.has_completed_since(ts)
        return {"has_new": has_new}

    @app.route("/api/state")
    def api_state():
        """Full state snapshot for the poll loop to consume when has_new=true.

        Optional `since` param: ISO timestamp — populates just_completed with
        challenges that finished after that point.
        """
        game_manager = current_app.game_manager
        flip_off_service = current_app.flip_off_service
        is_test_mode = bool(request.args.get("drew_test_outcome", ""))
        since = request.args.get("since", "")

        recent_flips = game_manager.get_recent_flips()
        just_completed = flip_off_service.get_completed_since(since) if since else []

        return {
            "recent_flips": recent_flips,
            "totals": game_manager.get_totals(include_test=is_test_mode),
            "active_challenges": flip_off_service.get_all_active_challenges(),
            "recent_completed": flip_off_service.get_recent_completed(3),
            "latest_flip": recent_flips[0] if recent_flips else None,
            "just_completed": just_completed,
            "latest_timestamp": recent_flips[0]["timestamp"] if recent_flips else "",
        }

    @app.route("/challenge/create", methods=["POST"])
    def challenge_create():
        """Creates a new Flip Off challenge."""
        flip_off_service = current_app.flip_off_service
        challenger_coin = request.form.get("challenger_coin", "").strip()
        challenged_coin = request.form.get("challenged_coin", "").strip()
        try:
            flip_count = int(request.form.get("flip_count", 0))
        except ValueError:
            return {"error": "Invalid flip_count"}, 400

        if not challenger_coin or not challenged_coin:
            return {"error": "Missing coin names"}, 400

        try:
            challenge_id = flip_off_service.create_challenge(challenger_coin, challenged_coin, flip_count)
        except FlipOffError as e:
            return {"error": str(e)}, 400

        log.info("[FLIP OFF] Challenge %d created via POST", challenge_id)
        return {"challenge_id": challenge_id, "status": "pending"}, 201

    @app.route("/challenge/yield", methods=["POST"])
    def challenge_yield():
        """Yield an active challenge, granting the opponent an immediate victory."""
        flip_off_service = current_app.flip_off_service
        coin_name = request.form.get("coin_name", "").strip()
        if not coin_name:
            return {"error": "Missing coin_name"}, 400
        try:
            result = flip_off_service.yield_challenge(coin_name)
        except FlipOffError as e:
            return {"error": str(e)}, 400
        return {"status": "yielded", "challenge": result}, 200


    @app.route("/api/coin/messages", methods=["POST"])
    def set_coin_messages():
        """Set custom Heads/Tails display messages for a coin. Auth: CMAC from the tap URL."""
        data = request.get_json(silent=True) or {}
        coin_name = data.get("coin_name", "").strip()
        uid_str = data.get("uid", "").strip()
        cmac = data.get("cmac", "").strip()
        ctr = data.get("ctr", "").strip()
        heads = data.get("heads_message", "").strip()
        tails = data.get("tails_message", "").strip()

        log.debug("[COIN MSG] save request coin=%r uid=%s ctr=%s cmac=%s heads=%r tails=%r",
                  coin_name, uid_str, ctr, mask_key(cmac), heads, tails)

        if not coin_name or not uid_str or not cmac or not ctr:
            log.debug("[COIN MSG] rejected — missing fields: coin=%r uid=%r cmac=%r ctr=%r",
                      bool(coin_name), bool(uid_str), bool(cmac), bool(ctr))
            return {"error": "Missing required fields"}, 400

        if len([*heads]) > 24 or len([*tails]) > 24:
            log.debug("[COIN MSG] rejected — message too long: heads=%d tails=%d", len([*heads]), len([*tails]))
            return {"error": "Message exceeds 24 characters"}, 400

        try:
            uid, ctr_int = parse_params(uid_str, ctr)
        except ValueError:
            log.debug("[COIN MSG] rejected — invalid uid or counter: uid=%r ctr=%r", uid_str, ctr)
            return {"error": "Invalid uid or counter"}, 400

        result = current_app.key_manager.validate_sdm_url(uid, ctr_int, cmac)
        log.debug("[COIN MSG] cmac validation result: valid=%s", result["valid"])
        if not result["valid"]:
            log.warning("[COIN MSG] auth failed for coin=%r uid=%s ctr=%s", coin_name, uid_str, ctr)
            return {"error": "auth_failed"}, 401

        current_app.coin_message_service.set_messages(coin_name, heads, tails)
        log.info("[COIN MSG] saved coin=%r heads=%r tails=%r", coin_name, heads, tails)
        return {"heads_message": heads, "tails_message": tails}, 200

    @app.route("/api/recent_flips")
    def api_recent_flips():
        game_manager = current_app.game_manager
        is_test_mode = bool(request.args.get("drew_test_outcome", ""))
        return {
            "recent_flips": game_manager.get_recent_flips(),
            "totals": game_manager.get_totals(include_test=is_test_mode),
        }

    return app

# Create the Flask app instance for Gunicorn to discover
app = create_app()

if __name__ == "__main__":
    port = getenv("PORT", "5000")
    log.info(f"Starting Flask app on port {port}...")
    app.run(host="127.0.0.1", port=int(port), debug=False)
