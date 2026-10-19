"""Serve the clan artwork locally without exposing project files or runtime data."""

import argparse
import json
import os
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

SERVER = Path(__file__).resolve().parents[1] / "game_server/src/game_server"
PACK = os.environ.get('STICKER_PACK', 'twelve-clans')
if PACK not in ('twelve-clans', 'rangers-history'):
    raise ValueError('Unknown STICKER_PACK')
CATALOG = SERVER / ('sticker_catalog_rangers.json' if PACK == 'rangers-history' else 'sticker_catalog.json')


def artwork(family: dict, form: dict) -> str:
    """Use the same explicit image references as the coin's sticker book."""
    return form.get('image') or f'/static/stickers/{family["id"]}-{form["level"]}.webp'


def gallery(catalog: dict) -> bytes:
    """Render each clan's three forms with their original illustrations and lore."""
    sections = []
    available = 0
    for clan in catalog["families"]:
        if not all((SERVER / artwork(clan, form).lstrip('/')).is_file() for form in clan['forms']):
            continue
        available += 1
        cards = []
        for form in clan["forms"]:
            filename = artwork(clan, form)
            cards.append(
                f'<article class="sticker-card sticker-level-{form["level"]}"><div class="sticker-portrait"><a href="{filename}" target="_blank">'
                f'<img loading="lazy" src="{filename}" alt="{escape(form["name"])}"></a></div>'
                f'<h3>{escape(form["name"])}</h3><p>Level {form["level"]}</p>'
                f'<blockquote>{"Fact: " if form.get("text_kind") == "fact" else "Lore: "}{escape(form["quote"])}</blockquote></article>'
            )
        sections.append(
            f'<section data-name="{escape(clan["name"].casefold())}"{" hidden" if available > 24 else ""}><h2>{escape(clan["name"])} <small>{escape(clan["rarity"].title())}</small></h2>'
            f'<p>{escape(clan["look"])}</p><div class="forms">{"".join(cards)}</div></section>'
        )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<link rel="stylesheet" href="/static/stickers.css">'
        f'<title>{escape(catalog["pack_name"])} — Artwork</title>'
        '<style>body{margin:0;background:#f3eee2;color:#302b22;font:16px/1.6 system-ui}'
        'main{max-width:1180px;margin:auto;padding:24px}h1{font-size:2.6rem;margin-bottom:0}'
        'section{margin:40px 0}h2 small{font-size:.9rem;margin-left:12px;color:#6b5635}'
        '.forms{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}'
        'article{background:#fffdf6;border:1px solid #d9cdb5;border-radius:16px;padding:16px}'
        'img{display:block;width:100%;aspect-ratio:1;object-fit:contain;border-radius:10px}'
        'h3{margin-bottom:0}article p{margin:4px 0}blockquote{margin:12px 0;color:#66543c}'
        '[hidden]{display:none!important}button,input{min-height:44px;font:inherit;max-width:100%;box-sizing:border-box}nav{display:flex;gap:12px;align-items:center;flex-wrap:wrap}'
        '@media(max-width:700px){.forms{grid-template-columns:1fr}main{padding:16px}}'
        '</style><main>'
        f'<h1>{escape(catalog["pack_name"])}</h1><p>{available} of {len(catalog["families"])} families with artwork · {available*3} level examples · Click an image to enlarge.</p>'
        f'<p>{escape(catalog["narrative"])}</p><label>Search artwork <input id="search" type="search"></label>'
        '<nav><button id="previous" type="button">Previous</button><span id="pages" role="status"></span><button id="next" type="button">Next</button></nav>'
        f'{"".join(sections)}</main>'
        '<script>const sections=[...document.querySelectorAll("section[data-name]")];let page=0;'
        'function render(){const matches=sections.filter(s=>s.dataset.name.includes(document.getElementById("search").value.toLocaleLowerCase()));'
        'const total=Math.max(1,Math.ceil(matches.length/24));page=Math.min(page,total-1);sections.forEach(s=>s.hidden=true);matches.slice(page*24,(page+1)*24).forEach(s=>s.hidden=false);'
        'document.getElementById("pages").textContent=`Page ${page+1} of ${total} · ${matches.length} matches`;document.getElementById("previous").disabled=page===0;document.getElementById("next").disabled=page===total-1;}'
        'document.getElementById("search").addEventListener("input",()=>{page=0;render()});document.getElementById("previous").onclick=()=>{page--;render()};document.getElementById("next").onclick=()=>{page++;render()};render();</script></html>'
    ).encode()


class GalleryHandler(BaseHTTPRequestHandler):
    """Expose only the gallery and the catalog's known artwork files."""

    catalog_data = None

    def do_GET(self) -> None:
        if GalleryHandler.catalog_data is None:
            GalleryHandler.catalog_data = json.loads(CATALOG.read_text())
        catalog = GalleryHandler.catalog_data
        path = urlsplit(self.path).path
        if path == "/":
            content, mime = gallery(catalog), "text/html; charset=utf-8"
        else:
            allowed = {
                artwork(clan, form): SERVER / artwork(clan, form).lstrip('/')
                for clan in catalog["families"] for form in clan["forms"]
            }
            allowed['/static/stickers.css'] = SERVER / 'static/stickers.css'
            if PACK == 'twelve-clans':
                allowed.update({key.replace('/static/stickers/', '/art/'): value
                                for key, value in list(allowed.items()) if key.endswith('.webp')})
            if path not in allowed or not allowed[path].is_file():
                self.send_error(404)
                return
            content = allowed[path].read_bytes()
            mime = 'text/css' if path.endswith('.css') else 'image/webp'
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with ThreadingHTTPServer((args.host, args.port), GalleryHandler) as server:
        print(f"Sticker gallery listening on http://{args.host}:{args.port}", flush=True)
        server.serve_forever()
