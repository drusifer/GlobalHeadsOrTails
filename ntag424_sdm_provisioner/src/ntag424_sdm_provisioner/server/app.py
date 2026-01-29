import logging
from os import getenv
from pathlib import Path
from flask import Flask, current_app, render_template, request

# Import from sibling modules in the same package
from ntag424_sdm_provisioner.csv_key_manager import UID, CsvKeyManager
from ntag424_sdm_provisioner.server.game_state_manager import SqliteGameStateManager

# Configure Logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def init_managers(app, key_csv_path, db_path):
    """Initializes and attaches the key and game managers to the app instance."""
    app.key_manager = CsvKeyManager(csv_path=key_csv_path)
    app.game_manager = SqliteGameStateManager(db_path=db_path)

def parse_params(uid_str: str, ctr_str: str):
    uid = UID(uid_str)
    ctr_int = int(ctr_str, 16)
    return uid, ctr_int

def create_app(key_csv_path="data/tag_keys.csv", db_path="data/app.db"):
    """Application factory for the Flask app."""
    app = Flask(__name__)

    # Ensure data directory exists and initialize managers within app context
    with app.app_context():
        Path("data").mkdir(exist_ok=True)
        init_managers(current_app, key_csv_path, db_path)

    @app.route("/")
    def index():
        key_manager = current_app.key_manager
        game_manager = current_app.game_manager

        drew_test_outcome = request.args.get("drew_test_outcome", "").lower()

        is_test_mode = bool(drew_test_outcome)
        log.debug(f"STARTING drew_test_outcome: {drew_test_outcome}, is_test_mode: {is_test_mode}")
        uid_str = request.args.get("uid", "")
        ctr = request.args.get("ctr", "")
        cmac = request.args.get("cmac", "")

        # Get current totals for display regardless of validation outcome

        totals = game_manager.get_totals(include_test=is_test_mode)

        # Get initial recent flips

        recent_flips = game_manager.get_recent_flips()

        # Get randomness analysis

        randomness_stats = game_manager.analyze_flip_sequence_randomness(include_test=is_test_mode)

        # Get leaderboard stats

        leaderboard_stats = game_manager.get_leaderboard_stats(include_test=is_test_mode)

        try:
            uid, ctr_int = parse_params(uid_str, ctr)
        except ValueError:
            params_display = {"Coin Name": "INVALID"}
            return render_template(
                "index.html",
                error="Invalid Counter Format",
                params=params_display,
                totals=totals,
                randomness_stats=randomness_stats,
                recent_flips=recent_flips,
                leaderboard_stats=leaderboard_stats,
            )

        tag_keys = key_manager.get_tag_keys(uid)
        coin_name = tag_keys.coin_name

        # Prioritize coin_name for display, fallback to asset_tag
        params_display = {"Coin Name": coin_name, "Asset Tag": uid.asset_tag}


        if is_test_mode:
            if drew_test_outcome not in ["heads", "tails", "invalid"]:
                return render_template(
                    "index.html",
                    error="Invalid test outcome. Use 'heads' or 'tails' or 'invalid'.",
                    params=params_display,
                    totals=totals,
                )

        if not uid_str or not ctr or not cmac:
            return render_template(
                "index.html", error="Missing Parameters", params=params_display, totals=totals
            )

        # 1. Validate Keys & CMAC (unless in test mode)

        if is_test_mode:
            log.debug("[VALIDATION] Skipped for test mode")
            validation_result = {"valid": True}

            # outcome from test param
            new_outcome_str = drew_test_outcome
        else:
            validation_result = key_manager.validate_sdm_url(uid, ctr_int, cmac)

            log.debug(
                f"[VALIDATION] UID: {uid}, CTR: {ctr_int}, CMAC: {cmac}, Result: {validation_result}"
            )

            # Determine Outcome from KeyManager for real taps

            new_outcome_str = tag_keys.outcome.value

        if not validation_result["valid"]:
            return render_template(
                "index.html",
                error="CMAC Verification Failed",
                params=params_display,
                totals=totals,
                randomness_stats=randomness_stats,
                recent_flips=recent_flips,
                leaderboard_stats=leaderboard_stats,
            )

        # 2. Game Logic & Replay Protection

        state = game_manager.get_state(uid_str)

        # Replay Check

        if is_test_mode:
            log.debug("[REPLAY] Skipped for test mode")

        elif ctr_int <= state.last_counter and not is_test_mode:
            msg = "Illegal Replay Detected!"

            log.warning(f"[REPLAY] {msg}")

            return render_template(
                "index.html",
                error=msg,
                params=params_display,
                outcome="Invalid",
                totals=totals,
                randomness_stats=randomness_stats,
                recent_flips=recent_flips,
                leaderboard_stats=leaderboard_stats,
            )

        # 3. Update State

        game_manager.update_state(
            uid_str, ctr_int, new_outcome_str, coin_name=coin_name, cmac=cmac, is_test=is_test_mode
        )

        # Get current totals for display regardless of validation outcome

        totals = game_manager.get_totals(include_test=is_test_mode)

        # Update display

        if is_test_mode:
            params_display["TEST"] = "YES"

            # Add tag-specific randomness to params display

            tag_randomness = game_manager.analyze_flip_sequence_randomness(
                include_test=is_test_mode, coin_name=coin_name
            )

            if tag_randomness and tag_randomness.get("total_bits", 0) > 0:
                params_display["Flips"] = tag_randomness["total_bits"]

                params_display["Entropy"] = f"{tag_randomness['entropy']:.4f}"

        totals = game_manager.get_totals(include_test=is_test_mode)  # Refresh totals after insert

        # Refresh recent flips to include the one we just added
        recent_flips = game_manager.get_recent_flips()

        return render_template(
            "index.html",
            outcome=new_outcome_str.upper(),
            params=params_display,
            totals=totals,
            recent_flips=recent_flips,
            randomness_stats=randomness_stats,
            leaderboard_stats=leaderboard_stats,
        )

    @app.route("/api/recent_flips")
    def api_recent_flips():
        game_manager = current_app.game_manager

        drew_test_outcome = request.args.get("drew_test_outcome", "").lower()

        is_test_mode = bool(drew_test_outcome)

        recent_flips = game_manager.get_recent_flips()

        totals = game_manager.get_totals(include_test=is_test_mode)

        return {"recent_flips": recent_flips, "totals": totals}

    return app


if __name__ == "__main__":
    port = getenv("PORT", "5000")
    log.info(f"Starting Flask app on port {port}...")
    app = create_app()
    app.run(host="127.0.0.1", port=int(port), debug=False)