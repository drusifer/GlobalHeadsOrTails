# Sprint Backlog: Generic YAML-Driven Art Generator Refactor

**Sprint Goal**: Refactor the art generation tool into a domain-agnostic, generic engine driven purely by declarative YAML manifests, outputting high-resolution WebP images into set-specific subdirectories with clean image-only contact sheets and zero card flair.

---

## User Stories

### US-ART-001: Declarative YAML Manifest & Prompt Template Engine
**As an** art director or developer,  
**I want** to specify artwork generation sets using a clean, declarative YAML manifest with metadata templating,  
**So that** the generator tool contains zero hardcoded knowledge of hockey, fantasy, or any specific genre.

#### Acceptance Criteria
1. Define a standardized YAML manifest schema supporting:
   - `artwork_set`: `name`, `description`, `output_dir`, `review_dir`, `theme`, `style`, `default_template`, `format` (default: `webp`), `resolution` (default: `[512, 512]`), `quality` (default: `92`), `autocrop` (default: `true`), `pad` (default: `10`).
   - `items`: List of entries, each containing `id` (required, unique stem), `prompt` or `prompt_template`, and arbitrary key-value `metadata`.
2. Implement `PromptEngine` that resolves the final prompt by interpolating item metadata (`{name}`, `{role}`, etc.) and global set parameters (`{theme}`, `{style}`, `{set_name}`) into the item template.
3. Validate manifests strictly with descriptive errors for missing IDs, malformed YAML, or invalid templates.
4. Support `--export-prompts` in CLI to preview resolved prompts without running image generation.

---

### US-ART-002: Pluggable Backend & High-Res WebP Pipeline
**As a** pipeline developer,  
**I want** pluggable generation backends and a robust Pillow-based WebP image processing pipeline,  
**So that** I can test generation deterministically in offline environments and output production-ready, auto-cropped WebP assets.

#### Acceptance Criteria
1. Pluggable backend architecture:
   - `MockBackend`: Generates synthetic high-resolution test canvases with gradient and identifier stamps for instant offline testing and unit tests without external API dependencies.
   - `CLICommandBackend`: Executes configurable command-line generator scripts or tools if specified.
   - Extensible base class `ArtBackend` for custom providers.
2. WebP Image Processing (`ImageProcessor`):
   - Automatic background margin detection and tight auto-cropping.
   - Centering and scaling with Lanczos resampling to specified target resolution (e.g. 512×512, 1024×1024).
   - High-quality WebP encoding (`quality=92`, `method=6`).
3. Resumability: Skips already existing WebP files unless `--force` or `--regenerate` is explicitly passed.

---

### US-ART-003: Set-Specific Storage & Clean Visual Review Contact Sheet
**As an** art reviewer or UX lead,  
**I want** generated images stored in dedicated subdirectories with a clean image-only review contact sheet,  
**So that** I can visually inspect newly generated artwork without usage-specific card flair, decorations, or giant monolithic composite images.

#### Acceptance Criteria
1. Output directory is set-specific and configurable per manifest (e.g. `build/artwork/<set_name>/` or `static/stickers/<set_name>/`), created automatically if missing.
2. Contact Sheet Builder (`ContactSheetBuilder`):
   - Generates a lightweight, responsive HTML review sheet (`contact_sheet.html`) displaying ONLY the rendered images in a clean, scrollable visual grid.
   - Shows image thumbnail, item ID, metadata title, dimensions, and prompt snippet.
   - Clickable links to inspect the full-resolution WebP image directly in the browser.
   - Zero card flair: No hockey stats ribbons, no fantasy evolution frames, no jersey number patches—pure image inspection.
3. Optional `--image-sheet` flag to generate a single composite stitched contact sheet image if needed for offline packaging.

---

### US-ART-004: Comprehensive Test Suite, CLI Tool & Makefile Automation
**As a** QA guardian and DevOps engineer,  
**I want** comprehensive unit tests and automated make targets,  
**So that** the generic art generator maintains 100% test coverage and is easy to run from the root workspace.

#### Acceptance Criteria
1. Implement executable CLI `tools/art_generator.py` with arguments:
   - `--manifest PATH`: Path to YAML manifest file.
   - `--status`: Report total, existing, and missing artwork counts.
   - `--generate`: Generate missing artwork items.
   - `--force`: Regenerate all items even if they exist.
   - `--item ID`: Target a specific item ID.
   - `--review`: Build review contact sheet for existing images.
   - `--backend {mock,cli}`: Select generation backend.
   - `--export-prompts`: Print resolved prompts.
2. Test suite in `tools/tests/test_art_generator.py` verifying:
   - YAML loading and validation.
   - Prompt template interpolation with metadata, theme, and style.
   - Image processor auto-cropping and WebP encoding.
   - Pluggable mock backend generation.
   - Contact sheet HTML generation.
   - CLI status and argument handling.
3. Root `Makefile.prj` updated with:
   - `test-art-generator`: Runs pytest on `tools/tests/test_art_generator.py`.
   - `art-status`, `art-generate`, `art-review`: Convenient entrypoints for the generic art generator.
4. 100% of new and existing tests pass cleanly.
