#!/usr/bin/env python3
"""Generic, domain-agnostic YAML-driven art generator.

TLDR:
    Takes a declarative YAML manifest specifying an artwork set, global theme/style,
    and itemized metadata templates. Generates high-resolution WebP images into set-specific
    subdirectories with tight auto-cropping and centering, and creates clean visual review
    contact sheets with zero usage-specific card flair.

Usage:
    python tools/art_generator.py --manifest path/to/manifest.yaml --status
    python tools/art_generator.py --manifest path/to/manifest.yaml --generate [--backend mock|cli]
    python tools/art_generator.py --manifest path/to/manifest.yaml --review
    python tools/art_generator.py --manifest path/to/manifest.yaml --export-prompts
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import yaml
from PIL import Image, ImageChops, ImageDraw, ImageFont


# ─────────────────────────────────────────────────────────────────────────────
# 1. Data Contracts
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ArtworkSetMeta:
    """Metadata describing the artwork set, styling, and processing rules."""
    name: str
    description: str = ""
    output_dir: Path = field(default_factory=lambda: Path("build/artwork/default"))
    review_dir: Path = field(default_factory=lambda: Path("build/artwork/default/review"))
    theme: str = ""
    style: str = ""
    default_template: str = "{prompt}"
    format: str = "webp"
    resolution: Tuple[int, int] = (512, 512)
    quality: int = 92
    autocrop: bool = True
    pad: int = 10
    cli_command: str = ""


@dataclass
class ArtItem:
    """A single artwork item to be generated."""
    id: str
    prompt: str = ""
    prompt_template: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    output_filename: str = ""

    def get_filename(self, ext: str = "webp") -> str:
        if self.output_filename:
            return self.output_filename
        clean_id = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", self.id)
        return f"{clean_id}.{ext}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Manifest Parser
# ─────────────────────────────────────────────────────────────────────────────

class ManifestParser:
    """Parses and validates declarative YAML artwork manifests."""

    @staticmethod
    def _parse_resolution(val: Any) -> Tuple[int, int]:
        if isinstance(val, (list, tuple)) and len(val) >= 2:
            return int(val[0]), int(val[1])
        if isinstance(val, int):
            return val, val
        if isinstance(val, str):
            parts = val.lower().replace(" ", "").split("x")
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
        return 512, 512

    @classmethod
    def load(cls, manifest_path: Path | str, base_dir: Optional[Path] = None) -> Tuple[ArtworkSetMeta, List[ArtItem]]:
        path = Path(manifest_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Manifest not found: {path}")

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid YAML manifest in {path}: expected top-level dictionary")

        context_root = base_dir or Path.cwd()

        # 1. Parse Set Metadata
        set_data = raw.get("artwork_set", {})
        if not isinstance(set_data, dict):
            raise ValueError("Missing or invalid 'artwork_set' mapping in manifest")

        name = str(set_data.get("name") or path.stem).strip()
        if not name:
            raise ValueError("artwork_set.name cannot be empty")

        raw_output_dir = set_data.get("output_dir", f"build/artwork/{name}")
        out_dir = Path(raw_output_dir)
        if not out_dir.is_absolute():
            out_dir = (context_root / out_dir).resolve()

        raw_review_dir = set_data.get("review_dir", str(out_dir / "review"))
        rev_dir = Path(raw_review_dir)
        if not rev_dir.is_absolute():
            rev_dir = (context_root / rev_dir).resolve()

        resolution = cls._parse_resolution(set_data.get("resolution", (512, 512)))

        meta = ArtworkSetMeta(
            name=name,
            description=str(set_data.get("description", "")),
            output_dir=out_dir,
            review_dir=rev_dir,
            theme=str(set_data.get("theme", "")).strip(),
            style=str(set_data.get("style", "")).strip(),
            default_template=str(set_data.get("default_template", "{prompt}")),
            format=str(set_data.get("format", "webp")).lower(),
            resolution=resolution,
            quality=int(set_data.get("quality", 92)),
            autocrop=bool(set_data.get("autocrop", True)),
            pad=int(set_data.get("pad", 10)),
            cli_command=str(set_data.get("cli_command", "")),
        )

        # 2. Parse Items (from inline 'items' list OR 'data_file' + 'item_template')
        raw_items = raw.get("items")
        if raw_items is None:
            data_file_rel = raw.get("data_file", "cards.json")
            data_path = (path.parent / data_file_rel).resolve()
            if not data_path.is_file():
                raise FileNotFoundError(
                    f"Manifest {path} specifies data_file '{data_file_rel}', but {data_path} does not exist"
                )
            loaded_data = json.loads(data_path.read_text(encoding="utf-8"))
            if isinstance(loaded_data, list):
                raw_cards = loaded_data
            elif isinstance(loaded_data, dict):
                raw_cards = loaded_data.get("cards") or loaded_data.get("items")
                if raw_cards is None and "families" in loaded_data:
                    raw_cards = []
                    for fam in loaded_data["families"]:
                        for form in fam.get("forms", []):
                            raw_cards.append({
                                "id": f"{fam['id']}-{form['level']}",
                                "name": form.get("name"),
                                "clan": fam.get("name"),
                                "clan_id": fam.get("id"),
                                "level": form.get("level"),
                                "rarity": fam.get("rarity", "common"),
                                "quote": form.get("quote", ""),
                                "clan_look": fam.get("look", ""),
                            })
            else:
                raise ValueError(f"Unexpected JSON card data format in {data_path}: expected list or dict")

            # Extract default item prompt template for the pack
            item_template_cfg = raw.get("item_template", {})
            if isinstance(item_template_cfg, str):
                default_prompt_template = item_template_cfg
            elif isinstance(item_template_cfg, dict):
                default_prompt_template = item_template_cfg.get("prompt_template", "")
            else:
                default_prompt_template = ""

            raw_items = []
            for card in (raw_cards or []):
                if not isinstance(card, dict):
                    continue
                cid = str(card.get("id", "")).strip()
                cprompt = str(card.get("prompt", "")).strip()
                ctemplate = str(card.get("prompt_template") or default_prompt_template).strip()
                cfile = str(card.get("output_filename", "")).strip()
                raw_items.append({
                    "id": cid,
                    "prompt": cprompt,
                    "prompt_template": ctemplate,
                    "metadata": card,
                    "output_filename": cfile,
                })

        if not isinstance(raw_items, list):
            raise ValueError("Invalid 'items' entry in manifest: expected a list")

        items: List[ArtItem] = []
        seen_ids = set()

        for idx, entry in enumerate(raw_items, 1):
            if not isinstance(entry, dict):
                raise ValueError(f"Item #{idx} is not a valid dictionary")
            item_id = str(entry.get("id", "")).strip()
            if not item_id:
                raise ValueError(f"Item #{idx} is missing required 'id' field")
            if item_id in seen_ids:
                raise ValueError(f"Duplicate item id '{item_id}' found in manifest")
            seen_ids.add(item_id)

            prompt = str(entry.get("prompt", "")).strip()
            prompt_template = str(entry.get("prompt_template", "")).strip()
            item_meta = entry.get("metadata") or {}
            if not isinstance(item_meta, dict):
                item_meta = {"value": str(item_meta)}

            out_filename = str(entry.get("output_filename", "")).strip()

            items.append(
                ArtItem(
                    id=item_id,
                    prompt=prompt,
                    prompt_template=prompt_template,
                    metadata=item_meta,
                    output_filename=out_filename,
                )
            )

        return meta, items


# ─────────────────────────────────────────────────────────────────────────────
# 3. Prompt Template Engine
# ─────────────────────────────────────────────────────────────────────────────

class PromptEngine:
    """Safely interpolates item metadata and set-level theme/style into generation prompts."""

    @staticmethod
    def render(set_meta: ArtworkSetMeta, item: ArtItem) -> str:
        # Determine the base template string
        if item.prompt_template:
            template = item.prompt_template
        elif "{prompt}" in set_meta.default_template:
            template = set_meta.default_template
        elif item.prompt:
            template = item.prompt
        else:
            template = set_meta.default_template

        # Build context dictionary
        context: Dict[str, Any] = {
            "id": item.id,
            "prompt": item.prompt,
            "theme": set_meta.theme,
            "style": set_meta.style,
            "set_name": set_meta.name,
        }
        # Item metadata takes precedence for item-specific tokens
        context.update(item.metadata)

        # Safe formatting helper: replace {var} if found in context, leave unchanged if missing
        def replacer(match: re.Match) -> str:
            key = match.group(1).strip()
            val = context.get(key)
            if val is not None:
                return str(val)
            # Check nested metadata or lowercased
            if key.lower() in context:
                return str(context[key.lower()])
            return match.group(0)

        resolved = re.sub(r"\{([a-zA-Z0-9_\-]+)\}", replacer, template)

        # If prompt was simple and theme/style exist but weren't in template, append them cleanly
        if template == item.prompt or template == "{prompt}":
            parts = [resolved.strip()]
            if set_meta.theme and set_meta.theme not in resolved:
                parts.append(set_meta.theme.strip())
            if set_meta.style and set_meta.style not in resolved:
                parts.append(set_meta.style.strip())
            resolved = " ".join(p for p in parts if p)

        # Clean excess whitespace
        return " ".join(resolved.split())


# ─────────────────────────────────────────────────────────────────────────────
# 4. Image Processing & WebP Auto-Cropping
# ─────────────────────────────────────────────────────────────────────────────

class ImageProcessor:
    """Auto-crops empty margins, centers subjects, and encodes high-res WebP images."""

    @staticmethod
    def crop_and_maximize(
        img: Image.Image,
        target_size: Tuple[int, int] = (512, 512),
        pad: int = 10,
        autocrop: bool = True,
    ) -> Image.Image:
        converted = img.convert("RGB")
        target_w, target_h = target_size

        if not autocrop:
            return converted.resize((target_w, target_h), Image.Resampling.LANCZOS)

        # Sample corner background color
        bg_color = converted.getpixel((0, 0))
        bg = Image.new("RGB", converted.size, bg_color)
        diff = ImageChops.difference(converted, bg).point(lambda p: 255 if p > 16 else 0)
        bbox = diff.getbbox()
        if not bbox:
            return converted.resize((target_w, target_h), Image.Resampling.LANCZOS)

        cropped = converted.crop(bbox)

        avail_w = max(1, target_w - (2 * pad))
        avail_h = max(1, target_h - (2 * pad))
        scale = min(avail_w / max(1, cropped.width), avail_h / max(1, cropped.height))

        new_w = max(1, int(cropped.width * scale))
        new_h = max(1, int(cropped.height * scale))
        resized = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)

        canvas = Image.new("RGB", (target_w, target_h), bg_color)
        pos_x = (target_w - new_w) // 2
        pos_y = (target_h - new_h) // 2
        canvas.paste(resized, (pos_x, pos_y))
        return canvas

    @classmethod
    def save(
        cls,
        img: Image.Image,
        dest_path: Path,
        target_size: Tuple[int, int] = (512, 512),
        pad: int = 10,
        autocrop: bool = True,
        quality: int = 92,
        img_format: str = "webp",
    ) -> Path:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        processed = cls.crop_and_maximize(img, target_size=target_size, pad=pad, autocrop=autocrop)

        fmt = img_format.upper()
        if fmt == "WEBP":
            processed.save(dest_path, "WEBP", quality=quality, method=6)
        else:
            processed.save(dest_path, fmt, quality=quality)
        return dest_path


# ─────────────────────────────────────────────────────────────────────────────
# 5. Pluggable Backends
# ─────────────────────────────────────────────────────────────────────────────

class ArtBackend:
    """Abstract base class for art generation providers."""

    def generate(self, prompt: str, item: ArtItem, set_meta: ArtworkSetMeta) -> Image.Image:
        raise NotImplementedError


class MockBackend(ArtBackend):
    """Deterministic synthetic image generator for unit tests, dry-runs, and offline CI."""

    def generate(self, prompt: str, item: ArtItem, set_meta: ArtworkSetMeta) -> Image.Image:
        w, h = set_meta.resolution
        # Generate consistent palette from item ID
        h_val = int(hashlib.md5(item.id.encode("utf-8")).hexdigest(), 16)
        r = 40 + (h_val % 180)
        g = 40 + ((h_val >> 8) % 180)
        b = 40 + ((h_val >> 16) % 180)

        # Base ivory/clean background with a centered subject silhouette
        bg_color = (248, 246, 240)
        img = Image.new("RGB", (w, h), bg_color)
        draw = ImageDraw.Draw(img)

        # Draw a stylized framed character/subject polygon in center
        margin = max(30, int(min(w, h) * 0.15))
        cx, cy = w // 2, h // 2
        rx, ry = (w - 2 * margin) // 2, (h - 2 * margin) // 2

        # Gradient / tinted central shape
        draw.rounded_rectangle([cx - rx, cy - ry, cx + rx, cy + ry], radius=24, fill=(r, g, b), outline=(20, 20, 20), width=4)

        # Stylized emblem inside
        draw.ellipse([cx - rx // 2, cy - ry // 2, cx + rx // 2, cy + ry // 2], fill=(min(255, r + 40), min(255, g + 40), min(255, b + 40)))

        # Identifier stamp
        display_text = item.metadata.get("name") or item.id
        draw.text((cx - len(display_text) * 4, cy - 8), display_text, fill=(255, 255, 255))

        return img


class CLICommandBackend(ArtBackend):
    """Invokes an external command to produce a raw image."""

    def __init__(self, command_template: str):
        self.command_template = command_template

    def generate(self, prompt: str, item: ArtItem, set_meta: ArtworkSetMeta) -> Image.Image:
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        cmd = self.command_template.format(
            prompt=prompt,
            id=item.id,
            output_path=str(tmp_path),
            resolution=f"{set_meta.resolution[0]}x{set_meta.resolution[1]}",
        )
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode != 0:
            if tmp_path.exists():
                tmp_path.unlink()
            raise RuntimeError(f"CLI generation failed (code {res.returncode}): {res.stderr}")

        if not tmp_path.exists():
            raise FileNotFoundError(f"CLI backend did not produce output file at {tmp_path}")

        try:
            with Image.open(tmp_path) as im:
                img = im.convert("RGB")
            return img
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Contact Sheet Builder (Pure Image Review)
# ─────────────────────────────────────────────────────────────────────────────

class ContactSheetBuilder:
    """Builds clean visual inspection contact sheets displaying ONLY the images and metadata."""

    @staticmethod
    def build_html(
        set_meta: ArtworkSetMeta,
        items: List[ArtItem],
        review_dir: Optional[Path] = None,
    ) -> Path:
        out_dir = review_dir or set_meta.review_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        html_file = out_dir / "contact_sheet.html"

        cards_html: List[str] = []
        ready_count = 0

        for item in items:
            img_filename = item.get_filename(set_meta.format)
            img_path = set_meta.output_dir / img_filename
            is_ready = img_path.is_file()

            if is_ready:
                ready_count += 1
                try:
                    rel_img_path = os.path.relpath(img_path, out_dir).replace("\\", "/")
                except ValueError:
                    rel_img_path = img_path.as_uri()

                size_kb = f"{img_path.stat().st_size / 1024:.1f} KB"
                image_markup = (
                    f'<a href="{escape(rel_img_path)}" target="_blank" title="Click to inspect full resolution">'
                    f'<img loading="lazy" src="{escape(rel_img_path)}" alt="{escape(item.id)}" class="art-thumb">'
                    f'</a>'
                )
                status_pill = f'<span class="pill ready">Ready · {size_kb}</span>'
            else:
                image_markup = (
                    f'<div class="art-thumb placeholder">'
                    f'<span>⏳ Pending Artwork</span>'
                    f'</div>'
                )
                status_pill = '<span class="pill pending">Pending Generation</span>'

            resolved_prompt = PromptEngine.render(set_meta, item)
            title = item.metadata.get("name") or item.id

            meta_rows = []
            for k, v in item.metadata.items():
                if k != "name" and isinstance(v, (str, int, float)):
                    meta_rows.append(f'<span class="meta-tag"><strong>{escape(str(k))}:</strong> {escape(str(v))}</span>')
            meta_html = f'<div class="meta-tags">{" ".join(meta_rows)}</div>' if meta_rows else ""

            card = f"""
            <article class="art-card {'card-ready' if is_ready else 'card-pending'}">
                <div class="thumb-container">
                    {image_markup}
                </div>
                <div class="card-info">
                    <div class="card-title-row">
                        <h3 class="card-id">{escape(item.id)}</h3>
                        {status_pill}
                    </div>
                    <div class="item-title">{escape(str(title))}</div>
                    {meta_html}
                    <details class="prompt-details">
                        <summary>Resolved Prompt</summary>
                        <p class="prompt-text">{escape(resolved_prompt)}</p>
                    </details>
                </div>
            </article>
            """
            cards_html.append(card)

        total = len(items)
        pct = (ready_count / total * 100) if total else 0

        html_content = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(set_meta.name)} — Artwork Contact Sheet</title>
<style>
:root {{
  --bg: #f8fafc;
  --surface: #ffffff;
  --text: #0f172a;
  --text-muted: #64748b;
  --border: #e2e8f0;
  --primary: #0284c7;
  --radius: 12px;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  padding: 24px;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.5;
}}
.container {{
  max-width: 1440px;
  margin: 0 auto;
}}
header {{
  background: var(--surface);
  padding: 24px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  margin-bottom: 24px;
}}
h1 {{ margin: 0 0 8px; font-size: 1.8rem; font-weight: 800; }}
.desc {{ color: var(--text-muted); margin: 0 0 16px; font-size: 1rem; }}
.stats-bar {{
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}}
.stat {{
  background: var(--bg);
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  font-size: 0.85rem;
}}
.stat strong {{ color: var(--primary); }}
.search-bar {{
  margin: 16px 0;
  width: 100%;
}}
.search-input {{
  width: 100%;
  padding: 12px 16px;
  font-size: 1rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  outline: none;
}}
.search-input:focus {{ border-color: var(--primary); }}
.grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
}}
.art-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}}
.art-card:hover {{
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0,0,0,0.06);
}}
.thumb-container {{
  background: #f1f5f9;
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}}
.art-thumb {{
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}}
.art-thumb.placeholder {{
  color: var(--text-muted);
  font-size: 0.9rem;
  font-weight: 600;
  text-align: center;
  padding: 20px;
}}
.card-info {{
  padding: 14px;
  display: flex;
  flex-direction: column;
  flex-grow: 1;
}}
.card-title-row {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}}
.card-id {{
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #1e293b;
}}
.item-title {{
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-muted);
  margin-top: 2px;
}}
.pill {{
  font-size: 0.72rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
}}
.pill.ready {{ background: #dcfce7; color: #15803d; }}
.pill.pending {{ background: #fef3c7; color: #b45309; }}
.meta-tags {{
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 8px 0;
}}
.meta-tag {{
  background: #f1f5f9;
  color: #475569;
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 4px;
}}
.prompt-details {{
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px dashed var(--border);
  font-size: 0.75rem;
}}
.prompt-details summary {{
  cursor: pointer;
  color: var(--primary);
  font-weight: 600;
}}
.prompt-text {{
  margin: 6px 0 0;
  color: #334155;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
}}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>{escape(set_meta.name)} — Contact Sheet</h1>
    {f'<p class="desc">{escape(set_meta.description)}</p>' if set_meta.description else ''}
    <div class="stats-bar">
      <div class="stat">Total Target Artworks: <strong>{total}</strong></div>
      <div class="stat">Available on Disk: <strong>{ready_count}</strong> ({pct:.1f}%)</div>
      <div class="stat">Target Geometry: <strong>{set_meta.resolution[0]}×{set_meta.resolution[1]} {set_meta.format.upper()}</strong></div>
      <div class="stat">Output Directory: <code>{escape(str(set_meta.output_dir))}</code></div>
    </div>
  </header>

  <div class="search-bar">
    <input type="search" id="filterInput" class="search-input" placeholder="Search artwork by ID or metadata name..." oninput="filterCards()">
  </div>

  <main class="grid" id="artGrid">
    {"".join(cards_html)}
  </main>
</div>

<script>
function filterCards() {{
  const query = document.getElementById('filterInput').value.toLowerCase();
  const cards = document.querySelectorAll('.art-card');
  cards.forEach(card => {{
    const text = card.textContent.toLowerCase();
    card.style.display = text.includes(query) ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""

        html_file.write_text(html_content, encoding="utf-8")
        return html_file


# ─────────────────────────────────────────────────────────────────────────────
# 7. Art Generator Orchestrator & CLI
# ─────────────────────────────────────────────────────────────────────────────

class ArtGenerator:
    """Main orchestrator coordinating manifest loading, image generation, and review sheets."""

    def __init__(
        self,
        set_meta: ArtworkSetMeta,
        items: List[ArtItem],
        backend: Optional[ArtBackend] = None,
    ):
        self.meta = set_meta
        self.items = items
        self.backend = backend or MockBackend()

    def status(self) -> Dict[str, Any]:
        self.meta.output_dir.mkdir(parents=True, exist_ok=True)
        ready_items = []
        missing_items = []

        for item in self.items:
            f = self.meta.output_dir / item.get_filename(self.meta.format)
            if f.is_file():
                ready_items.append(item)
            else:
                missing_items.append(item)

        return {
            "total": len(self.items),
            "ready": len(ready_items),
            "missing": len(missing_items),
            "ready_items": ready_items,
            "missing_items": missing_items,
            "output_dir": self.meta.output_dir,
            "format": self.meta.format,
            "resolution": self.meta.resolution,
        }

    def print_status(self) -> None:
        st = self.status()
        print("=================================================================")
        print(f"Artwork Set:     {self.meta.name}")
        print(f"Destination:     {st['output_dir']}")
        print(f"Format/Geometry: {st['resolution'][0]}x{st['resolution'][1]} {st['format'].upper()} (Quality {self.meta.quality})")
        print("-----------------------------------------------------------------")
        pct = (st['ready'] / st['total'] * 100) if st['total'] else 0
        print(f"Total Items:     {st['total']}")
        print(f"  Ready:         {st['ready']} ({pct:.1f}%)")
        print(f"  Missing:       {st['missing']}")
        print("=================================================================")
        if st["missing_items"]:
            print("Next missing items:")
            for m in st["missing_items"][:8]:
                title = m.metadata.get("name") or m.id
                print(f"  - {m.id} : {title}")
            if len(st["missing_items"]) > 8:
                print(f"    ... and {len(st['missing_items']) - 8} more.")

    def export_prompts(self) -> List[Dict[str, Any]]:
        results = []
        for item in self.items:
            resolved = PromptEngine.render(self.meta, item)
            results.append({
                "id": item.id,
                "filename": item.get_filename(self.meta.format),
                "resolved_prompt": resolved,
                "metadata": item.metadata,
            })
        return results

    def generate(
        self,
        force: bool = False,
        target_id: Optional[str] = None,
        on_progress: Optional[Callable[[int, int, str, Path], None]] = None,
    ) -> List[Path]:
        self.meta.output_dir.mkdir(parents=True, exist_ok=True)
        items_to_run = self.items
        if target_id:
            items_to_run = [i for i in self.items if i.id == target_id]
            if not items_to_run:
                raise ValueError(f"Target item ID '{target_id}' not found in manifest")

        generated_paths: List[Path] = []
        total = len(items_to_run)

        for idx, item in enumerate(items_to_run, 1):
            out_filename = item.get_filename(self.meta.format)
            out_path = self.meta.output_dir / out_filename

            if out_path.is_file() and not force:
                continue

            resolved_prompt = PromptEngine.render(self.meta, item)
            raw_img = self.backend.generate(resolved_prompt, item, self.meta)

            saved_path = ImageProcessor.save(
                img=raw_img,
                dest_path=out_path,
                target_size=self.meta.resolution,
                pad=self.meta.pad,
                autocrop=self.meta.autocrop,
                quality=self.meta.quality,
                img_format=self.meta.format,
            )
            generated_paths.append(saved_path)

            if on_progress:
                on_progress(idx, total, item.id, saved_path)

        return generated_paths

    def build_review(self) -> Path:
        return ContactSheetBuilder.build_html(self.meta, self.items)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", "-m", required=True, help="Path to declarative YAML manifest")
    parser.add_argument("--status", action="store_true", help="Report status of artwork set")
    parser.add_argument("--generate", action="store_true", help="Generate missing artwork items")
    parser.add_argument("--force", action="store_true", help="Regenerate items even if they exist")
    parser.add_argument("--item", help="Target a specific item ID")
    parser.add_argument("--review", action="store_true", help="Generate HTML review contact sheet")
    parser.add_argument("--export-prompts", action="store_true", help="Print resolved prompts to stdout")
    parser.add_argument("--backend", choices=["mock", "cli"], default="mock", help="Generator backend")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    meta, items = ManifestParser.load(manifest_path)

    backend: ArtBackend = MockBackend()
    if args.backend == "cli":
        if not meta.cli_command:
            raise ValueError("Backend 'cli' requested, but manifest does not specify artwork_set.cli_command")
        backend = CLICommandBackend(meta.cli_command)

    orchestrator = ArtGenerator(meta, items, backend=backend)

    if args.export_prompts:
        prompts = orchestrator.export_prompts()
        print(json.dumps(prompts, indent=2))
        return

    if args.status or (not args.generate and not args.review):
        orchestrator.print_status()
        return

    if args.generate:
        print(f"Generating artwork for set '{meta.name}' using {args.backend} backend...")
        def progress(cur, tot, item_id, path):
            print(f"  [{cur}/{tot}] Generated {item_id} -> {path.name}")
        paths = orchestrator.generate(force=args.force, target_id=args.item, on_progress=progress)
        print(f"Generation complete: {len(paths)} artwork file(s) saved.")

    if args.review:
        sheet = orchestrator.build_review()
        print(f"Review contact sheet built: {sheet}")


if __name__ == "__main__":
    main()
