"""Require complete artwork before building, then verify the actual wheel payload."""
import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT/'src/ntag424_sdm_provisioner/server'
PREFIX = 'ntag424_sdm_provisioner/server/'
CATALOGS = {'sticker_catalog.json','sticker_catalog_rangers.json'}


def expected_assets() -> set:
    """Fail before a package build when any full-roster portrait is absent."""
    old = json.loads((SERVER/'sticker_catalog.json').read_text())
    new = json.loads((SERVER/'sticker_catalog_rangers.json').read_text())
    assert len(new['families']) == 1162
    assert len({family['id'] for family in new['families']}) == 1162
    assert sum(len(family['forms']) for family in new['families']) == 3486
    legacy = {f"static/stickers/{family['id']}-{form['level']}.webp" for family in old['families'] for form in family['forms']}
    rangers = set()
    for family in new['families']:
        expected = f"/static/stickers/rangers-history/{family['id']}.webp"
        assert {form['image'] for form in family['forms']} == {expected}
        assert {form['level'] for form in family['forms']} == {1,2,3}
        rangers.add(expected.lstrip('/'))
    assert len(legacy) == 36 and len(rangers) == 1162
    assets = legacy | rangers
    missing = sorted(path for path in assets if not (SERVER/path).is_file())
    assert not missing, f'Incomplete artwork: {len(missing)} missing assets; first missing: {missing[:5]}'
    return assets


def verify(wheel_path: Path, expected: set) -> None:
    """Compare the wheel's catalog/registry/static payload with the release source."""
    with ZipFile(wheel_path) as wheel:
        members = set(wheel.namelist())
        catalogs = {name[len(PREFIX):] for name in members if name.startswith(PREFIX+'sticker_catalog') and name.endswith('.json')}
        assert catalogs == CATALOGS, catalogs
        for relative in [*sorted(CATALOGS),'sticker_packs.json']:
            assert wheel.read(PREFIX+relative) == (SERVER/relative).read_bytes(), relative
        expected_static = expected | {str(path.relative_to(SERVER)) for path in (SERVER/'static').iterdir() if path.is_file() and path.suffix in {'.js','.css'}}
        actual_static = {name[len(PREFIX):] for name in members if name.startswith(PREFIX+'static/') and not name.endswith('/')}
        assert actual_static == expected_static, {'missing':sorted(expected_static-actual_static),'unexpected':sorted(actual_static-expected_static)}
        portrait_hashes = {}
        for relative in expected:
            with Image.open(BytesIO(wheel.read(PREFIX+relative))) as image:
                image.load()
                assert image.format == 'WEBP' and min(image.size) >= 512, relative
                if relative.startswith('static/stickers/rangers-history/'):
                    digest = hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()
                    assert digest not in portrait_hashes, f'Duplicate decoded portraits: {relative}, {portrait_hashes.get(digest)}'
                    portrait_hashes[digest] = relative
        assert PREFIX+'templates/index.html' in members
    print(f'PASS: {wheel_path.name}: exactly2catalogs+registry,36legacy+1162Rangers decoded WebPs,3486form refs and exact static payload.')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-only',action='store_true')
    parser.add_argument('--wheel-dir',type=Path,default=ROOT/'build/rangers-wheel')
    args = parser.parse_args()
    expected = expected_assets()
    if args.source_only:
        print('PASS: complete source artwork exists; local wheel build may proceed.')
        return
    wheels = sorted(args.wheel_dir.glob('*.whl'),key=lambda path:path.stat().st_mtime_ns)
    assert wheels, f'No wheel found in {args.wheel_dir}'
    verify(wheels[-1],expected)


if __name__ == '__main__':
    main()
