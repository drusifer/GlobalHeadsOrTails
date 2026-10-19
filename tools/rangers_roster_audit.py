"""Snapshot official NHL NYR regular-season and playoff career statistics."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OUT = Path('build/rangers-roster')


def fetch(role, game_type, aggregate=True):
    rows, pages, start = [], [], 0
    while True:
        query = urlencode(dict(isAggregate=str(aggregate).lower(), isGame='false', start=start,
                               limit=100, sort=json.dumps([{'property': 'playerId', 'direction': 'ASC'}] + ([] if aggregate else [{'property': 'seasonId', 'direction': 'ASC'}])),
                               factCayenneExp='gamesPlayed>=1',
                               cayenneExp=f'teamId=3 and gameTypeId={game_type}'))
        url = f'https://api.nhle.com/stats/rest/en/{role}/summary?{query}'
        with urlopen(Request(url, headers={'User-Agent': 'RangersRosterAudit/1.0'}), timeout=60) as response:
            data = json.load(response)
        pages.append({'url': url, 'response': data})
        rows.extend(data['data'])
        if len(rows) >= data['total']:
            break
        if not data['data']:
            raise ValueError('Empty page before reported total')
        start += len(data['data'])
    ids = [row['playerId'] if aggregate else (row['playerId'],row['seasonId']) for row in rows]
    if len(ids) != len(set(ids)) or len(ids) != data['total']:
        raise ValueError(f'{role}/{game_type}: unstable pagination or duplicate IDs')
    return {'total': len(rows), 'pages': pages, 'data': rows}


def season_audit():
    reports = {}
    for role in ('skater', 'goalie'):
        for game in (2, 3):
            key = f'{role}-{game}'
            destination = OUT / f'{key}-seasons.json'
            reports[key] = json.loads(destination.read_text()) if destination.exists() else fetch(role, game, aggregate=False)
            destination.write_text(json.dumps(reports[key], indent=2) + '\n')
            print(key, 'season rows:', reports[key]['total'], flush=True)
    career = {row['playerId'] for role in ('skater','goalie') for game in (2,3)
              for row in json.loads((OUT / f'{role}-{game}.json').read_text())['data']}
    seasons = {}
    for report in reports.values():
        for row in report['data']:
            seasons.setdefault(str(row['playerId']), []).append(row['seasonId'])
    assert career == {int(value) for value in seasons}, 'Career/season player union mismatch'
    result = {'fetched_at': datetime.now(timezone.utc).isoformat(), 'all_players':len(career),
              'players': {key:{'first_season':min(value),'last_season':max(value)} for key,value in seasons.items()}}
    (OUT / 'seasons-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'PASS: first/last NYR seasons reconciled for all {len(career)} players')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seasons', action='store_true')
    args = parser.parse_args()
    if args.seasons:
        season_audit()
        return
    OUT.mkdir(parents=True, exist_ok=True)
    reports = {}
    for role in ('skater', 'goalie'):
        for game in (2, 3):
            key = f'{role}-{game}'
            reports[key] = fetch(role, game)
            (OUT / f'{key}.json').write_text(json.dumps(reports[key], indent=2) + '\n')
            print(key, reports[key]['total'])
    regular = {r['playerId'] for k, v in reports.items() if k.endswith('-2') for r in v['data']}
    playoffs = {r['playerId'] for k, v in reports.items() if k.endswith('-3') for r in v['data']}
    names = {r['playerId']: r.get('skaterFullName', r.get('goalieFullName')) for v in reports.values() for r in v['data']}
    audit = {'fetched_at': datetime.now(timezone.utc).isoformat(), 'teamId': 3,
             'regular_season_players': len(regular), 'playoff_players': len(playoffs),
             'all_players': len(regular | playoffs),
             'playoff_only': [{'playerId': p, 'name': names[p]} for p in sorted(playoffs - regular)]}
    (OUT / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit, indent=2))
    for key, report in reports.items():
        for row in report['data']:
            if row.get('skaterFullName', row.get('goalieFullName')) in ('Wayne Gretzky', 'Lester Patrick', 'Henrik Lundqvist'):
                print(key, row)


if __name__ == '__main__':
    main()
