"""Cache official NHL portrait references separately from generated sticker art."""
import json
import os
import sys
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def export_index() -> None:
    """Retain portable source records without shipping cached reference photographs."""
    records = [json.loads(path.read_text()) for path in sorted((ROOT/'build/rangers-art/references').glob('*.json'))]
    if len(records) != 1162 or len({record['id'] for record in records}) != 1162:
        raise ValueError('Complete 1162-player reference audit required')
    (ROOT/'agents/oracle.docs/rangers_art_sources.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n')
    print(f'Exported {len(records)} reference records; downloaded photos remain candidates for visual review')


def download(url: str) -> bytes:
    """Fetch a public reference with an explicit timeout and identifiable client."""
    with urlopen(Request(url, headers={'User-Agent': 'RangersStickerReferenceAudit/1.0'}), timeout=30) as response:
        return response.read()


def main() -> None:
    """Record each selected player's source and actual downloaded reference status."""
    from PIL import Image
    catalog = json.loads((ROOT/'game_server/src/game_server/sticker_catalog_rangers.json').read_text())
    families = {family['id']:family for family in catalog['families']}
    selection = os.environ.get('ART_IDS', '')
    ids = list(families) if selection == 'all' else selection.split(',')
    if not ids or any(identity not in families for identity in ids):
        raise ValueError('Explicit valid Rangers ART_IDS required for reference audit')
    destination = ROOT/'build/rangers-art/references'
    destination.mkdir(parents=True, exist_ok=True)
    index = ROOT/'agents/oracle.docs/rangers_art_sources.json'
    overrides = {record['id']:record for record in json.loads(index.read_text()) if record.get('source_url')} if index.exists() else {}
    def audit(identity: str) -> None:
        sidecar = destination/f'{identity}.json'
        if sidecar.is_file() and os.environ.get('ART_REFRESH') != '1':
            print(identity, 'cached')
            return
        source = f"https://api-web.nhle.com/v1/player/{families[identity]['player']['player_id']}/landing"
        record = {'id':identity, 'name':families[identity]['name'], 'landing_url':source,
                  'fetched_at':datetime.now(timezone.utc).isoformat(), 'status':'unavailable'}
        try:
            landing = json.loads(download(source))
            url = landing.get('headshot', '')
            record['image_url'] = url
            if not url.startswith('https://assets.nhle.com/'):
                raise ValueError('No official portrait URL')
            image = destination/f'{identity}.png'
            season = families[identity]['player']['last_season']
            era_url = f'https://assets.nhle.com/mugs/nhl/{season}/NYR/{families[identity]["player"]["player_id"]}.png'
            if identity in overrides:
                override = overrides[identity]
                data = download(override['image_url'])
                record.update({key:override[key] for key in ('image_url','source_url','reference_scope')})
            else:
                try:
                    data = download(era_url)
                    record.update(image_url=era_url, reference_scope='Requested Rangers season; visually verify photo era before use')
                except Exception:
                    data = download(url)
                    record['reference_scope'] = 'Facial identity only; visually verify and adapt age/gear to documented Rangers tenure'
            image.write_bytes(data)
            with Image.open(image) as portrait:
                portrait.load()
                if min(portrait.size) < 100:
                    raise ValueError('Reference image too small')
                colors = portrait.convert('RGB').getcolors(portrait.width*portrait.height)
                dominant = sum(sorted((count for count, _ in colors), reverse=True)[:3])/(portrait.width*portrait.height)
                if len(colors) < 16 or dominant > .9:
                    image.unlink()
                    raise ValueError('Generic silhouette is not a player portrait')
            record['status'] = 'downloaded_for_visual_verification'
        except Exception as error:
            record['error'] = str(error)
        (destination/f'{identity}.json').write_text(json.dumps(record, indent=2)+'\n')
        print(identity, record['status'])
    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(audit, ids))


if __name__ == '__main__':
    export_index() if '--export' in sys.argv else main()
