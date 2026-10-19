"""Validate actual-art gallery pagination, references and file access boundaries."""
import os
from threading import Thread
from http.server import ThreadingHTTPServer

from playwright.sync_api import expect, sync_playwright
from sticker_gallery import GalleryHandler


def main() -> None:
    server = ThreadingHTTPServer(('127.0.0.1', 0), GalleryHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH'))
            page = browser.new_page(viewport={'width':390,'height':844})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(origin)
            assert 0 < page.locator('section:visible').count() <= 24
            if page.locator('#next').is_enabled():
                page.locator('#next').click()
                expect(page.locator('#pages')).to_contain_text('Page 2')
                assert page.locator('section:visible').count() <= 24
            page.locator('#search').fill('gretzky')
            expect(page.locator('section:visible')).to_have_count(1)
            expect(page.locator('section:visible img')).to_have_count(3)
            page.locator('section:visible').scroll_into_view_if_needed()
            page.wait_for_function('Array.from(document.querySelectorAll("section:not([hidden]) img")).every(i=>i.complete && i.naturalWidth>=512)')
            assert page.locator('section:visible img').first.get_attribute('loading') == 'lazy'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.request.get(origin+'/data/app.db').status == 404
            assert page.request.get(origin+'/static/stickers/unknown.webp').status == 404
            page.locator('#search').fill('No matching player')
            expect(page.locator('section:visible')).to_have_count(0)
            expect(page.locator('#pages')).to_contain_text('0 matches')
            assert not errors, errors
            browser.close()
        print('PASS: actual 512px art, lazy loading, 24-family pages/search, mobile width and known-files-only access')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
