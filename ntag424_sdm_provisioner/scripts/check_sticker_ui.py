"""Real Flask/SQLite and mobile Chromium acceptance check; no production data."""
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from types import SimpleNamespace
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server
from ntag424_sdm_provisioner.csv_key_manager import Outcome
from ntag424_sdm_provisioner.server.app import create_app

UIDS = {'A': '0401000000001A', 'B': '0402000000002A'}

class SignedKeys:
    def get_tag_keys(self, uid):
        coin = next((coin for coin, value in UIDS.items() if value == getattr(uid, 'uid', str(uid))), None)
        if coin is None:
            raise ValueError('Unknown fixture coin')
        return SimpleNamespace(coin_name=coin, outcome=Outcome.HEADS)

    def validate_sdm_url(self, uid, counter, cmac):
        return {'valid': getattr(uid, 'uid', str(uid)) in UIDS.values() and cmac == 'VALID'}

class FixedRandom:
    def __init__(self, drop=0, index=0):
        self.drop = drop
        self.index = index
    def random(self):
        return self.drop
    def choice(self, values):
        return values[self.index]

def credentials(coin, counter):
    return {'uid': UIDS[coin], 'ctr': f'{counter:08x}', 'cmac': 'VALID'}

def main():
    with TemporaryDirectory(prefix='sticker-ui-') as directory:
        app = create_app(str(Path(directory)/'keys.csv'), str(Path(directory)/'game.db'))
        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        app.key_manager = SignedKeys()
        app.sticker_service.rng = FixedRandom(1)
        with app.test_client() as client:
            for coin in UIDS:
                assert client.get('/api/flip', query_string=credentials(coin, 1)).status_code == 200
        app.sticker_service.rng = FixedRandom()
        a_stake = app.sticker_service.award_flip('A', 'seed-a', 1)['drop']['id']
        app.sticker_service.rng = FixedRandom(index=1)
        b_stake = app.sticker_service.award_flip('B', 'seed-b', 1)['drop']['id']
        app.sticker_service.rng = FixedRandom()
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f'http://127.0.0.1:{server.server_port}'
        errors = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, executable_path=os.environ.get("CHROMIUM_PATH"))
                context = browser.new_context(viewport={'width':390, 'height':844}, is_mobile=True, has_touch=True)
                context.set_default_timeout(10000)
                pages = {coin:context.new_page() for coin in UIDS}
                for page in pages.values():
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('dialog', lambda dialog: dialog.accept())
                a, b = pages['A'], pages['B']
                a.goto(origin)
                a.get_by_role('button', name='Sticker Book', exact=True).click()
                expect(a.locator('#StickerBook')).to_be_visible()
                expect(a.locator('#sticker-lore')).not_to_be_empty()
                expect(a.locator('#sticker-progress')).to_contain_text('Tap a coin')
                expect(a.locator('.sticker-card')).to_have_count(0)
                expect(a.locator('#RecentFlips')).not_to_be_visible()
                a.get_by_role('button', name='Leaderboard', exact=True).click()
                expect(a.locator('#StickerBook')).not_to_be_visible()
                a.goto(origin+'/?'+urlencode(credentials('A',2)))
                expect(a.locator('#sticker-reveal')).to_contain_text('Sticker found:')
                expect(a.locator('.sticker-family')).to_have_count(1)
                expect(a.locator('.sticker-card')).to_have_count(1)
                expect(a.locator('.sticker-meta')).to_contain_text('2 owned')
                expect(a.locator('.sticker-meta')).to_contain_text('Level 1')
                app.sticker_service.rng = FixedRandom(1)
                b.goto(origin+'/?'+urlencode(credentials('B',2)))
                expect(b.locator('.sticker-family')).to_have_count(1)
                expect(b.locator('.sticker-card')).to_have_count(1)
                def refresh(page):
                    page.evaluate('() => CoinStickers.refresh(true)')
                def offer(sticker_id):
                    refresh(a)
                    if a.locator('#fanfare-overlay').is_visible():
                        a.locator('#fanfare-overlay').click(position={'x':10,'y':10})
                    a.locator('#start-flipoff-btn').click()
                    a.locator('label.opponent-option').filter(has=a.locator('input[value="B"]')).first.click()
                    a.locator('.flip-count-btn').first.click()
                    if not a.locator("details.wager-panel").evaluate("e=>e.open"):
                        a.locator("details.wager-panel summary").click()
                    choice = a.locator('#wager-create-options label.sticker-choice').filter(has=a.locator('input:not([value=""])')).first
                    sticker_id = choice.locator('input').input_value()
                    choice.click()
                    a.locator('#challenge-submit').click()
                    expect(a.locator('#wager-active')).to_contain_text('Waiting for the opponent')
                    refresh(b)
                    expect(b.locator('#wager-active')).to_contain_text('A offers')
                    return sticker_id
                a_stake = offer(a_stake)
                expect(a.locator('#sticker-album')).to_contain_text('1 locked in wager')
                assert app.flip_off_service.get_active_challenge('A')['wager_status'] == 'awaiting_acceptance'
                b.locator('#wager-accept-form label.sticker-choice').filter(has=b.locator(f'input[value="{b_stake}"]')).click()
                expect(b.locator('#wager-review')).to_contain_text('you may lose this copy')
                b.locator('#wager-accept-button').click()
                expect(b.locator('#wager-active')).to_contain_text('Both stickers are locked')
                expect(b.locator('#sticker-album')).to_contain_text('1 locked in wager')
                # Both the accept CTA and yield must remain finger-sized.
                sizes = b.locator('.yield-btn').evaluate_all('(els)=>els.map(e=>e.getBoundingClientRect().height)')
                assert sizes and min(sizes) >= 44, sizes
                b.locator('.yield-btn').first.click()
                expect(b.locator('#wager-active')).to_contain_text('winner received both')
                refresh(a)
                assert {a_stake,b_stake} <= {s['id'] for s in app.sticker_service.collection('A')}
                assert not app.sticker_service.collection('B')
                a.wait_for_timeout(3500)
                if a.locator('#fanfare-overlay').is_visible():
                    a.locator('#fanfare-overlay').click(position={'x':10,'y':10})
                a.wait_for_timeout(3500)
                expect(a.locator('#fanfare-overlay')).not_to_be_visible()
                # Decline and creator cancellation, through actual controls.
                a_stake = offer(a_stake)
                b.locator('#wager-cancel').click()
                expect(b.locator('#wager-active')).to_contain_text('returned')
                refresh(a)
                assert all(s['locked_challenge_id'] is None for s in app.sticker_service.collection('A'))
                a_stake = offer(a_stake)
                a.locator('#wager-cancel').click()
                expect(a.locator('#wager-active')).to_contain_text('returned')
                assert all(s['locked_challenge_id'] is None for s in app.sticker_service.collection('A'))
                expect(a.locator('#flipoff-status-msg')).not_to_contain_text('Waiting for your opponent')
                expect(a.locator('#start-flipoff-btn')).to_contain_text('Start Flip-Off')
                app.sticker_service.rng = FixedRandom()
                a.goto(origin+'/?'+urlencode(credentials('A',3)))
                expect(a.locator('#sticker-reveal')).to_contain_text('3 copies combined automatically:')
                assert any(s['level'] == 2 for s in app.sticker_service.collection('A'))
                a.get_by_role('button', name='Sticker Book', exact=True).click()
                expect(a.locator('#StickerBook')).to_be_visible()
                expect(a.locator('.sticker-meta').filter(has_text='Level 2')).to_have_count(1)
                a.locator('.sticker-family').first.locator('summary').click()
                assert a.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal overflow'
                controls = a.locator('.sticker-family summary, .sticker-choice, #start-flipoff-btn, .flip-count-btn, #challenge-submit').evaluate_all('(els)=>els.filter(e=>e.getClientRects().length).map(e=>({name:e.textContent.trim(),height:e.getBoundingClientRect().height}))')
                assert all(c['height'] >= 44 for c in controls), controls
                assert not errors, errors
                output=Path('build/collectables-mobile.png')
                output.parent.mkdir(exist_ok=True)
                expect(a.locator('#outcome-text')).to_have_text(' HEADS ')
                a.wait_for_timeout(1500)  # Allow the existing header reveal animation to settle.
                a.screenshot(path=str(output),full_page=True)
                browser.close()
                print(f'PASS: mobile owned-only tabbed album and no-tap season description, drop/evolution reveals, exact wager consent, locks, yield settlement, decline/cancel, controls and no JS errors. Screenshot: {output}')
        finally:
            server.shutdown()
            thread.join(timeout=5)

if __name__ == '__main__':
    main()
