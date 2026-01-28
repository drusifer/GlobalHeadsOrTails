import logging
from os import getenv
from pathlib import Path

from flask import Flask, render_template, request

# Import from sibling modules in the same package
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.uid_utils import UID

from .game_state_manager import SqliteGameStateManager


app = Flask(__name__)

# Configure Logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Initialize Managers
# Logic: KeyManager is READ-ONLY for validation. SqliteGameStateManager handles game logic.
key_manager = CsvKeyManager(csv_path="data/tag_keys.csv") # Points to shared/local key DB
game_manager = SqliteGameStateManager(db_path="data/app.db")

@app.route('/')
def index():
    uid_str = request.args.get('uid', '')
    ctr = request.args.get('ctr', '')
    cmac = request.args.get('cmac', '')

    params_display = {
        "uid": uid_str,
        "ctr": ctr,
        "cmac": cmac
    }

    # Get current totals for display regardless of validation outcome
    totals = game_manager.get_totals()

    if not uid_str or not ctr or not cmac:
        return render_template('index.html', error="Missing Parameters", params=params_display, totals=totals)

    # Convert UID string to UID object
    try:
        uid = UID(uid_str)
    except ValueError:
        return render_template('index.html', error="Invalid UID Format", params=params_display, totals=totals)

    # 1. Validate Keys & CMAC (Read-Only access to KeyManager)
    try:
        ctr_int = int(ctr, 16) # Counter is hex in URL? Code.gs says: `parseInt(value, 16)` if param is 'ctr'.
        # Wait, Code.gs line 33: `params_info['ctr'] = parseInt(value, 16);`
        # And line 34: `params_info['counter_hex'] = value;`
        # So 'ctr' param in URL is HEX.
    except ValueError:
        return render_template('index.html', error="Invalid Counter Format", params=params_display, totals=totals)

    validation_result = key_manager.validate_sdm_url(uid, ctr_int, cmac)
    log.debug(f"[VALIDATION] UID: {uid}, CTR: {ctr_int}, CMAC: {cmac}, Result: {validation_result}")
    
    if not validation_result['valid']:
        return render_template('index.html', error="CMAC Verification Failed", params=params_display, totals=totals)

    # 2. Game Logic & Replay Protection
    state = game_manager.get_state(uid_str)

    # Replay Check
    if ctr_int <= state.last_counter:
        msg = f"Replay Detected! Old Counter {state.last_counter} >= New {ctr_int}"
        log.warning(f"[REPLAY] {msg}")
        return render_template('index.html', error=msg, params=params_display, outcome='Invalid', totals=totals)

    # 3. Determine Outcome & Coin Name (Pre-determined based on UID from Keys DB)
    tag_keys = key_manager.get_tag_keys(uid)
    new_outcome = tag_keys.outcome
    coin_name = tag_keys.coin_name

    # Update State with coin_name
    game_manager.update_state(uid_str, ctr_int, new_outcome.value, coin_name=coin_name, cmac=cmac)

    # Update display
    params_display['outcome'] = new_outcome
    params_display['coin_name'] = coin_name
    params_display['counter_int'] = ctr_int
    totals = game_manager.get_totals() # Refresh totals after insert

    return render_template('index.html', outcome=new_outcome.value, params=params_display, totals=totals)

if __name__ == '__main__':
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    port = getenv("PORT", "5000")
    log.info(f"Starting Flask app on port {port}...")
    app.run(host='0.0.0.0', port=int(port), debug=True)
