"""Build the focused target roster: Stanley Cup Champions (82) + Current 2024-2026 Roster (61)."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "game_server/src/game_server"
CATALOG_PATH = SERVER / "sticker_catalog_rangers.json"
OUTPUT_PATH = ROOT / "tools/target_roster.json"

CHAMPIONSHIP_SEASONS = {
    19271928: "1928",
    19321933: "1933",
    19391940: "1940",
    19931994: "1994",
}


import sys
sys.path.insert(0, str(ROOT / "tools"))
try:
    from rangers_flair import get_jersey_number, get_primary_position_code
except ImportError:
    get_jersey_number = lambda pid: None
    get_primary_position_code = lambda pos: (pos[0] if pos else "F")


def build_target_roster() -> list:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    targets = []

    for family in catalog["families"]:
        player = family.get("player", {})
        first = player.get("first_season", 0)
        last = player.get("last_season", 0)

        cups = [yr for s_code, yr in CHAMPIONSHIP_SEASONS.items() if first <= s_code <= last]
        is_current = last >= 20242025

        if cups or is_current:
            positions = player.get("positions", [])
            gear = "goaltender pads, blocker and catcher" if positions == ["G"] else "skater gloves and hockey stick"
            jersey_num = get_jersey_number(player.get("player_id"))
            jersey_str = f" with jersey number {jersey_num} on sweater" if jersey_num is not None else ""

            tags = []
            if cups:
                tags.append(" & ".join(cups) + " Stanley Cup champion")
            if is_current:
                tags.append("active New York Rangers roster")
            honor_text = f" ({', '.join(tags)})" if tags else ""

            prompt = (
                f"Authentic athletic cartoon caricature illustration of New York Rangers player {family['name']}{honor_text}, NHL player ID {player.get('player_id')}. "
                f"Rangers playing era {player.get('tenure')}; wearing official era-appropriate blue, red and white New York Rangers uniform{jersey_str} and {gear}. "
                "Recognizable face and hairstyle, confident athletic expression, classic hockey stance posing proudly in full uniform on ice. "
                "Bold clean ink outlines, rich painted colors, centered full body, square composition, warm ivory background, generous margin. "
                "No text, letters, labels, numbers, watermarks, photographs, food or whimsical props. Fresh illustrated art, legible at mobile sticker size. "
                "Use a reliable player portrait reference when available; do not depict a different player."
            )

            targets.append({
                "id": family["id"],
                "player_id": player.get("player_id"),
                "name": family["name"],
                "jersey_number": jersey_num,
                "is_championship": bool(cups),
                "championships": cups,
                "is_current": is_current,
                "tenure": player.get("tenure"),
                "positions": positions,
                "primary_position": get_primary_position_code(positions),
                "rarity": family.get("rarity", "common"),
                "fact": family.get("fact", ""),
                "image": f"/static/stickers/rangers-history/{family['id']}.webp",
                "art_prompt": prompt,
            })

    targets.sort(key=lambda t: (not t["is_current"], min([int(y) for y in t["championships"]] or [9999]), t["name"]))
    return targets


def main() -> None:
    roster = build_target_roster()
    OUTPUT_PATH.write_text(json.dumps(roster, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    champ_count = sum(1 for p in roster if p["is_championship"])
    curr_count = sum(1 for p in roster if p["is_current"])
    print(f"Generated {OUTPUT_PATH.name} with {len(roster)} target players:")
    print(f"  - Stanley Cup Champions: {champ_count} players")
    print(f"  - Current 2024-2026 Roster: {curr_count} players")
    print(f"  - Total unique players: {len(roster)} players")


if __name__ == "__main__":
    main()
