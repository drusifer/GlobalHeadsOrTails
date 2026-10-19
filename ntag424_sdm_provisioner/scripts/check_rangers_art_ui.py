"""Review six actual portraits in all three production card frames, using a temp app."""
import argparse
import json
import logging
import os
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.parse import urlencode

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from ntag424_sdm_provisioner.server.app import create_app
from check_sticker_ui import FixedRandom, SignedKeys, credentials
from sticker_pack_fixtures import select_fixture_pack


PLAYERS = [8444933, 8448095, 8445529, 8447400, 8468685, 8478550]


def capture(page, output: Path, mobile: bool) -> dict:
    """Capture every real owned card and prove shared images and distinct frames load."""
    page.get_by_role('button', name='Sticker Book', exact=True).click()
    page.locator('#sticker-pack').select_option('rangers-history')
    expect(page.locator('.sticker-family')).to_have_count(6)
    expect(page.locator('.sticker-card')).to_have_count(18)
    expect(page.locator('.sticker-art-note')).to_have_count(18)
    expect(page.locator('.sticker-art-note').first).to_contain_text('facial likeness unverified')
    expect(page.locator('#sticker-progress')).to_contain_text('18/3486 forms')
    page.locator('.sticker-family').evaluate_all('(els)=>els.forEach(el=>el.open=true)')
    # Review all actual assets; ordinary user UI retains lazy loading.
    page.locator('.sticker-card img').evaluate_all('(els)=>els.forEach(el=>el.loading="eager")')
    page.wait_for_function('Array.from(document.querySelectorAll(".sticker-card img")).every(img=>img.complete && img.naturalWidth>=512 && img.naturalHeight>=512)')
    images = page.locator('.sticker-card img').evaluate_all('(els)=>els.map(img=>({src:img.getAttribute("src"),width:img.naturalWidth,height:img.naturalHeight}))')
    assert len({image['src'] for image in images}) == 6, images
    frame_styles = page.locator('.sticker-family').first.locator('.sticker-portrait').evaluate_all('(els)=>els.map(el=>{const s=getComputedStyle(el);return [s.borderStyle,s.borderWidth,s.borderRadius,s.outlineStyle].join("|")})')
    assert len(set(frame_styles)) == 3, frame_styles
    for player_id in PLAYERS:
        family = page.locator(f'.sticker-family[data-family="nyr-{player_id}"]')
        expect(family.locator('.sticker-card')).to_have_count(3)
        for level in (1, 2, 3):
            expect(family.locator(f'.sticker-level-{level} .sticker-meta')).to_contain_text(f'Level {level}')
        # Include one actual expanded stats/fact/source panel in each player view.
        family.locator('.sticker-player-details').first.evaluate('(el)=>el.open=true')
        expect(family.locator('.sticker-player-details').first).to_contain_text('Fact:')
        expect(family.locator('.sticker-player-details').first).to_contain_text('Original cartoon flavor:')
        assert family.locator('.sticker-player-details a').first.get_attribute('href').startswith('https://')
        family.screenshot(path=str(output/f'nyr-{player_id}-{"mobile" if mobile else "desktop"}.png'))
    patrick = page.locator('.sticker-family[data-family="nyr-8448095"]')
    expect(patrick).to_contain_text('regular season · skater')
    expect(patrick).to_contain_text('playoffs · goalie')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal overflow'
    page.locator('#StickerBook').screenshot(path=str(output/f'overview-{"mobile" if mobile else "desktop"}.png'))
    return {'cards': 18, 'portraits': 6, 'images': images, 'frame_styles': frame_styles}


class WeightedGretzkyRandom:
    """Repeat deterministic successful drop and independently computed player interval."""
    def __init__(self, service):
        players = [family for family in service.catalog['families'] if family['pack_id']=='rangers-history']
        weights = {'common':8,'uncommon':4,'rare':2,'legendary':1}
        total = sum(weights[family['rarity']] for family in players)
        before = 0
        for family in players:
            if family['id']=='nyr-8447400':
                break
            before += weights[family['rarity']]
        self.roll = (before+.5)/total
        self.calls = 0

    def random(self):
        value = 0 if self.calls%2==0 else self.roll
        self.calls += 1
        return value


def active_season_checks(page, app, origin: str, output: Path) -> dict:
    """Exercise actual temporary Rangers defaults, real/test awards, replay and archive."""
    page.goto(origin)
    page.get_by_role('button',name='Sticker Book',exact=True).click()
    expect(page.locator('#sticker-pack')).to_have_value('rangers-history')
    expect(page.locator('#sticker-title')).to_contain_text('Broadway Blueshirts')
    expect(page.locator('#sticker-lore')).to_contain_text('1,162 players')
    expect(page.locator('.sticker-card')).to_have_count(0)
    expect(page.locator('#sticker-search')).to_be_disabled()
    page.locator('#StickerBook').screenshot(path=str(output/'active-no-tap-mobile.png'))
    app.sticker_service.rng = WeightedGretzkyRandom(app.sticker_service)
    params = credentials('B',1)
    page.goto(origin+'/?'+urlencode(params))
    expect(page.locator('#sticker-reveal')).to_contain_text('Wayne Gretzky')
    page.get_by_role('button',name='Sticker Book',exact=True).click()
    expect(page.locator('#sticker-pack')).to_have_value('rangers-history')
    expect(page.locator('.sticker-family')).to_have_count(1)
    expect(page.locator('.sticker-meta')).to_contain_text('1 owned')
    expect(page.locator('#sticker-progress')).to_contain_text('B · 1/3486')
    page.locator('.sticker-family').evaluate('(el)=>el.open=true')
    page.wait_for_function('document.querySelector(".sticker-card img").naturalWidth>=512')
    assert page.locator('.sticker-card img').get_attribute('src') == '/static/stickers/rangers-history/nyr-8447400.webp'
    assert page.request.get(origin+'/api/flip',params=params).status == 409
    assert len(app.sticker_service.collection('B')) == 1
    page.locator('#StickerBook').screenshot(path=str(output/'active-real-drop-mobile.png'))
    test_params = {**credentials('B',2),'drew_test_outcome':'heads'}
    page.goto(origin+'/?'+urlencode(test_params))
    expect(page.locator('#sticker-reveal')).to_contain_text('Wayne Gretzky')
    page.get_by_role('button',name='Sticker Book',exact=True).click()
    expect(page.locator('.sticker-meta')).to_contain_text('2 owned')
    expect(page.locator('#sticker-odds')).to_contain_text('Test mode')
    assert len(app.sticker_service.collection('B')) == 2
    first_test = page.request.get(origin+'/api/flip',params=test_params).json()['sticker_award']
    second_test = page.request.get(origin+'/api/flip',params=test_params).json()['sticker_award']
    assert first_test == second_test
    assert first_test['drop']['family_id'] == 'nyr-8447400'
    assert len(app.sticker_service.collection('B')) == 2
    app.sticker_service.rng = FixedRandom(1)
    page.goto(origin+'/?'+urlencode(credentials('A',3)))
    page.get_by_role('button',name='Sticker Book',exact=True).click()
    expect(page.locator('#sticker-pack')).to_have_value('rangers-history')
    expect(page.locator('.sticker-card')).to_have_count(18)
    page.locator('#sticker-pack').select_option('twelve-clans')
    expect(page.locator('#sticker-title')).to_have_text('The Twelve Clans')
    expect(page.locator('.sticker-family')).to_have_count(1)
    expect(page.locator('.sticker-card')).to_have_count(1)
    page.locator('.sticker-family').evaluate('(el)=>el.open=true')
    page.wait_for_function('document.querySelector(".sticker-card img").naturalWidth>=512')
    assert page.locator('.sticker-card img').get_attribute('src') == '/static/stickers/hearthshield-compact-1.webp'
    page.locator('#StickerBook').screenshot(path=str(output/'active-legacy-archive-mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    return {'active_pack_id':'rangers-history','seeded_rangers_cards':18,'normal_drop':'nyr-8447400',
            'test_drop':'nyr-8447400','replay_copy_count':2,'legacy_archive_cards':1,'no_tap_cards':0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--active-rangers',action='store_true',help='Test temporary Rangers activation without modifying production registry')
    args = parser.parse_args()
    active = 'rangers-history' if args.active_rangers else 'twelve-clans'
    output = Path('build/rangers-active-ui' if args.active_rangers else 'build/rangers-art-ui')
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='rangers-art-ui-') as directory:
        app = create_app(str(Path(directory)/'keys.csv'), str(Path(directory)/'game.db'))
        select_fixture_pack(app.sticker_service, directory, active)
        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        app.key_manager = SignedKeys()
        app.sticker_service.rng = FixedRandom(1)  # Page tap may persist a no-drop, never new copies.
        assert app.sticker_service.catalog['active_pack_id'] == active
        with sqlite3.connect(app.sticker_service.db_path) as conn:
            for player_id in PLAYERS:
                for level in (1, 2, 3):
                    app.sticker_service._insert(conn, 'A', f'nyr-{player_id}', level)
            if args.active_rangers:
                app.sticker_service._insert(conn,'A','hearthshield-compact',1)
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        errors = []
        results = {}
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH'))
                for mobile in (True, False):
                    context = browser.new_context(viewport={'width': 390 if mobile else 1280, 'height': 844 if mobile else 900}, is_mobile=mobile, has_touch=mobile)
                    context.set_default_timeout(15000)
                    page = context.new_page()
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    # Freeze only background polling; call real refresh before snapshots.
                    page.add_init_script('window.setInterval=()=>0')
                    origin = f'http://127.0.0.1:{server.server_port}'
                    page.goto(origin+'/?'+urlencode(credentials('A', 1 if mobile else 2)))
                    page.evaluate('()=>CoinStickers.refresh(true)')
                    expect(page.locator('#sticker-pack')).to_have_value(active)
                    results['mobile' if mobile else 'desktop'] = capture(page, output, mobile)
                    context.close()
                if args.active_rangers:
                    context = browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
                    context.set_default_timeout(15000)
                    page = context.new_page()
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    page.add_init_script('window.setInterval=()=>0')
                    results['active_season'] = active_season_checks(page,app,origin,output)
                    context.close()
                browser.close()
            assert not errors, errors
            assert len(app.sticker_service.collection('A')) == (19 if args.active_rangers else 18)
            with sqlite3.connect(app.sticker_service.db_path) as conn:
                assert all(json.loads(row[0])['drop'] is None for row in conn.execute("SELECT result FROM sticker_awards WHERE coin_name='A'"))
            (output/'review.json').write_text(json.dumps(results, indent=2)+'\n')
            print(f'PASS:18 actual owned cards,6 decoded512px portraits,3 structural frames, role/fact/source details, no overflow/JS errors. Active-Rangers award/archive mode: {args.active_rangers}. Screenshots: {output}')
        finally:
            server.shutdown()
            thread.join(timeout=5)


if __name__ == '__main__':
    main()
