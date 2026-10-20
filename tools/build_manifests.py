#!/usr/bin/env python3
"""Build declarative sticker packs: pack-level YAML manifests + per-card JSON data."""

import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "game_server/src/game_server/sticker_catalog"
CATALOG_DIR.mkdir(parents=True, exist_ok=True)


def build_twelve_clans():
    catalog_path = ROOT / "game_server/src/game_server/sticker_catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    cards = []
    for family in catalog["families"]:
        clan_name = family["name"]
        clan_id = family["id"]
        rarity = family.get("rarity", "common")
        clan_look = family.get("look", "")

        for form in family["forms"]:
            lvl = form["level"]
            form_name = form["name"]
            quote = form.get("quote", "")
            item_id = f"{clan_id}-{lvl}"

            cards.append({
                "id": item_id,
                "name": form_name,
                "clan": clan_name,
                "clan_id": clan_id,
                "level": lvl,
                "rarity": rarity,
                "quote": quote,
                "clan_look": clan_look,
            })

    out_dir = CATALOG_DIR / "twelve-clans"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Card Data JSON
    cards_file = out_dir / "cards.json"
    with open(cards_file, "w", encoding="utf-8") as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)
    print(f"Generated {cards_file} with {len(cards)} card records.")

    # 2. Pack-level Manifest YAML with 1 per-item prompt template
    manifest = {
        "artwork_set": {
            "name": "twelve_clans",
            "description": "The Twelve Clans Collectible Stickers (36 forms across 12 clans)",
            "output_dir": "game_server/src/game_server/static/stickers",
            "review_dir": "build/artwork/twelve_clans/review",
            "theme": "Mythic fantasy tabletop RPG miniature aesthetic with twelve sworn factions",
            "style": "Original tabletop RPG collectible sticker illustration, bold ink outline, rich painted colors, single centered full-body champion, square composition, clean warm ivory background, generous margin, no words, letters, numbers, labels or watermark. Maintain clan palette and emblem. Legible at mobile card size.",
            "format": "webp",
            "resolution": [512, 512],
            "quality": 92,
            "autocrop": True,
            "pad": 10,
        },
        "item_template": {
            "prompt_template": "{clan_look} Depict {name}: Evolution level {level} of 3. {style}",
        },
        "data_file": "cards.json",
    }
    out_manifest = out_dir / "manifest.yaml"
    with open(out_manifest, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, sort_keys=False, allow_unicode=True)
    print(f"Generated {out_manifest} (pack metadata + 1 item template).")


def build_rangers_manifests():
    target_roster_path = ROOT / "tools/target_roster.json"
    players = json.loads(target_roster_path.read_text(encoding="utf-8"))

    # Extract championship players
    champ_players = [p for p in players if p.get("is_championship")]

    def make_cards(player_list):
        cards = []
        for p in player_list:
            gear = "skater gloves and hockey stick"
            pos_list = p.get("positions", [])
            is_goalie = "G" in pos_list or p.get("primary_position") == "G"
            if is_goalie:
                gear = "goalie pads, trapper, blocker and goalie stick"

            cohort = "Stanley Cup Champion" if p.get("is_championship") else "Current 2025–2026 Roster"
            cups = " & ".join(p.get("championships", [])) if p.get("championships") else "None"

            cards.append({
                "id": p["id"],
                "name": p["name"],
                "player_id": p["player_id"],
                "jersey_number": p.get("jersey_number") or 0,
                "position": p.get("primary_position") or (pos_list[0] if pos_list else "F"),
                "era": p.get("tenure", ""),
                "gear": gear,
                "cohort": cohort,
                "championships": cups,
                "rarity": p.get("rarity", "common"),
            })
        return cards

    rangers_dir = CATALOG_DIR / "rangers-history"
    rangers_dir.mkdir(parents=True, exist_ok=True)

    # 1. Rangers Targets (Full 143 cards data + manifest)
    target_cards = make_cards(players)
    targets_data_file = rangers_dir / "cards.json"
    with open(targets_data_file, "w", encoding="utf-8") as f:
        json.dump(target_cards, f, indent=2, ensure_ascii=False)
    print(f"Generated {targets_data_file} with {len(target_cards)} cards.")

    targets_manifest = {
        "artwork_set": {
            "name": "rangers_targets",
            "description": "New York Rangers Full Target Roster (143 Players: 82 Cup Champions + 61 Current 2025–2026)",
            "output_dir": "game_server/src/game_server/static/stickers/rangers-history",
            "review_dir": "build/artwork/rangers_targets/review",
            "theme": "New York Rangers History: Championship Legends and Current 2025–2026 Roster",
            "style": "Authentic athletic cartoon caricature illustration, bold clean ink outlines, rich painted colors, centered full body, square composition, warm ivory background, generous margin. No text, letters, labels, numbers, watermarks, photographs, food or whimsical props. Legible at mobile sticker size.",
            "format": "webp",
            "resolution": [512, 512],
            "quality": 92,
            "autocrop": True,
            "pad": 10,
        },
        "item_template": {
            "prompt_template": "Authentic athletic cartoon caricature illustration of New York Rangers player {name}, NHL player ID {player_id}. Rangers playing era {era}; wearing official era-appropriate blue, red and white New York Rangers uniform and {gear}. Recognizable face and hairstyle, confident athletic expression, classic hockey stance posing proudly in full uniform on ice. {style}",
        },
        "data_file": "cards.json",
    }
    targets_manifest_file = rangers_dir / "manifest.yaml"
    with open(targets_manifest_file, "w", encoding="utf-8") as f:
        yaml.dump(targets_manifest, f, sort_keys=False, allow_unicode=True)
    print(f"Generated {targets_manifest_file} (pack metadata + 1 item template).")

    # 2. Rangers Champions (82 cards data + champions.yaml)
    champ_cards = make_cards(champ_players)
    champ_data_file = rangers_dir / "champions_cards.json"
    with open(champ_data_file, "w", encoding="utf-8") as f:
        json.dump(champ_cards, f, indent=2, ensure_ascii=False)
    print(f"Generated {champ_data_file} with {len(champ_cards)} cards.")

    champ_manifest = {
        "artwork_set": {
            "name": "rangers_champions",
            "description": "New York Rangers Stanley Cup Champions (82 Players across 1994, 1940, 1933, and 1928)",
            "output_dir": "game_server/src/game_server/static/stickers/rangers-history",
            "review_dir": "build/artwork/rangers_champions/review",
            "theme": "New York Rangers Stanley Cup Championship Eras (1928, 1933, 1940, 1994)",
            "style": "Authentic athletic cartoon caricature illustration, bold clean ink outlines, rich painted colors, centered full body, square composition, warm ivory background, generous margin. No text, letters, labels, numbers, watermarks, photographs, food or whimsical props. Legible at mobile sticker size.",
            "format": "webp",
            "resolution": [512, 512],
            "quality": 92,
            "autocrop": True,
            "pad": 10,
        },
        "item_template": {
            "prompt_template": "Authentic athletic cartoon caricature illustration of New York Rangers player {name}, NHL player ID {player_id}. Rangers playing era {era}; wearing official era-appropriate blue, red and white New York Rangers uniform and {gear}. Recognizable face and hairstyle, confident athletic expression, classic hockey stance posing proudly in full uniform on ice. {style}",
        },
        "data_file": "champions_cards.json",
    }
    champ_manifest_file = rangers_dir / "champions.yaml"
    with open(champ_manifest_file, "w", encoding="utf-8") as f:
        yaml.dump(champ_manifest, f, sort_keys=False, allow_unicode=True)
    print(f"Generated {champ_manifest_file} (champions metadata + 1 item template).")


def build_fantasy_example():
    catalog_path = ROOT / "game_server/src/game_server/sticker_catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    cards = []
    for family in catalog["families"]:
        clan_name = family["name"]
        clan_id = family["id"]
        form_level_1 = family["forms"][0]
        rarity = family.get("rarity", "common")

        cards.append({
            "id": f"{clan_id}-hero",
            "name": form_level_1["name"],
            "character_name": form_level_1["name"],
            "clan": clan_name,
            "rarity": rarity,
            "quote": form_level_1.get("quote", ""),
            "clan_look": family.get("look", ""),
        })

    fantasy_dir = CATALOG_DIR / "fantasy-heroes"
    fantasy_dir.mkdir(parents=True, exist_ok=True)

    # 1. Cards Data JSON
    cards_file = fantasy_dir / "cards.json"
    with open(cards_file, "w", encoding="utf-8") as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)
    print(f"Generated {cards_file} with {len(cards)} cards.")

    # 2. Pack Manifest YAML with 1 per-item prompt template
    manifest = {
        "artwork_set": {
            "name": "fantasy_heroes",
            "description": "Tabletop RPG Clan Champions (12 Primary Clan Heroes)",
            "output_dir": "build/artwork/fantasy_heroes",
            "review_dir": "build/artwork/fantasy_heroes/review",
            "theme": "Mythic fantasy tabletop miniature aesthetic with twelve ancestral clans",
            "style": "Original tabletop RPG collectible sticker illustration, bold ink outline, rich painted colors, single centered full-body champion, square composition, clean warm ivory background, generous margin. Legible at mobile size.",
            "format": "webp",
            "resolution": [512, 512],
            "quality": 92,
            "autocrop": True,
            "pad": 12,
        },
        "item_template": {
            "prompt_template": "{character_name} of the {clan}: {clan_look}. Posing proudly with clan emblem. {style}",
        },
        "data_file": "cards.json",
    }
    manifest_file = fantasy_dir / "manifest.yaml"
    with open(manifest_file, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, sort_keys=False, allow_unicode=True)
    print(f"Generated {manifest_file} (fantasy metadata + 1 item template).")


if __name__ == "__main__":
    build_twelve_clans()
    build_rangers_manifests()
    build_fantasy_example()
