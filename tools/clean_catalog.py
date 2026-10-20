"""Clean all prompts and flavors in sticker_catalog_rangers.json (zero bagels, authentic uniform poses)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT_PATHS = [
    ROOT / "game_server/src/game_server/sticker_catalog_rangers.json",
    ROOT / "ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/server/sticker_catalog_rangers.json",
]

FLAVOR = (
    "Ready for the opening faceoff under the Garden lights.",
    "Even the pigeon in the cheap seats wants an autograph.",
    "Skates sharpened, tape fresh, ready for the Garden ice.",
    "The stick handles pucks; the eyebrows handle drama.",
    "A Broadway entrance, followed by a very hockey exit.",
    "The equipment bag has its own subway pass.",
)


def main():
    for cat_path in CAT_PATHS:
        if not cat_path.is_file():
            continue
        cat = json.loads(cat_path.read_text(encoding="utf-8"))
        for fam in cat["families"]:
            p = fam["player"]
            pid = p["player_id"]
            fam["flavor"] = FLAVOR[pid % len(FLAVOR)]
            gear = "goaltender pads, blocker and catcher" if p.get("positions") == ["G"] else "skater gloves and hockey stick"
            prompt = (
                f"Authentic athletic cartoon caricature illustration of New York Rangers player {p['name']}, NHL player ID {pid}. "
                f"Rangers playing era {p['tenure']}; wearing official era-appropriate blue, red and white New York Rangers uniform and {gear}. "
                "Recognizable face and hairstyle, confident athletic expression, classic hockey stance posing proudly in full uniform on ice. "
                "Bold clean ink outlines, rich painted colors, centered full body, square composition, warm ivory background, generous margin. "
                "No text, letters, labels, numbers, watermarks, photographs, food or whimsical props. Fresh illustrated art, legible at mobile sticker size. "
                "Use a reliable player portrait reference when available; do not depict a different player."
            )
            for form in fam["forms"]:
                form["art_prompt"] = prompt
                form["image"] = f"/static/stickers/rangers-history/{fam['id']}.webp"

        cat_path.write_text(json.dumps(cat, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Purged bagels and updated prompts across all {len(cat['families'])} player families in {cat_path}!")


if __name__ == "__main__":
    main()
