# Technical Architecture: Generic YAML-Driven Art Generator

**Author**: Morpheus (Tech Lead)  
**Date**: 2026-10-19  
**Status**: APPROVED (Passed Gate 2 Review)

---

## 1. Architectural Blueprint & Philosophy

The art generator refactor eliminates legacy tech debt by replacing ad-hoc, hardcoded scripts (`tools/sticker_art.mjs`, `tools/sticker_production.py`) with a clean, domain-agnostic Python engine (`tools/art_generator.py`).

### Key Design Principles
1. **Domain-Agnostic (Zero Hardcoded Knowledge)**: The engine knows nothing about hockey, Rangers, fantasy clans, or any genre. All subject-matter rules are defined externally in a declarative YAML manifest.
2. **Declarative YAML Contracts**: A single manifest YAML file provides set-level parameters (`artwork_set`) and an itemized manifest (`items`).
3. **Template-Driven Prompts**: Prompts are constructed via dynamic interpolation of item-specific metadata and set-level style/theme tokens.
4. **Isolated Set Subdirectories**: Assets are output to dedicated subdirectories (`<output_dir>/<id>.webp`) to prevent collisions between artwork sets.
5. **Native WebP High-Res Pipeline**: Auto-crops whitespace/margins, centers the character, scales to target dimensions (e.g. 512×512, 1024×1024), and encodes directly as WebP with Pillow.
6. **Pure Image Review Contact Sheet**: Produces a clean HTML review gallery displaying *only* the generated images, metadata, and prompts—without application-specific card flair (no hockey stats ribbons, no evolution borders, no jersey numbers).

---

## 2. Component Architecture

```
                       ┌─────────────────────────┐
                       │  YAML Art Manifest      │
                       │  (artwork_set + items)  │
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │     ManifestParser      │
                       │  (Schema & Validation)  │
                       └────────────┬────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
       ┌─────────────────────┐             ┌─────────────────────┐
       │ PromptTemplateEngine│             │    ArtGenerator     │
       │(safe format mapping)│             │ (status, orchestrate│
       └──────────┬──────────┘             └──────────┬──────────┘
                  │                                   │
                  └─────────────────┬─────────────────┘
                                    ▼
                       ┌─────────────────────────┐
                       │   ArtBackend (Pluggable)│
                       │ ├─ MockBackend (offline)│
                       │ ├─ CLICommandBackend    │
                       │ └─ CallableBackend      │
                       └────────────┬────────────┘
                                    │ (raw image)
                                    ▼
                       ┌─────────────────────────┐
                       │     ImageProcessor      │
                       │  ├─ Auto-Crop & Center  │
                       │  ├─ Lanczos Resampling  │
                       │  └─ WebP Encoder (Q92)  │
                       └────────────┬────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
       ┌───────────────────────────┐ ┌───────────────────────────┐
       │ Set Output Subdirectory   │ │    ContactSheetBuilder    │
       │ (<output_dir>/<id>.webp)  │ │   (clean review.html)     │
       └───────────────────────────┘ └───────────────────────────┘
```

---

## 3. Data Contracts & YAML Schema

```yaml
artwork_set:
  name: "rangers_champions"                  # Unique set slug
  description: "Stanley Cup Champions"       # Optional human summary
  output_dir: "game_server/src/game_server/static/stickers/rangers-history" # Destination
  review_dir: "build/artwork/rangers_champions" # Review destination
  theme: "New York Rangers Historical Championship Era"
  style: "Authentic athletic cartoon caricature illustration, bold ink outlines, warm ivory background, generous margin."
  default_template: "{character_description} {style}"
  format: "webp"                            # Target format
  resolution: [512, 512]                     # Target canvas [width, height]
  quality: 92                               # WebP quality
  autocrop: true                            # Tight crop to content
  pad: 10                                   # Padding inside canvas (px)

items:
  - id: "nyr-8449573"
    prompt: "Mark Messier in 1994 New York Rangers uniform hoisting stick on ice."
    # OR prompt_template using item metadata and global set variables:
    prompt_template: "{name}, NHL player ID {player_id}. Rangers playing era {era}; posing in full uniform on ice. {style}"
    metadata:
      name: "Mark Messier"
      player_id: "8449573"
      era: "1991–92 to 2003–04"
      jersey_number: 11
      position: "C"
```

---

## 4. Subsystem Details

### 4.1 PromptTemplateEngine
- Performs robust string formatting using standard `{key}` template tokens.
- Variables available to each template:
  - All keys in the item's `metadata` dictionary (e.g. `{name}`, `{player_id}`).
  - Global set attributes: `{theme}`, `{style}`, `{set_name}`.
  - `{prompt}` if referencing base item text.
  - `{id}` for the asset identifier.
- Safe substitution: Unresolved keys are preserved or warned rather than crashing the batch.

### 4.2 ImageProcessor
- Accepts raw generated PIL image or bytes.
- Identifies background boundary via corner pixel sampling (`ImageChops.difference`).
- Performs tight bounding-box crop.
- Resizes with Lanczos filter preserving aspect ratio to fit `(width - 2*pad, height - 2*pad)`.
- Pastes onto a clean background canvas of the exact target resolution.
- Saves as native WebP (`quality=92`, `method=6`).

### 4.3 Pluggable Backends
- **MockBackend**: Creates synthetic high-resolution test canvases with gradient and identifier stamps. Used for unit tests, dry-runs, and offline CI without network or quota usage.
- **CLICommandBackend**: Invokes external generation CLIs via template string with variables `{prompt}`, `{output_path}`, `{id}`.
- **CallableBackend**: Allows direct in-process Python callback registration.

### 4.4 ContactSheetBuilder
- Generates `contact_sheet.html` inside the set's review directory.
- Features:
  - Clean responsive grid of images.
  - Player/item title, ID, dimensions, and file size.
  - Resolved prompt snippet in an expandable details block.
  - Click to view/zoom full-resolution WebP.
  - Pure visual review: ZERO usage-specific card flair (no stats ribbons, no evolution frames).
  - Optional `--image-sheet` for generating a single composite stitched `.webp` contact grid.
