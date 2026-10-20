# Generic Art Generator Guide

**Author**: Oracle (Knowledge Officer)  
**Date**: 2026-10-19  
**Status**: ACTIVE

---

## Overview

`tools/art_generator.py` is a domain-agnostic, declarative YAML-driven art generation engine. It completely eliminates hardcoded subject-matter coupling (such as hockey rosters, fantasy clans, or RPG lore) from the codebase.

The generator consumes a single declarative YAML manifest and produces:
1. High-resolution WebP images (`quality=92`, `method=6`, 512×512 or custom resolution) stored in a dedicated set subdirectory.
2. Tight auto-cropping and centering that maximizes the character/subject while preserving aspect ratio.
3. A clean, responsive HTML inspection contact sheet (`contact_sheet.html`) displaying *only* the rendered images, metadata, and resolved prompts—with zero usage-specific card flair (no stats ribbons, no evolution borders, no jersey numbers).

---

## Manifest Organization & Modes

Manifests live in `game_server/src/game_server/sticker_catalog/<set-id>/manifest.yaml`. The engine supports two modes:

### Mode A: Structured Pack Catalog (`cards.json` + `item_template`) — **Recommended**
Decouples pure data from prompt templates. `cards.json` contains the array of cards with actual fields filled out. The manifest provides pack metadata and **one** prompt template:

```yaml
artwork_set:
  name: "twelve_clans"
  description: "The Twelve Clans Collectible Stickers (36 forms across 12 clans)"
  output_dir: "game_server/src/game_server/static/stickers"
  review_dir: "build/artwork/twelve_clans/review"
  theme: "Mythic fantasy tabletop RPG miniature aesthetic with twelve sworn factions"
  style: "Original tabletop RPG collectible sticker illustration, bold ink outline, rich painted colors, single centered full-body champion, square composition, clean warm ivory background, generous margin. Legible at mobile size."
  format: "webp"
  resolution: [512, 512]
  quality: 92
  autocrop: true
  pad: 10

# Single prompt template applied across all cards in cards.json
item_template:
  prompt_template: "{clan_look} Depict {name}: Evolution level {level} of 3. {style}"

# Path to the card data JSON (relative to the manifest file)
data_file: "cards.json"
```

**`cards.json` Example:**
```json
[
  {
    "id": "hearthshield-compact-1",
    "name": "Hearth Recruit",
    "clan": "Hearthshield Clan",
    "clan_id": "hearthshield-compact",
    "level": 1,
    "rarity": "common",
    "quote": "Our clan begins wherever someone guards another's door.",
    "clan_look": "Human hearth-kin with rounded shields, warm ochre cloaks, copper kettle emblem."
  }
]
```

### Mode B: Inline Items (`items: [...]`)
For smaller or ad-hoc sets where cards are embedded directly:

```yaml
artwork_set:
  name: "fantasy_heroes"
  output_dir: "build/artwork/fantasy_heroes"
  theme: "Mythic fantasy heroes"
  style: "Bold ink outlines, rich colors"

items:
  - id: "item-01"
    prompt_template: "{name} in {theme}. Wielding {gear}. {style}"
    metadata:
      name: "Subject Name"
      gear: "Epic item"
```

---

## Template Engine Variables

Each item's prompt template can safely interpolate:
- `{id}`: The item ID.
- `{prompt}`: The item's base prompt (if defined).
- `{theme}`: Set-level `theme`.
- `{style}`: Set-level `style`.
- `{set_name}`: Set-level `name`.
- Any key from `item.metadata` (e.g. `{name}`, `{player_id}`, `{role}`, `{era}`).

Missing template tokens are preserved safely without throwing exceptions.

---

## Makefile Automation

```bash
# Check status of an artwork manifest (total, ready, missing)
make art-status MANIFEST=game_server/src/game_server/sticker_catalog/twelve-clans/manifest.yaml

# Generate missing artwork items
make art-generate MANIFEST=game_server/src/game_server/sticker_catalog/twelve-clans/manifest.yaml BACKEND=mock

# Build clean HTML review contact sheet
make art-review MANIFEST=game_server/src/game_server/sticker_catalog/twelve-clans/manifest.yaml

# Run test suite
make test-art-generator
```

---

## CLI Reference

```bash
python tools/art_generator.py --manifest <file.yaml> [options]

Options:
  --status           Show set status, geometry, and missing items
  --generate         Generate missing artwork items
  --force            Regenerate existing items
  --item <id>        Target single item ID
  --review           Build review contact sheet
  --export-prompts   Export resolved prompts as JSON to stdout
  --backend {mock,cli} Choose generation backend (default: mock)
```
