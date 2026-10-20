"""Unit and integration tests for generic art generator."""

import io
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image
import yaml

from tools.art_generator import (
    ArtGenerator,
    ArtItem,
    ArtworkSetMeta,
    ContactSheetBuilder,
    ImageProcessor,
    ManifestParser,
    MockBackend,
    PromptEngine,
)


class TestManifestParser(unittest.TestCase):
    """Verify declarative YAML manifest parsing and validation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_valid_manifest(self):
        manifest_content = {
            "artwork_set": {
                "name": "test_pack",
                "description": "Test Pack Description",
                "output_dir": "output",
                "review_dir": "review",
                "theme": "Cyberpunk 2099",
                "style": "Neon cel-shaded, ink outlines",
                "resolution": "512x512",
                "quality": 90,
                "autocrop": True,
            },
            "items": [
                {
                    "id": "item-01",
                    "prompt": "Hacker at terminal",
                    "metadata": {"name": "Cipher", "role": "Infiltrator"},
                },
                {
                    "id": "item-02",
                    "prompt_template": "{name} the {role} in {theme}. {style}",
                    "metadata": {"name": "Nova", "role": "Enforcer"},
                },
            ],
        }
        manifest_file = self.dir_path / "manifest.yaml"
        manifest_file.write_text(yaml.dump(manifest_content), encoding="utf-8")

        meta, items = ManifestParser.load(manifest_file)
        self.assertEqual(meta.name, "test_pack")
        self.assertEqual(meta.theme, "Cyberpunk 2099")
        self.assertEqual(meta.style, "Neon cel-shaded, ink outlines")
        self.assertEqual(meta.resolution, (512, 512))
        self.assertEqual(meta.quality, 90)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].id, "item-01")
        self.assertEqual(items[1].metadata["name"], "Nova")

    def test_duplicate_item_id_raises_error(self):
        manifest_content = {
            "artwork_set": {"name": "dupe_test"},
            "items": [
                {"id": "item-01", "prompt": "First"},
                {"id": "item-01", "prompt": "Second"},
            ],
        }
        manifest_file = self.dir_path / "dupe.yaml"
        manifest_file.write_text(yaml.dump(manifest_content), encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            ManifestParser.load(manifest_file)
        self.assertIn("Duplicate item id", str(ctx.exception))

    def test_missing_id_raises_error(self):
        manifest_content = {
            "artwork_set": {"name": "missing_id_test"},
            "items": [{"prompt": "No id here"}],
        }
        manifest_file = self.dir_path / "no_id.yaml"
        manifest_file.write_text(yaml.dump(manifest_content), encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            ManifestParser.load(manifest_file)
        self.assertIn("missing required 'id'", str(ctx.exception))

    def test_load_manifest_with_json_data_and_template(self):
        import json
        cards_data = [
            {"id": "card-01", "name": "Valkyrie", "role": "Aerial Scout", "rarity": "rare"},
            {"id": "card-02", "name": "Titan", "role": "Siege Tank", "rarity": "legendary"},
        ]
        cards_file = self.dir_path / "cards.json"
        cards_file.write_text(json.dumps(cards_data), encoding="utf-8")

        manifest_content = {
            "artwork_set": {
                "name": "mecha_squad",
                "theme": "Anime dieselpunk mecha",
                "style": "Clean vector lines",
            },
            "item_template": {
                "prompt_template": "Pilot {name} commanding {role}. {style}",
            },
            "data_file": "cards.json",
        }
        manifest_file = self.dir_path / "manifest.yaml"
        manifest_file.write_text(yaml.dump(manifest_content), encoding="utf-8")

        meta, items = ManifestParser.load(manifest_file)
        self.assertEqual(meta.name, "mecha_squad")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].id, "card-01")
        self.assertEqual(items[0].metadata["name"], "Valkyrie")
        self.assertEqual(items[0].metadata["role"], "Aerial Scout")
        self.assertEqual(items[0].prompt_template, "Pilot {name} commanding {role}. {style}")

        # Render prompt to verify end-to-end interpolation
        rendered = PromptEngine.render(meta, items[0])
        self.assertIn("Pilot Valkyrie commanding Aerial Scout", rendered)
        self.assertIn("Clean vector lines", rendered)


class TestPromptEngine(unittest.TestCase):
    """Verify prompt templating and metadata interpolation."""

    def setUp(self):
        self.meta = ArtworkSetMeta(
            name="space_fleet",
            theme="Deep space starship armada",
            style="Hard sci-fi technical illustration, blueprint details",
            default_template="{ship_name} class {ship_class}. {theme}. {style}",
        )

    def test_render_with_metadata_template(self):
        item = ArtItem(
            id="ship-01",
            prompt_template="Flagship {ship_name} ({registry}) commanding {ship_class}. {style}",
            metadata={
                "ship_name": "Aegis",
                "registry": "NX-01",
                "ship_class": "Heavy Dreadnought",
            },
        )
        rendered = PromptEngine.render(self.meta, item)
        self.assertIn("Flagship Aegis (NX-01) commanding Heavy Dreadnought.", rendered)
        self.assertIn("Hard sci-fi technical illustration", rendered)

    def test_safe_unresolved_variables(self):
        item = ArtItem(
            id="ship-02",
            prompt_template="{ship_name} equipped with {missing_gear}. {style}",
            metadata={"ship_name": "Valiant"},
        )
        rendered = PromptEngine.render(self.meta, item)
        self.assertIn("Valiant", rendered)
        self.assertIn("{missing_gear}", rendered)  # Safe: not crash

    def test_default_template_fallback(self):
        item = ArtItem(
            id="ship-03",
            metadata={"ship_name": "Prometheus", "ship_class": "Explorer"},
        )
        rendered = PromptEngine.render(self.meta, item)
        self.assertIn("Prometheus class Explorer.", rendered)
        self.assertIn("Deep space starship armada.", rendered)


class TestImageProcessor(unittest.TestCase):
    """Verify auto-crop, Lanczos scaling, and WebP encoding."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_crop_and_maximize(self):
        # Create a 200x200 canvas with a small 50x50 central square
        raw = Image.new("RGB", (200, 200), (240, 240, 240))
        for x in range(75, 125):
            for y in range(75, 125):
                raw.putpixel((x, y), (20, 20, 100))

        processed = ImageProcessor.crop_and_maximize(raw, target_size=(512, 512), pad=10, autocrop=True)
        self.assertEqual(processed.size, (512, 512))

        # Center should contain the scaled blue square
        center_pixel = processed.getpixel((256, 256))
        self.assertEqual(center_pixel, (20, 20, 100))

    def test_save_webp(self):
        raw = Image.new("RGB", (100, 100), (255, 0, 0))
        out_file = self.dir_path / "test.webp"

        saved = ImageProcessor.save(raw, out_file, target_size=(256, 256), quality=92, img_format="webp")
        self.assertTrue(saved.is_file())
        self.assertTrue(saved.stat().st_size > 0)

        with Image.open(saved) as im:
            self.assertEqual(im.format, "WEBP")
            self.assertEqual(im.size, (256, 256))


class TestContactSheetBuilder(unittest.TestCase):
    """Verify clean image-only contact sheet generation with zero card flair."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)
        self.output_dir = self.dir_path / "images"
        self.review_dir = self.dir_path / "review"
        self.output_dir.mkdir(parents=True)

        self.meta = ArtworkSetMeta(
            name="solarpunk_cities",
            output_dir=self.output_dir,
            review_dir=self.review_dir,
            theme="Eco-futurism",
            style="Crisp architectural watercolors",
        )
        self.items = [
            ArtItem(id="city-01", prompt="Hanging gardens skyscraper", metadata={"name": "Verdant Spire"}),
            ArtItem(id="city-02", prompt="Solar canopy transit station", metadata={"name": "Canopy Hub"}),
        ]

        # Generate a dummy WebP for city-01
        dummy_img = Image.new("RGB", (256, 256), (30, 120, 30))
        ImageProcessor.save(dummy_img, self.output_dir / "city-01.webp")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_contact_sheet_html_content(self):
        html_path = ContactSheetBuilder.build_html(self.meta, self.items, self.review_dir)
        self.assertTrue(html_path.is_file())

        content = html_path.read_text(encoding="utf-8")
        self.assertIn("solarpunk_cities — Contact Sheet", content)
        self.assertIn("city-01", content)
        self.assertIn("Verdant Spire", content)
        self.assertIn("city-02", content)
        self.assertIn("Pending Generation", content)

        # STRICT REQUIREMENT: ZERO card flair (no hockey ribbons, no evolution tiers)
        self.assertNotIn("stats-ribbon", content)
        self.assertNotIn("evolution-badge", content)
        self.assertNotIn("jersey-patch", content)
        self.assertNotIn("Rinkside", content)
        self.assertNotIn("Spotlight", content)
        self.assertNotIn("Garden Glow", content)


class TestArtGeneratorOrchestrator(unittest.TestCase):
    """Verify full orchestration lifecycle (status, generate, review, export)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)
        self.output_dir = self.dir_path / "art"
        self.review_dir = self.dir_path / "review"

        self.meta = ArtworkSetMeta(
            name="mythic_creatures",
            output_dir=self.output_dir,
            review_dir=self.review_dir,
            theme="Ancient Bestiary",
            style="Intricate pen and ink engraving",
            resolution=(256, 256),
        )
        self.items = [
            ArtItem(id="beast-griffin", prompt="Griffin perched on cliff", metadata={"name": "Alpine Griffin"}),
            ArtItem(id="beast-kraken", prompt="Kraken rising from abyss", metadata={"name": "Abyssal Kraken"}),
        ]
        self.orchestrator = ArtGenerator(self.meta, self.items, backend=MockBackend())

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_status_and_generation_flow(self):
        # 1. Initial status
        st1 = self.orchestrator.status()
        self.assertEqual(st1["total"], 2)
        self.assertEqual(st1["ready"], 0)
        self.assertEqual(st1["missing"], 2)

        # 2. Generate all items
        generated = self.orchestrator.generate()
        self.assertEqual(len(generated), 2)
        for p in generated:
            self.assertTrue(p.is_file())
            with Image.open(p) as im:
                self.assertEqual(im.size, (256, 256))
                self.assertEqual(im.format, "WEBP")

        # 3. Status after generation
        st2 = self.orchestrator.status()
        self.assertEqual(st2["ready"], 2)
        self.assertEqual(st2["missing"], 0)

        # 4. Idempotent: without force, generate returns 0 files
        generated_again = self.orchestrator.generate(force=False)
        self.assertEqual(len(generated_again), 0)

        # 5. Build review contact sheet
        sheet_path = self.orchestrator.build_review()
        self.assertTrue(sheet_path.is_file())

        # 6. Export prompts
        prompts = self.orchestrator.export_prompts()
        self.assertEqual(len(prompts), 2)
        self.assertEqual(prompts[0]["id"], "beast-griffin")
        self.assertIn("Griffin perched on cliff", prompts[0]["resolved_prompt"])


if __name__ == "__main__":
    unittest.main()
