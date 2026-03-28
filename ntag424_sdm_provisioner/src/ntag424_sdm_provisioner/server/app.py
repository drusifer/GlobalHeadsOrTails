import json
import logging
from os import getenv
from pathlib import Path
from flask import Flask, Response, current_app, render_template, request, stream_with_context

# Import from sibling modules in the same package
from ntag424_sdm_provisioner.csv_key_manager import UID, CsvKeyManager
from ntag424_sdm_provisioner.server.flip_off_service import FlipOffError, FlipOffService
from ntag424_sdm_provisioner.server.game_state_manager import SqliteGameStateManager
from ntag424_sdm_provisioner.server.jokes import get_random_joke

# Configure Logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)

# --- SSE listener registry (event-driven, no polling) ---
_sse_listeners: list = []

def _push_sse(data: dict) -> None:
    """Broadcast an SSE event to all connected clients."""
    payload = json.dumps(data)
    listeners = list(_sse_listeners)
    latest = data.get("latest_flip")
    completed = data.get("just_completed", [])
    active = data.get("active_challenges", [])
    log.info(
        "[SSE] push → %d listener(s) | flip=%s active=%d completed=%s",
        len(listeners),
        f"{latest['coin_name']}:{latest['outcome']}" if latest else "none",
        len(active),
        [(c.get("id"), c.get("winner_coin_name"), c.get("end_condition")) for c in completed] if completed else "[]",
    )
    for q in listeners:
        try:
            q.put_nowait(payload)
        except Exception:
            pass


def _check_expired(flip_off_service) -> None:
    """Expire stale challenges and push SSE if any were expired."""
    expired = flip_off_service.expire_stale_challenges()
    if expired:
        _push_sse({
            "recent_flips": [],
            "totals": None,
            "active_challenges": flip_off_service.get_all_active_challenges(),
            "recent_completed": flip_off_service.get_recent_completed(3),
            "latest_flip": None,
            "just_completed": expired,
        })


def init_managers(app, key_csv_path, db_path):
    """Initializes and attaches the key and game managers to the app instance."""
    app.key_manager = CsvKeyManager(csv_path=key_csv_path)
    app.game_manager = SqliteGameStateManager(db_path=db_path)
    app.flip_off_service = FlipOffService(db_path=db_path)

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

        totals = game_manager.get_totals(include_test=is_test_mode)
        recent_flips = game_manager.get_recent_flips()
        randomness_stats = game_manager.analyze_flip_sequence_randomness(include_test=is_test_mode)
        leaderboard_stats = game_manager.get_leaderboard_stats(include_test=is_test_mode)
        active_challenges = flip_off_service.get_all_active_challenges()
        recent_completed = flip_off_service.get_recent_completed(3)
        flip_off_stats = flip_off_service.get_all_coin_stats()

        params_display = None
        challenge = None
        if uid_str and ctr:
            try:
                uid, _ = parse_params(uid_str, ctr)
                tag_keys = key_manager.get_tag_keys(uid)
                coin_name = tag_keys.coin_name
                params_display = {"Coin Name": coin_name, "Asset Tag": uid.asset_tag}
                if is_test_mode:
                    params_display["TEST"] = "YES"
                challenge = flip_off_service.get_latest_challenge(coin_name) if coin_name else None
            except ValueError:
                params_display = {"Coin Name": "INVALID"}

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
        )

    @app.route("/api/flip")
    def api_flip():
        """Validate and record a coin flip, then push the result to all SSE clients."""
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
            log.debug("[VALIDATION] UID: %s, CTR: %s, Result: %s", uid, ctr_int, validation_result)
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

        totals = game_manager.get_totals(include_test=is_test_mode)
        recent_flips = game_manager.get_recent_flips()
        active_challenges = flip_off_service.get_all_active_challenges()
        challenge = flip_off_service.get_latest_challenge(coin_name) if coin_name else None

        just_completed = []
        if active_before:
            updated = flip_off_service.get_challenge(active_before["id"])
            if updated and updated["status"] == "complete":
                just_completed = [updated]

        latest_flip = recent_flips[0] if recent_flips else None
        _push_sse({
            "recent_flips": recent_flips,
            "totals": totals,
            "active_challenges": active_challenges,
            "recent_completed": flip_off_service.get_recent_completed(3),
            "latest_flip": latest_flip,
            "just_completed": just_completed,
        })

        joke = get_random_joke() if new_outcome_str.lower() in ("heads", "tails") else None
        return {
            "outcome": new_outcome_str.upper(),
            "coin_name": coin_name,
            "joke": joke,
            "challenge": challenge,
            "flip": latest_flip,
            "active_challenges": active_challenges,
        }, 200

    @app.route("/api/stream/flips")
    def stream_flips():
        """Server-Sent Events stream — event-driven via in-memory queue, no polling."""
        try:
            from gevent.queue import Queue, Empty
        except ImportError:
            from queue import Queue, Empty

        client_ip = request.remote_addr
        client_uid = request.args.get("uid", "")
        client_ctr = request.args.get("ctr", "")
        q = Queue()
        _sse_listeners.append(q)
        log.info("[SSE] client connected ip=%s uid=%s ctr=%s total_listeners=%d",
                 client_ip, client_uid or "(none)", client_ctr or "(none)", len(_sse_listeners))

        def generate():
            # Send an immediate comment so the browser fires onopen without waiting 30s
            yield ": connected\n\n"
            log.info("[SSE] sent connected comment ip=%s uid=%s", client_ip, client_uid or "(none)")
            try:
                while True:
                    try:
                        payload = q.get(timeout=2)
                        log.debug("[SSE] sending event to ip=%s", client_ip)
                        yield f"data: {payload}\n\n"
                    except Empty:
                        yield ": keepalive\n\n"
            finally:
                try:
                    _sse_listeners.remove(q)
                except ValueError:
                    pass
                log.info("[SSE] client disconnected ip=%s total_listeners=%d", client_ip, len(_sse_listeners))

        return Response(
            stream_with_context(generate()),
            content_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

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
        _push_sse({
            "recent_flips": [],
            "totals": None,
            "active_challenges": flip_off_service.get_all_active_challenges(),
            "recent_completed": flip_off_service.get_recent_completed(3),
            "latest_flip": None,
            "just_completed": [],
        })
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

        _push_sse({
            "recent_flips": [],
            "totals": None,
            "active_challenges": flip_off_service.get_all_active_challenges(),
            "recent_completed": flip_off_service.get_recent_completed(3),
            "latest_flip": None,
            "just_completed": [result],
        })
        return {"status": "yielded", "challenge": result}, 200


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
    # Monkey-patch stdlib so gevent Queue signaling works in the dev server.
    # gunicorn -k gevent does this automatically; the dev server does not.
    from gevent import monkey as _monkey
    _monkey.patch_all()
    port = getenv("PORT", "5000")
    log.info(f"Starting Flask app on port {port}...")
    app.run(host="127.0.0.1", port=int(port), debug=False)
