"""Build the complete Rangers pack from frozen, reconciled official NHL reports."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'build/rangers-roster'
SERVER = ROOT / 'ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/server'
RARITY = ROOT / 'agents/cypher.docs/rangers_rarity.json'
ART_SOURCES = ROOT / 'agents/oracle.docs/rangers_art_sources.json'
SKATER = ('gamesPlayed','goals','assists','points')
GOALIE = ('gamesPlayed','wins','losses','ties','otLosses','shutouts','goalsAgainstAverage','savePct','saves','shotsAgainst')
TREATMENTS = ('Rinkside','Spotlight','Garden Glow')
FLAVOR = ('Protecting the puck and the last New York bagel.', 'Even the pigeon in the cheap seats wants an autograph.',
          'Skates sharpened. Pretzel secured.', 'The stick handles pucks; the eyebrows handle drama.',
          'A Broadway entrance, followed by a very hockey exit.', 'The equipment bag has its own subway pass.')


def season_label(season: int) -> str:
    return f'{str(season)[:4]}–{str(season)[-2:]}'


def build_catalog(reports: dict, tenures: dict, manifest: dict, audit: dict) -> dict:
    """Join by NHL ID, retaining role/competition boundaries and unknown values."""
    players = {}
    for key, report in reports.items():
        role, game = key.split('-')
        competition = 'regular_season' if game == '2' else 'playoffs'
        fields = SKATER if role == 'skater' else GOALIE
        for row in report['data']:
            identity = row['playerId']
            player = players.setdefault(identity, {'player_id':identity, 'name':row.get('skaterFullName',row.get('goalieFullName')),
                                                   'positions':set(), 'stats':{'regular_season':{},'playoffs':{}}, 'sources':[]})
            player['positions'].add(row.get('positionCode','G') if role == 'skater' else 'G')
            player['stats'][competition][role] = {field:row.get(field) for field in fields}
            query = urlencode({'isAggregate':'true','isGame':'false','cayenneExp':f'teamId=3 and gameTypeId={game} and playerId={identity}'})
            player['sources'].append(f'https://api.nhle.com/stats/rest/en/{role}/summary?{query}')
    if len(players) != audit['all_players'] or set(players) != {int(key) for key in tenures['players']}:
        raise ValueError('Career/tenure/audited player coverage mismatch')
    overrides = {entry['player_id']:entry for entry in manifest['overrides']}
    if len(overrides) != len(manifest['overrides']) or not set(overrides) <= set(players):
        raise ValueError('Duplicate or unknown rarity player ID')
    families = []
    for identity, player in sorted(players.items()):
        player['positions'] = sorted(player['positions'])
        player.update(tenures['players'][str(identity)])
        player['tenure'] = season_label(player['first_season'])
        if player['last_season'] != player['first_season']:
            player['tenure'] += ' to ' + season_label(player['last_season'])
        regular = player['stats']['regular_season']
        appearances = max((stats['gamesPlayed'] for stats in regular.values()),default=0)
        rarity = overrides.get(identity,{}).get('rarity', 'uncommon' if appearances >= manifest['default_rule']['uncommon_min_regular_season_games'] else 'common')
        player['rarity_reason'] = overrides.get(identity,{}).get('reason',manifest['default_rule']['uncommon_basis'] if rarity == 'uncommon' else 'Historical roster member; editorial Common tier.')
        player['rarity_sources'] = overrides.get(identity,{}).get('source_urls',player['sources'])
        if 'skater' in regular:
            stats = regular['skater']
            count = stats['gamesPlayed']
            fact = f"Recorded {count} Rangers regular-season {'appearance' if count == 1 else 'appearances'}."
            if stats['goals'] is not None and stats['assists'] is not None:
                fact += f" Credited with {stats['goals']} {'goal' if stats['goals'] == 1 else 'goals'} and {stats['assists']} {'assist' if stats['assists'] == 1 else 'assists'}."
        elif 'goalie' in regular:
            stats = regular['goalie']
            count = stats['gamesPlayed']
            fact = f"Appeared in {count} Rangers regular-season {'game' if count == 1 else 'games'} as a goaltender."
            if stats['wins'] is not None:
                fact += f" Credited with {stats['wins']} {'win' if stats['wins'] == 1 else 'wins'}."
        else:
            appearances = max(stats['gamesPlayed'] for stats in player['stats']['playoffs'].values())
            fact = f"Recorded Rangers NHL playoff appearances: {appearances} {'game' if appearances == 1 else 'games'}. No regular-season appearances are recorded."
        if len(player['positions']) > 1 and 'G' in player['positions']:
            fact += ' Official records include separate skater and goalie appearances.'
        family_id = f'nyr-{identity}'
        gear = 'goaltender pads and catcher' if player['positions'] == ['G'] else 'skater gloves and hockey stick'
        prompt = (f"Original affectionate cartoon caricature of New York Rangers player {player['name']}, NHL player ID {identity}. "
                  f"Rangers playing era {player['tenure']}; use era-appropriate blue, red and white hockey equipment, {gear}. "
                  'Recognizable face and hairstyle, gently exaggerated expressive head, confident friendly smile, oversized skates and a tiny New York bagel balanced on the equipment. '
                  'Celebratory light hockey humor, no mean caricature or unsupported personal claims. Bold clean ink outlines, rich painted colors, centered full body, square composition, warm ivory background, generous margin. '
                  'No text, letters, labels, numbers, watermarks or photographs. Fresh illustrated art, legible at mobile sticker size. '
                  'Use a reliable player portrait reference when available; do not depict a different player.')
        families.append({'id':family_id,'pack_id':'rangers-history','name':player['name'],'rarity':rarity,'player':player,
                         'fact':fact,'flavor':FLAVOR[identity % len(FLAVOR)],'look':f"Rangers {gear}; {player['tenure']}",
                         'forms':[{'level':level,'name':player['name']+' — '+treatment,'quote':fact,'text_kind':'fact',
                                   'treatment':treatment,'image':f'/static/stickers/rangers-history/{family_id}.webp',
                                   'art_prompt':prompt} for level,treatment in enumerate(TREATMENTS,1)]})
    counts = Counter(f['rarity'] for f in families)
    total = sum(manifest['weights'][f['rarity']] for f in families)
    return {'id':'rangers-history','pack_name':'Broadway Blueshirts: Rangers Through the Years',
            'narrative':f"Collect the full New York Rangers playing history: {len(families):,} players from 1926 onward, including playoff-only appearances. Original affectionate caricatures meet verified Rangers-only statistics. Fan-favorite rarity is editorial; popular icons are the hardest individual pulls. Three matching copies evolve from Rinkside to Spotlight to Garden Glow.",
            'snapshot':audit['fetched_at'],'selection':{'type':'player_weights','weights':manifest['weights']},
            'rarity_policy':manifest['policy'],'rarity_counts':dict(counts),'total_player_weight':total,
            'tier_probabilities':{tier:count*manifest['weights'][tier]/total for tier,count in counts.items()},
            'coverage':{'players':len(families),'forms':len(families)*3,'portraits':len(families),
                        'regular_season_players':audit['regular_season_players'],'playoff_players':audit['playoff_players'],
                        'playoff_only':audit['playoff_only']},'families':families}


def main():
    names = ('skater-2','skater-3','goalie-2','goalie-3')
    reports = {name:json.loads((CACHE/f'{name}.json').read_text()) for name in names}
    catalog = build_catalog(reports,json.loads((CACHE/'seasons-audit.json').read_text()),json.loads(RARITY.read_text()),json.loads((CACHE/'audit.json').read_text()))
    provenance = {}
    for name in [f'{name}.json' for name in names]+['seasons-audit.json']:
        data = (CACHE/name).read_bytes()
        provenance[name] = {'sha256':hashlib.sha256(data).hexdigest()}
        if 'pages' in json.loads(data):
            provenance[name]['urls'] = [page['url'] for page in json.loads(data)['pages']]
        elif name == 'seasons-audit.json':
            provenance[name]['urls'] = [
                'https://api.nhle.com/stats/rest/en/' + role + '/summary?' + urlencode({
                    'isAggregate':'false', 'isGame':'false',
                    'cayenneExp':f'teamId=3 and gameTypeId={game}',
                    'factCayenneExp':'gamesPlayed>=1',
                    'sort':json.dumps([{'property':'playerId','direction':'ASC'},
                                       {'property':'seasonId','direction':'ASC'}]),
                    'limit':100, 'start':0})
                for role in ('skater','goalie') for game in (2,3)]
    catalog['provenance'] = provenance
    if ART_SOURCES.is_file():
        sources = {record['id']:record for record in json.loads(ART_SOURCES.read_text())}
        if set(sources) != {family['id'] for family in catalog['families']}:
            raise ValueError('Portrait source audit must cover the exact player roster')
        for family in catalog['families']:
            source = sources[family['id']]
            available = source['status'] == 'downloaded_for_visual_verification'
            family['art_reference'] = {
                'status':'reference_candidate' if available else 'archival_interpretation',
                'likeness_verified':False,
                'source_url':source.get('source_url',source.get('image_url',source['landing_url'])),
                'retrieved_at':source['fetched_at'],
                'scope':source.get('reference_scope','No usable official identity photograph'),
                'note':'Original cartoon interpretation; facial likeness unverified.' if available else
                       'Archival cartoon interpretation; facial likeness unverified.'}
        catalog['art_reference_coverage'] = dict(Counter(family['art_reference']['status'] for family in catalog['families']))
        catalog['provenance']['art_reference_audit'] = {'sha256':hashlib.sha256(ART_SOURCES.read_bytes()).hexdigest()}
    catalog['rarity_manifest_sha256'] = hashlib.sha256(RARITY.read_bytes()).hexdigest()
    (SERVER/'sticker_catalog_rangers.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    print(f"Catalog: {len(catalog['families'])} players, {catalog['coverage']['forms']} forms; tiers {catalog['rarity_counts']}; total weight {catalog['total_player_weight']}")


if __name__ == '__main__':
    main()
