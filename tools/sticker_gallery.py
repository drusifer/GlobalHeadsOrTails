"""Serve the clan artwork locally without exposing project files or runtime data."""

import argparse
import json
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

SERVER = Path(__file__).resolve().parents[1] / "ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/server"


def gallery(catalog: dict) -> bytes:
    """Render each clan's three forms with their original illustrations and lore."""
    sections = []
    for clan in catalog["families"]:
        cards = []
        for form in clan["forms"]:
            filename = f'{clan["id"]}-{form["level"]}.webp'
            cards.append(
                f'<article><a href="/art/{filename}" target="_blank">'
                f'<img src="/art/{filename}" alt="{escape(form["name"])}"></a>'
                f'<h3>{escape(form["name"])}</h3><p>Level {form["level"]}</p>'
                f'<blockquote>“{escape(form["quote"])}”</blockquote></article>'
            )
        sections.append(
            f'<section><h2>{escape(clan["name"])} <small>{escape(clan["rarity"].title())}</small></h2>'
            f'<p>{escape(clan["look"])}</p><div class="forms">{"".join(cards)}</div></section>'
        )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{escape(catalog["pack_name"])} — Artwork</title>'
        '<style>body{margin:0;background:#f3eee2;color:#302b22;font:16px/1.6 system-ui}'
        'main{max-width:1180px;margin:auto;padding:24px}h1{font-size:2.6rem;margin-bottom:0}'
        'section{margin:40px 0}h2 small{font-size:.9rem;margin-left:12px;color:#6b5635}'
        '.forms{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}'
        'article{background:#fffdf6;border:1px solid #d9cdb5;border-radius:16px;padding:16px}'
        'img{display:block;width:100%;aspect-ratio:1;object-fit:contain;border-radius:10px}'
        'h3{margin-bottom:0}article p{margin:4px 0}blockquote{margin:12px 0;color:#66543c}'
        '@media(max-width:700px){.forms{grid-template-columns:1fr}main{padding:16px}}'
        '</style><main>'
        f'<h1>{escape(catalog["pack_name"])}</h1><p>12 clans · 36 stickers · Click an image to enlarge.</p>'
        f'<p>{escape(catalog["narrative"])}</p>{"".join(sections)}</main></html>'
    ).encode()


class GalleryHandler(BaseHTTPRequestHandler):
    """Expose only the gallery and the catalog's known artwork files."""

    def do_GET(self) -> None:
        catalog = json.loads((SERVER / "sticker_catalog.json").read_text())
        path = urlsplit(self.path).path
        if path == "/":
            content, mime = gallery(catalog), "text/html; charset=utf-8"
        else:
            allowed = {
                f'/art/{clan["id"]}-{form["level"]}.webp': SERVER / "static/stickers" / f'{clan["id"]}-{form["level"]}.webp'
                for clan in catalog["families"] for form in clan["forms"]
            }
            if path not in allowed:
                self.send_error(404)
                return
            content, mime = allowed[path].read_bytes(), "image/webp"
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
