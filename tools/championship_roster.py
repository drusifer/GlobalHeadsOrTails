"""Build and maintain the 82-player Rangers Stanley Cup Championship Roster and Manifest."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "game_server/src/game_server"
CATALOG_PATH = SERVER / "sticker_catalog_rangers.json"
OUTPUT_PATH = ROOT / "tools/championship_roster.json"

CHAMPIONSHIP_SEASONS = {
    19271928: "1928",
    19321933: "1933",
    19391940: "1940",
    19931994: "1994",
}


def build_championship_roster() -> list:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    champions = []

    for family in catalog["families"]:
        player = family.get("player", {})
        first = player.get("first_season")
        last = player.get("last_season")

        if first and last:
            cups = [yr for s_code, yr in CHAMPIONSHIP_SEASONS.items() if first <= s_code <= last]
            if cups:
                positions = player.get("positions", [])
                gear = "goaltender pads, blocker and catcher" if positions == ["G"] else "skater gloves and hockey stick"
                cups_label = " & ".join(cups) + " Stanley Cup champion"
                prompt = (
                    f"Authentic athletic cartoon caricature illustration of New York Rangers player {family['name']} ({cups_label}), NHL player ID {player.get('player_id')}. "
                    f"Rangers playing era {player.get('tenure')}; wearing official era-appropriate blue, red and white New York Rangers uniform and {gear}. "
                    "Recognizable face and hairstyle, confident athletic expression, classic hockey stance posing proudly in full uniform on ice. "
                    "Bold clean ink outlines, rich painted colors, centered full body, square composition, warm ivory background, generous margin. "
                    "No text, letters, labels, numbers, watermarks, photographs, food or whimsical props. Fresh illustrated art, legible at mobile sticker size. "
                    "Use a reliable player portrait reference when available; do not depict a different player."
                )

                champions.append({
                    "id": family["id"],
                    "player_id": player.get("player_id"),
                    "name": family["name"],
                    "championships": cups,
                    "tenure": player.get("tenure"),
                    "positions": positions,
                    "rarity": family.get("rarity", "common"),
                    "fact": family.get("fact", ""),
                    "image": f"/static/stickers/rangers-history/{family['id']}.webp",
                    "art_prompt": prompt,
                })

    champions.sort(key=lambda c: (min(int(yr) for yr in c["championships"]), c["name"]))
    return champions


def main() -> None:
    roster = build_championship_roster()
    OUTPUT_PATH.write_text(json.dumps(roster, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Generated {OUTPUT_PATH.name} with {len(roster)} championship players:")
    breakdown = {}
    for c in roster:
        key = ", ".join(c["championships"])
        breakdown[key] = breakdown.get(key, 0) + 1
    for cups, count in sorted(breakdown.items()):
        print(f"  Stanley Cup {cups}: {count} players")


if __name__ == "__main__":
    main()
