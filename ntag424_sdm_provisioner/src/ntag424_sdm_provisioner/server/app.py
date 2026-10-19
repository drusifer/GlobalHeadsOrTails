import logging
from os import getenv
from pathlib import Path
from flask import Flask, current_app, render_template, request

# Import from sibling modules in the same package
from ntag424_sdm_provisioner.csv_key_manager import UID, CsvKeyManager
from ntag424_sdm_provisioner.service_key_manager import ServiceKeyManager
from ntag424_sdm_provisioner.log_utils import mask_key
from ntag424_sdm_provisioner.server.coin_message_service import CoinMessageService
from ntag424_sdm_provisioner.server.vip_service import VipService
from ntag424_sdm_provisioner.server.flip_off_service import FlipOffError, FlipOffService
from ntag424_sdm_provisioner.server.game_state_manager import SqliteGameStateManager
from ntag424_sdm_provisioner.server.jokes import get_random_joke
from ntag424_sdm_provisioner.server.sticker_service import StickerService
from ntag424_sdm_provisioner.server.sticker_routes import register_sticker_routes, authenticated_coin

# Configure Logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


def _check_expired(flip_off_service) -> None:
    """Expire stale challenges (>24h). Called on every mutating request."""
    flip_off_service.expire_stale_challenges()


def init_managers(
    app,
    key_csv_path,
    db_path,
    vip_key_csv_path="data/vip_tag_keys.csv",
    service_url: str | None = None,
):
    """Initializes and attaches the key and game managers to the app instance."""
    svc_url = service_url or getenv("KEY_SERVICE_URL") or getenv("TAG_VALIDATOR_URL")
    if svc_url:
        log.info("[SERVER INIT] Using ServiceKeyManager connected to %s", svc_url)
        app.key_manager = ServiceKeyManager(service_url=svc_url, db_path=db_path)
    else:
        log.info("[SERVER INIT] Using CsvKeyManager with %s", key_csv_path)
        app.key_manager = CsvKeyManager(csv_path=key_csv_path)

    vip_csv = getenv("VIP_KEY_CSV_PATH", vip_key_csv_path)
    app.vip_key_manager = CsvKeyManager(
        csv_path=vip_csv,
        backup_path=f"{vip_csv}.bak",
        timestamped_backup_dir=str(Path(vip_csv).parent / "vip_backups"),
    )
    app.game_manager = SqliteGameStateManager(db_path=db_path)
    app.sticker_service = StickerService(db_path=db_path)
    app.flip_off_service = FlipOffService(db_path=db_path, sticker_service=app.sticker_service)
    app.coin_message_service = CoinMessageService(db_path=db_path)
    app.vip_service = VipService(db_path=db_path)

def parse_params(uid_str: str, ctr_str: str):
    uid = UID(uid_str)
    ctr_int = int(ctr_str, 16)
    return uid, ctr_int

def create_app(
    key_csv_path="data/tag_keys.csv",
    db_path="data/app.db",
    vip_key_csv_path="data/vip_tag_keys.csv",
    service_url: str | None = None,
):
    """Application factory for the Flask app."""
    app = Flask(__name__)

    with app.app_context():
        Path("data").mkdir(exist_ok=True)
        init_managers(
            current_app,
            key_csv_path,
            db_path,
            vip_key_csv_path=vip_key_csv_path,
            service_url=service_url,
        )
    register_sticker_routes(app)

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
        uid_str = uid.uid

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

        sticker_award = {"drop": None, "evolutions": []}
        if is_test_mode:
            game_manager.update_state(
                uid_str, ctr_int, new_outcome_str, coin_name=coin_name, cmac=cmac, is_test=True,
            )
            if new_outcome_str in ("heads", "tails"):
                sticker_award = current_app.sticker_service.award_flip(
                    coin_name, f"test:{uid_str}", ctr_int,
                )
        else:
            try:
                sticker_award = game_manager.record_validated_flip(
                    uid_str, ctr_int, new_outcome_str, coin_name, cmac,
                    current_app.sticker_service, flip_off_service,
                )
            except ValueError as exc:
                if str(exc) == "Replay detected":
                    return {"error": "Replay detected"}, 409
                raise
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
            "sticker_award": sticker_award,
            "stickers": current_app.sticker_service.collection(coin_name) if coin_name else [],
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
            sticker_id = request.form.get("sticker_id", "").strip()
            if sticker_id:
                verified_coin, error = authenticated_coin(request.form, challenger_coin)
                if error:
                    return error
                challenger_coin = verified_coin
            challenge_id = flip_off_service.create_challenge(
                challenger_coin, challenged_coin, flip_count,
                sticker_id=sticker_id or None,
            )
        except FlipOffError as e:
            return {"error": str(e)}, 400
        except ValueError:
            return {"error": "Choose a valid sticker copy."}, 400

        log.info("[FLIP OFF] Challenge %d created via POST", challenge_id)
        return {"challenge_id": challenge_id, "status": "pending"}, 201

    @app.route("/challenge/yield", methods=["POST"])
    def challenge_yield():
        """Yield an active challenge, granting the opponent an immediate victory."""
        flip_off_service = current_app.flip_off_service
        coin_name = request.form.get("coin_name", "").strip()
        if not coin_name:
            return {"error": "Missing coin_name"}, 400
        active = flip_off_service.get_active_challenge(coin_name)
        wager_authorized = False
        if (active and active.get("wagered")) or request.form.get("cmac"):
            _, error = authenticated_coin(request.form, coin_name)
            if error:
                return error
            wager_authorized = True
        try:
            result = flip_off_service.yield_challenge(coin_name, allow_wager=wager_authorized)
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


    @app.route("/api/vip/validate", methods=["GET"])
    def api_vip_validate():
        """Validate an NTAG 424 DNA SDM tap for gs.works/contact VIP mode."""
        uid_str = (request.args.get("uid") or request.args.get("id") or "").strip()
        ctr = (request.args.get("ctr") or request.args.get("counter") or "").strip()
        cmac = (request.args.get("cmac") or "").strip()

        if not uid_str or not ctr or not cmac:
            return {"valid": False, "vip": False, "reason": "missing_params"}, 400

        try:
            uid, ctr_int = parse_params(uid_str, ctr)
        except ValueError:
            return {"valid": False, "vip": False, "reason": "invalid_params"}, 400

        result = current_app.vip_key_manager.validate_sdm_url(uid, ctr_int, cmac)
        if not result.get("valid"):
            return {"valid": False, "vip": False, "reason": "invalid_cmac"}, 401

        if not current_app.vip_service.is_counter_fresh(uid.uid, ctr_int):
            return {"valid": False, "vip": False, "reason": "replayed_counter"}, 401

        return {
            "valid": True,
            "vip": True,
            "uid": uid.uid,
            "counter": ctr_int,
        }, 200

    @app.route("/api/vip/send", methods=["POST"])
    def api_vip_send():
        """Verify SDM tap, persist VIP Bat Signal message, and notify via ntfy.sh."""
        data = request.get_json(silent=True) or {}
        uid_str = (data.get("uid") or "").strip()
        ctr = (data.get("ctr") or "").strip()
        cmac = (data.get("cmac") or "").strip()
        sender = (data.get("sender") or "").strip()
        message = (data.get("message") or "").strip()

        if not sender or len(sender) > 120 or not message or len(message) > 1000:
            return {"ok": False, "error": "Invalid sender or message"}, 400

        if not uid_str or not ctr or not cmac:
            return {"ok": False, "error": "auth_failed"}, 401

        try:
            uid, ctr_int = parse_params(uid_str, ctr)
        except ValueError:
            return {"ok": False, "error": "auth_failed"}, 401

        result = current_app.vip_key_manager.validate_sdm_url(uid, ctr_int, cmac)
        if not result.get("valid"):
            return {"ok": False, "error": "auth_failed"}, 401

        if not current_app.vip_service.is_counter_fresh(uid.uid, ctr_int):
            return {"ok": False, "error": "auth_failed"}, 401

        ok, reason = current_app.vip_service.send_bat_signal(
            uid.uid, ctr_int, sender, message
        )
        if not ok:
            return {"ok": False, "error": reason}, 502

        return {"ok": True}, 200

    return app

# Create the Flask app instance for Gunicorn to discover
app = create_app()

if __name__ == "__main__":
    port = getenv("PORT", "5000")
    log.info(f"Starting Flask app on port {port}...")
    app.run(host="127.0.0.1", port=int(port), debug=False)
