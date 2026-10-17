"""Frozen official roster coverage, mixed roles and documented per-player rarity."""
import json
from pathlib import Path
from urllib.parse import urlparse

import pytest

CATALOG = Path(__file__).parents[1] / 'src/ntag424_sdm_provisioner/server/sticker_catalog_rangers.json'


@pytest.fixture(scope='module')
def catalog():
    return json.loads(CATALOG.read_text())


def test_full_roster_ids_forms_and_portraits(catalog):
    families = catalog['families']
    assert len(families) == catalog['coverage']['players'] == 1162
    ids = {f['player']['player_id'] for f in families}
    assert len(ids) == len(families)
    for family in families:
        assert family['id'] == f"nyr-{family['player']['player_id']}"
        assert [form['level'] for form in family['forms']] == [1,2,3]
        assert len({form['image'] for form in family['forms']}) == 1
        assert family['fact'] and family['player']['first_season'] <= family['player']['last_season']
        assert all(form['text_kind'] == 'fact' for form in family['forms'])
    assert sum(len(f['forms']) for f in families) == 3486


def test_team_only_known_totals_and_legendary_icons(catalog):
    players = {f['name']:f for f in catalog['families']}
    wayne = players['Wayne Gretzky']
    assert wayne['rarity'] == 'legendary'
    assert wayne['player']['stats']['regular_season']['skater'] == {'gamesPlayed':234,'goals':57,'assists':192,'points':249}
    henrik = players['Henrik Lundqvist']
    assert henrik['rarity'] == 'legendary'
    assert henrik['player']['stats']['regular_season']['goalie']['wins'] == 459
    assert henrik['player']['stats']['regular_season']['goalie']['gamesPlayed'] == 887


def test_playoff_only_and_lester_patrick_are_not_lost(catalog):
    by_id = {f['player']['player_id']:f for f in catalog['families']}
    assert len(catalog['coverage']['playoff_only']) == 6
    for row in catalog['coverage']['playoff_only']:
        assert by_id[row['playerId']]['player']['stats']['regular_season'] == {}
        assert 'playoff' in by_id[row['playerId']]['fact']
    lester = by_id[8448095]['player']['stats']
    assert lester['regular_season']['skater']['gamesPlayed'] == 1
    assert lester['playoffs']['goalie']['gamesPlayed'] == 1


def test_rarity_is_per_player_not_tier_first(catalog):
    weights = catalog['selection']['weights']
    assert weights == {'common':8,'uncommon':4,'rare':2,'legendary':1}
    assert catalog['rarity_counts'] == {'common':908,'uncommon':219,'rare':22,'legendary':13}
    assert catalog['total_player_weight'] == 8197
    assert sum(catalog['tier_probabilities'].values()) == pytest.approx(1)
    assert weights['legendary']/8197 < weights['rare']/8197 < weights['uncommon']/8197 < weights['common']/8197


def test_fact_sources_and_historical_unavailable_rates(catalog):
    unknown = 0
    for family in catalog['families']:
        for url in family['player']['sources']:
            assert urlparse(url).hostname == 'api.nhle.com'
        for competition in family['player']['stats'].values():
            goalie = competition.get('goalie')
            if goalie and goalie['savePct'] is None:
                unknown += 1
    assert unknown > 0
    assert len(catalog['provenance']) == 6
    assert catalog['snapshot'].startswith('2026-10-08')


def test_portrait_candidates_never_claim_verified_facial_likeness(catalog):
    assert catalog['art_reference_coverage'] == {'reference_candidate':717, 'archival_interpretation':445}
    for family in catalog['families']:
        reference = family['art_reference']
        assert reference['likeness_verified'] is False
        assert reference['source_url'].startswith('https://')
        assert 'unverified' in reference['note']
        if reference['status'] == 'archival_interpretation':
            assert reference['note'].startswith('Archival cartoon interpretation')
