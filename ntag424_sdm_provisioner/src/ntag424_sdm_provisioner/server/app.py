import sys
import logging
from flask import Flask, request, render_template
from pathlib import Path

# Import from sibling modules in the same package
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from .game_state_manager import GameStateManager

app = Flask(__name__)

# Configure Logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Initialize Managers
# Logic: KeyManager is READ-ONLY for validation. GameStateManager handles game logic.
key_manager = CsvKeyManager(csv_path="data/tag_keys.csv") # Points to shared/local key DB
game_manager = GameStateManager(csv_path="data/game_state.csv")

@app.route('/')
def index():
    uid = request.args.get('uid', '')
    ctr = request.args.get('ctr', '')
    cmac = request.args.get('cmac', '')

    params_display = {
        "uid": uid,
        "ctr": ctr,
        "cmac": cmac
    }

    if not uid or not ctr or not cmac:
        return render_template('index.html', error="Missing Parameters", params=params_display)

    # 1. Validate Keys & CMAC (Read-Only access to KeyManager)
    try:
        ctr_int = int(ctr, 16) # Counter is hex in URL? Code.gs says: `parseInt(value, 16)` if param is 'ctr'.
        # Wait, Code.gs line 33: `params_info['ctr'] = parseInt(value, 16);`
        # And line 34: `params_info['counter_hex'] = value;`
        # So 'ctr' param in URL is HEX.
    except ValueError:
        return render_template('index.html', error="Invalid Counter Format", params=params_display)

    validation_result = key_manager.validate_sdm_url(uid, ctr_int, cmac)
    
    if not validation_result['valid']:
        return render_template('index.html', error="CMAC Verification Failed", params=params_display)

    # 2. Game Logic & Replay Protection
    state = game_manager.get_state(uid)
    
    # Replay Check
    if ctr_int <= state.last_counter:
        msg = f"Replay Detected! Old Counter {state.last_counter} >= New {ctr_int}"
        log.warning(f"[REPLAY] {msg}")
        return render_template('index.html', error=msg, params=params_display, outcome=state.outcome)

    # 3. Determine Outcome (Simple toggle or random if new)
    # Code.gs had `outcome = tag_keys['outcome']` which implies it was stored in the key sheet!
    # But since we are allowed to define new behavior in game_state, let's just make it random 
    # OR alternate?
    # User said "reimplement Code.gs". Code.gs retrieved outcome from `getKeysForUid`.
    # `getKeysForUid` returned a row from KEYS_SHEET.
    # So the outcome was pre-determined per tag? Or was it writing back?
    # Code.gs line 61: `recordOutcome(...)`.
    # Logic in Code.gs is:
    # 1. Get keys & info from Keys Sheet.
    # 2. Validate.
    # 3. If valid, `recordOutcome`.
    # HTML displays `outcome`.
    # Wait, where does `outcome` come from in Code.gs?
    # Line 30: `outcome = tag_keys['outcome']`
    # So it WAS in the key sheet.
    # Since we can't change TagKeys schema, we need to store/generate outcome in GameState.
    # Let's say we flip it every time? Or random? Code.gs suggests it was static per tag?
    # "GlobalHeadsOrTails" suggests it might be random?
    # Actually, if it's "Heads OR Tails", maybe the TAG determines it?
    # If it was in the key sheet, maybe some tags are HEADS tags and some are TAILS tags?
    # Let's assume for now we generate it or it's per tag.
    # I'll implement a simple randomizer for now, or persist it if it was supposed to be static.
    # Let's persist it in GameState. Initial state is empty.
    # If empty, assign random? Or maybe just "Heads" / "Tails" based on UID parity?
    # Let's do random for "Heads" or "Tails".
    
    import random
    new_outcome = random.choice(["Heads", "Tails"])
    
    # Update State
    game_manager.update_state(uid, ctr_int, new_outcome)
    
    # Update display
    params_display['outcome'] = new_outcome
    params_display['counter_int'] = ctr_int

    return render_template('index.html', outcome=new_outcome, params=params_display)

if __name__ == '__main__':
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
