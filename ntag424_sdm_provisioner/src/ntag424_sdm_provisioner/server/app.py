import sys
from os import getenv
import logging
from flask import Flask, request, render_template
from pathlib import Path 

# Import from sibling modules in the same package
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, UID
from .game_state_manager import SqliteGameStateManager

app = Flask(__name__)

# Configure Logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

# Initialize Managers
# Logic: KeyManager is READ-ONLY for validation. SqliteGameStateManager handles game logic.
key_manager = CsvKeyManager(csv_path="data/tag_keys.csv") # Points to shared/local key DB
game_manager = SqliteGameStateManager(db_path="data/app.db")

@app.route('/')
def index():
    drew_test_outcome = request.args.get('drew_test_outcome', '').lower()
    is_test_mode = bool(drew_test_outcome)

    log.debug(f"STARTING drew_test_outcome: {drew_test_outcome}, is_test_mode: {is_test_mode}")

    uid_str = request.args.get('uid', '')
    ctr = request.args.get('ctr', '')
    cmac = request.args.get('cmac', '')

    params_display = {
        "Coin ID": UID(uid_str).asset_tag if uid_str else ""
    }

    # Get current totals for display regardless of validation outcome
    totals = game_manager.get_totals(include_test=is_test_mode)

    # Get initial recent flips
    recent_flips = game_manager.get_recent_flips()

    # Get randomness analysis
    randomness_stats = game_manager.analyze_flip_sequence_randomness(include_test=is_test_mode)

    # Get leaderboard stats
    leaderboard_stats = game_manager.get_leaderboard_stats(include_test=is_test_mode)


    if is_test_mode:
        if drew_test_outcome not in ['heads', 'tails', 'invalid']:
            return render_template('index.html', error="Invalid test outcome. Use 'heads' or 'tails' or 'invalid'.", params=params_display, totals=totals)

    if not uid_str or not ctr or not cmac:
        return render_template('index.html', error="Missing Parameters", params=params_display, totals=totals)

    uid = UID(uid_str)

    try:
        ctr_int = int(ctr, 16)
    except ValueError:
        return render_template('index.html', error="Invalid Counter Format", params=params_display, totals=totals, randomness_stats=randomness_stats, recent_flips=recent_flips, leaderboard_stats=leaderboard_stats)

    # 1. Validate Keys & CMAC (unless in test mode)
    if is_test_mode:
        log.debug(f"[VALIDATION] Skipped for test mode")
        validation_result = {'valid': True}
        # outcome from test param
        new_outcome_str = drew_test_outcome
    else:
        validation_result = key_manager.validate_sdm_url(uid, ctr_int, cmac)
        log.debug(f"[VALIDATION] UID: {uid}, CTR: {ctr_int}, CMAC: {cmac}, Result: {validation_result}")
        # Determine Outcome from KeyManager for real taps
        new_outcome_str = key_manager.get_outcome(uid).value

        
    if not validation_result['valid']:
        return render_template('index.html', error="CMAC Verification Failed", params=params_display, totals=totals, randomness_stats=randomness_stats, recent_flips=recent_flips, leaderboard_stats=leaderboard_stats)


    # 2. Game Logic & Replay Protection
    state = game_manager.get_state(uid_str)

    
    # Replay Check
    if is_test_mode:
        log.debug(f"[REPLAY] Skipped for test mode")
    elif ctr_int <= state.last_counter and not is_test_mode:
        msg = f"Illegal Replay Detected!" 
        log.warning(f"[REPLAY] {msg}")
        return render_template('index.html', error=msg, params=params_display, outcome='Invalid', totals=totals, randomness_stats=randomness_stats, recent_flips=recent_flips, leaderboard_stats=leaderboard_stats)

    # 3. Update State
    game_manager.update_state(uid_str, ctr_int, 
                              new_outcome_str, cmac, is_test=is_test_mode)

    # Get current totals for display regardless of validation outcome
    totals = game_manager.get_totals(include_test=is_test_mode)
    
    # Update display
    if is_test_mode:
        params_display['TEST'] = "YES"

    # Add tag-specific randomness to params display
    tag_randomness = game_manager.analyze_flip_sequence_randomness(include_test=is_test_mode, uid=uid_str)
    if tag_randomness and tag_randomness.get('total_bits', 0) > 0:
        params_display['Flips'] = tag_randomness['total_bits']
        params_display['Entropy'] = f"{tag_randomness['entropy']:.4f}"

    totals = game_manager.get_totals(include_test=is_test_mode) # Refresh totals after insert

    return render_template('index.html', outcome=new_outcome_str.upper(), params=params_display, totals=totals, recent_flips=recent_flips, randomness_stats=randomness_stats, leaderboard_stats=leaderboard_stats)

@app.route('/api/recent_flips')
def api_recent_flips():
    drew_test_outcome = request.args.get('drew_test_outcome', '').lower()
    is_test_mode = bool(drew_test_outcome)

    recent_flips = game_manager.get_recent_flips()
    totals = game_manager.get_totals(include_test=is_test_mode)
    return {"recent_flips": recent_flips, "totals": totals}

if __name__ == '__main__':
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    port = getenv("PORT", "5000")
    log.info(f"Starting Flask app on port {port}...")
    app.run(host='0.0.0.0', port=int(port), debug=True)