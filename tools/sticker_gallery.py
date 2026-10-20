"""Serve the clan and Rangers sticker cards locally as rendered HTML with pack switching."""

import argparse
import json
import os
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "game_server/src/game_server"
BUILD = ROOT / "build"
TARGET_ROSTER_PATH = ROOT / "tools/target_roster.json"
_TARGET_LOOKUP = {}
if TARGET_ROSTER_PATH.exists():
    try:
        _TARGET_LOOKUP = {p["id"]: p for p in json.loads(TARGET_ROSTER_PATH.read_text(encoding="utf-8"))}
    except Exception:
        pass

import sys
sys.path.insert(0, str(ROOT / "tools"))
try:
    from rangers_flair import get_image_flair_html, format_stats_ribbon, get_position_display
except ImportError:
    get_image_flair_html = lambda p, level=1: ""
    format_stats_ribbon = lambda p: ""
    get_position_display = lambda pos: ""

_CATALOG_CACHE = {}


def get_catalog(pack_name: str) -> dict:
    """Load and cache pack catalog by name."""
    if pack_name not in _CATALOG_CACHE:
        filename = 'sticker_catalog_rangers.json' if pack_name == 'rangers-history' else 'sticker_catalog.json'
        _CATALOG_CACHE[pack_name] = json.loads((SERVER / filename).read_text(encoding='utf-8'))
    return _CATALOG_CACHE[pack_name]


def artwork(family: dict, form: dict) -> str:
    """Use the same explicit image references as the coin's sticker book."""
    return form.get('image') or f'/static/stickers/{family["id"]}-{form["level"]}.webp'


def count_available(pack_name: str) -> int:
    """Count how many card families in a pack have complete artwork on disk."""
    cat = get_catalog(pack_name)
    return sum(
        1 for clan in cat["families"]
        if all((SERVER / artwork(clan, form).lstrip('/')).is_file() for form in clan['forms'])
    )


def gallery(catalog: dict, active_pack: str = 'rangers-history') -> bytes:
    """Render each clan's three forms with their original illustrations and lore."""
    sections = []
    available = 0
    for clan in catalog["families"]:
        if not all((SERVER / artwork(clan, form).lstrip('/')).is_file() for form in clan['forms']):
            continue
        available += 1
        cards = []
        player = clan.get("player", {})
        is_rangers = active_pack == "rangers-history"
        stats_ribbon = format_stats_ribbon(player) if is_rangers else ""
        pos_tenure = (
            f'<div class="card-player-pos-tenure">{escape(get_position_display(player.get("positions", [])))} · {escape(player.get("tenure", ""))}</div>'
            if is_rangers and (player.get("positions") or player.get("tenure")) else ""
        )

        for form in clan["forms"]:
            filename = artwork(clan, form)
            lvl = form["level"]
            treatment_name = form.get("treatment") or f"Form {lvl}"
            stars = "⭐" * lvl
            badge_html = f'<div class="evolution-badge level-{lvl}">{stars} Level {lvl} · {escape(treatment_name)}</div>'
            tag_label = "FACT" if form.get("text_kind") == "fact" else "LORE"
            if lvl == 2:
                tag_label = "SPOTLIGHT " + tag_label
            elif lvl == 3:
                tag_label = "GARDEN GLOW " + tag_label

            image_flair = get_image_flair_html(player, level=lvl) if is_rangers else ""

            quote_box = (
                f'<div class="sticker-quote-box level-{lvl}">'
                f'<span class="quote-tag level-{lvl}">{tag_label}</span><br>'
                f'{escape(form["quote"])}</div>'
            )
            cards.append(
                f'<article class="sticker-card sticker-level-{lvl}">'
                f'{badge_html}'
                f'<div class="sticker-portrait"><a href="{filename}" target="_blank">'
                f'{image_flair}'
                f'<img loading="lazy" src="{filename}" alt="{escape(form["name"])}"></a></div>'
                f'<div class="card-title-row"><h3 class="card-player-name">{escape(form["name"])}</h3></div>'
                f'{pos_tenure}'
                f'{stats_ribbon}'
                f'{quote_box}</article>'
            )
        target_info = _TARGET_LOOKUP.get(clan["id"])
        cups = target_info.get("championships", []) if target_info else []
        is_curr = target_info.get("is_current", False) if target_info else False

        badges = []
        if cups:
            badges.append(f'<small style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:700;border:1px solid #fde68a">🏆 {" & ".join(cups)} Cup</small>')
        if is_curr:
            badges.append('<small style="background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:700;border:1px solid #bfdbfe">⚡ Current Roster</small>')
        badge_html_line = ' '.join(badges)

        tags = []
        if cups: tags.append('champions')
        if is_curr: tags.append('current')
        if cups or is_curr: tags.append('target')
        for yr in cups: tags.append(yr)
        data_tags = ','.join(tags)

        sections.append(
            f'<section data-name="{escape(clan["name"].casefold())}" data-tags="{escape(data_tags)}"'
            f'{" hidden" if available > 24 else ""}><h2>{escape(clan["name"])} <small>{escape(clan["rarity"].title())}</small> {badge_html_line}</h2>'
            f'<p>{escape(clan["look"])}</p><div class="forms">{"".join(cards)}</div></section>'
        )

    twelve_active = ' active' if active_pack == 'twelve-clans' else ''
    rangers_active = ' active' if active_pack == 'rangers-history' else ''
    twelve_count = count_available('twelve-clans')
    rangers_count = count_available('rangers-history')

    filter_bar = ''
    if active_pack == 'rangers-history':
        filter_bar = (
            '<div class="roster-filter-bar">'
            '<span style="font-weight:600;font-size:0.9rem;align-self:center">Roster:</span>'
            '<button type="button" class="filter-btn active" onclick="setFilter(\'all\')">All Available</button>'
            '<button type="button" class="filter-btn" onclick="setFilter(\'target\')">🎯 Target Roster (143)</button>'
            '<button type="button" class="filter-btn" onclick="setFilter(\'champions\')">🏆 Championship Teams (82)</button>'
            '<button type="button" class="filter-btn" onclick="setFilter(\'current\')">⚡ Current 2025–2026 (61)</button>'
            '<button type="button" class="filter-btn" onclick="setFilter(\'1994\')">1994 Cup</button>'
            '<button type="button" class="filter-btn" onclick="setFilter(\'1940\')">1940 Cup</button>'
            '<button type="button" class="filter-btn" onclick="setFilter(\'1933\')">1933 Cup</button>'
            '<button type="button" class="filter-btn" onclick="setFilter(\'1928\')">1928 Cup</button>'
            '</div>'
        )

    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<link rel="stylesheet" href="/static/stickers.css">'
        f'<title>{escape(catalog["pack_name"])} — Rendered Cards</title>'
        '<style>body{margin:0;background:#f3eee2;color:#302b22;font:16px/1.6 system-ui}'
        'main{max-width:1180px;margin:auto;padding:24px}h1{font-size:2.6rem;margin-bottom:0}'
        'section{margin:40px 0}h2 small{font-size:.9rem;margin-left:12px;color:#6b5635}'
        '.forms{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}'
        'article{background:#fffdf6;border:1px solid #d9cdb5;border-radius:16px;padding:16px}'
        'img{display:block;width:100%;aspect-ratio:1;object-fit:contain;border-radius:10px}'
        'h3{margin-bottom:0}article p{margin:4px 0}blockquote{margin:12px 0;color:#66543c}'
        '[hidden]{display:none!important}button,input{min-height:44px;font:inherit;max-width:100%;box-sizing:border-box}nav{display:flex;gap:12px;align-items:center;flex-wrap:wrap}'
        '.pack-nav{background:#e9dfcd;padding:12px 16px;border-radius:12px;margin-bottom:20px;border:1px solid #d5c8af}'
        '.pack-tab{padding:8px 16px;border-radius:8px;text-decoration:none;font-weight:600;color:#5a472c;background:#fffdf6;border:1px solid #c9bda5;transition:all .15s}'
        '.pack-tab:hover{background:#faf4e7;border-color:#8e744d}'
        '.pack-tab.active{background:#234a75;color:#fff;border-color:#173454}'
        '.roster-filter-bar{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0;align-items:center}'
        '.filter-btn{padding:6px 14px;border-radius:8px;font-size:0.85rem;font-weight:600;background:#fffdf6;border:1px solid #c9bda5;cursor:pointer;color:#4a3b25;transition:all .15s}'
        '.filter-btn:hover{background:#faf4e7;border-color:#8e744d}'
        '.filter-btn.active{background:#234a75;color:#fff;border-color:#173454}'
        '@media(max-width:700px){.forms{grid-template-columns:1fr}main{padding:16px}}'
        '</style><main>'
        '<nav class="pack-nav">'
        '<span style="font-weight:600;margin-right:4px">Select Pack:</span>'
        f'<a href="/?pack=rangers-history" class="pack-tab{rangers_active}">🏒 Broadway Blueshirts: Rangers History ({rangers_count} available)</a>'
        f'<a href="/?pack=twelve-clans" class="pack-tab{twelve_active}">🛡️ The Twelve Clans ({twelve_count} available)</a>'
        '</nav>'
        f'<h1>{escape(catalog["pack_name"])}</h1><p>{available} of {len(catalog["families"])} families with artwork · {available*3} level examples · Click an image to enlarge.</p>'
        f'<p>{escape(catalog["narrative"])}</p>'
        f'{filter_bar}'
        '<label>Search artwork <input id="search" type="search" placeholder="Type name (e.g. Messier, Leetch, Gretzky, Lundqvist)..."></label>'
        '<nav><button id="previous" type="button">Previous</button><span id="pages" role="status"></span><button id="next" type="button">Next</button></nav>'
        f'{"".join(sections)}</main>'
        '<script>const sections=[...document.querySelectorAll("section[data-name]")];let page=0;let activeFilter="all";'
        'function setFilter(f){activeFilter=f;document.querySelectorAll(".filter-btn").forEach(b=>b.classList.toggle("active",b.getAttribute("onclick").includes(`\'${f}\'`)));page=0;render();}'
        'function render(){const query=document.getElementById("search").value.toLocaleLowerCase();'
        'const matches=sections.filter(s=>{'
        'const tags=(s.dataset.tags||"").split(",");'
        'const matchesSearch=s.dataset.name.includes(query)||(s.dataset.tags||"").includes(query);'
        'let matchesFilter=true;'
        'if(activeFilter!=="all")matchesFilter=tags.includes(activeFilter);'
        'return matchesSearch&&matchesFilter;});'
        'const total=Math.max(1,Math.ceil(matches.length/24));page=Math.min(page,total-1);sections.forEach(s=>s.hidden=true);matches.slice(page*24,(page+1)*24).forEach(s=>s.hidden=false);'
        'document.getElementById("pages").textContent=`Page ${page+1} of ${total} · ${matches.length} matches`;document.getElementById("previous").disabled=page===0;document.getElementById("next").disabled=page===total-1;}'
        'document.getElementById("search").addEventListener("input",()=>{page=0;render()});document.getElementById("previous").onclick=()=>{page--;render()};document.getElementById("next").onclick=()=>{page++;render()};render();</script></html>'
    ).encode('utf-8')


def sheets_page() -> bytes:
    # Deprecated: Redirect legacy /sheets requests to the Rangers cards gallery
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta http-equiv="refresh" content="0; url=/?pack=rangers-history">'
        '<title>Redirecting...</title><body><p>Redirecting to <a href="/?pack=rangers-history">Rendered HTML Cards Gallery</a>...</p></body></html>'
    ).encode('utf-8')


class GalleryHandler(BaseHTTPRequestHandler):
    """Expose the rendered HTML sticker cards and catalog artwork files."""

    def do_GET(self) -> None:
        split_url = urlsplit(self.path)
        path = split_url.path
        query = parse_qs(split_url.query)

        default_pack = os.environ.get('STICKER_PACK', 'rangers-history')
        pack = query.get('pack', [default_pack])[0]
        if pack not in ('twelve-clans', 'rangers-history'):
            pack = default_pack

        if path in ("/", "/gallery"):
            catalog = get_catalog(pack)
            content, mime = gallery(catalog, active_pack=pack), "text/html; charset=utf-8"
        elif path == "/sheets":
            content, mime = sheets_page(), "text/html; charset=utf-8"
        else:
            allowed = {}
            for p in ('twelve-clans', 'rangers-history'):
                cat = get_catalog(p)
                for clan in cat["families"]:
                    for form in clan["forms"]:
                        ref = artwork(clan, form)
                        allowed[ref] = SERVER / ref.lstrip('/')
                        if p == 'twelve-clans' and ref.endswith('.webp'):
                            allowed[ref.replace('/static/stickers/', '/art/')] = SERVER / ref.lstrip('/')

            allowed['/static/stickers.css'] = SERVER / 'static/stickers.css'

            if path not in allowed or not allowed[path].is_file():
                self.send_error(404)
                return

            content = allowed[path].read_bytes()
            if path.endswith('.css'):
                mime = 'text/css'
            elif path.endswith('.webp'):
                mime = 'image/webp'
            elif path.endswith('.jpg') or path.endswith('.jpeg'):
                mime = 'image/jpeg'
            elif path.endswith('.png'):
                mime = 'image/png'
            else:
                mime = 'application/octet-stream'

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
