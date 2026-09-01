#!/usr/bin/env python3
"""不打真实 API 的运行时单测。"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gen_image  # noqa: E402
import match_pack  # noqa: E402
import queue_pack  # noqa: E402
import swap_fast  # noqa: E402
import update_skill  # noqa: E402


class SizeTests(unittest.TestCase):
    def test_ratio_passthrough(self) -> None:
        self.assertEqual(gen_image.size_to_ratio("1:1"), "1:1")
        self.assertEqual(gen_image.size_to_ratio("4:5"), "4:5")

    def test_pixel_maps_to_ratio(self) -> None:
        self.assertEqual(gen_image.size_to_ratio("1024x1024"), "1:1")
        self.assertEqual(gen_image.size_to_ratio("1024x1536"), "2:3")

    def test_sync_size_collapses_portrait(self) -> None:
        self.assertEqual(gen_image.sync_size("9:16"), "1024x1536")
        self.assertEqual(gen_image.sync_size("1:1"), "1024x1024")


class ProviderTests(unittest.TestCase):
    def test_detect_from_explicit(self) -> None:
        self.assertEqual(gen_image.detect_provider("", "", "grok"), "grok")
        self.assertEqual(gen_image.detect_provider("", "", "xai"), "grok")

    def test_detect_from_model(self) -> None:
        self.assertEqual(gen_image.detect_provider("", "gemini-3.1-flash-image", None), "gemini")
        self.assertEqual(gen_image.detect_provider("", "gpt-image-2", None), "openai")

    def test_official_url_ignores_configured(self) -> None:
        self.assertEqual(
            gen_image.resolve_base_url("openai", "https://proxy.example/v1"),
            "https://api.openai.com/v1",
        )

    def test_custom_keeps_url(self) -> None:
        self.assertEqual(
            gen_image.resolve_base_url("custom", "https://gateway.example/v1"),
            "https://gateway.example/v1",
        )


class BackoffTests(unittest.TestCase):
    def test_rate_limit_retries(self) -> None:
        self.assertTrue(gen_image.is_backoff_error("HTTP 429 rate_limit"))
        self.assertTrue(gen_image.is_backoff_error("接口连接失败或超时"))

    def test_auth_does_not_retry(self) -> None:
        self.assertFalse(gen_image.is_backoff_error("HTTP 401 unauthorized"))
        self.assertFalse(gen_image.is_backoff_error("缺少配置 IMG_API_KEY"))


class DownloadUrlTests(unittest.TestCase):
    def test_rejects_file_and_localhost(self) -> None:
        with self.assertRaises(gen_image.GenError):
            gen_image.assert_download_url("file:///tmp/x.png")
        with self.assertRaises(gen_image.GenError):
            gen_image.assert_download_url("http://127.0.0.1/x.png")
        with self.assertRaises(gen_image.GenError):
            gen_image.assert_download_url("http://192.168.1.8/x.png")

    def test_allows_https_host(self) -> None:
        gen_image.assert_download_url("https://cdn.example.com/a.png")


class MatchPackTests(unittest.TestCase):
    def test_named_template_is_first(self) -> None:
        result = match_pack.rank_plans("使用 dsimage 模板：箱包单品报价模板，基于这张图出全套")
        self.assertEqual(len(result["plans"]), 3)
        self.assertIn("箱包单品报价模板", result["plans"][0]["title"])
        self.assertTrue(result["plans"][0]["slots"])
        self.assertEqual(result["plans"][0]["kind"], "rules")
        self.assertTrue(result["plans"][0]["label"].startswith("模板「"))
        self.assertEqual(
            result["plans"][0]["path"],
            "templates/BeautyU/01-箱包单品报价模板/01-箱包单品报价模板.json",
        )

    def test_swap_intent_notes_when_no_master(self) -> None:
        result = match_pack.rank_plans("使用 dsimage 替换模板：某某，把这个型号换进去")
        self.assertTrue(any("母版" in n for n in result["notes"]))

    def test_fast_swap_points_to_masters(self) -> None:
        result = match_pack.rank_plans("使用 dsimage 快速换货，把这个文件夹里的书包换进样板")
        self.assertTrue(any("FAST_SWAP" in n or "快速换货" in n for n in result["notes"]))
        self.assertTrue(any("母版" in n for n in result["notes"]))

    def test_amazon_set_uses_starter(self) -> None:
        result = match_pack.rank_plans("使用 dsimage 来制作，基于这张衣服图做 Amazon 详情页")
        self.assertEqual(result["plans"][0]["title"], "默认电商模板")

    def test_xiaohongshu_uses_scene(self) -> None:
        result = match_pack.rank_plans("使用 dsimage，用这张产品图出 3 张小红书图，要真实拍照感")
        self.assertEqual(result["plans"][0]["kind"], "scene")
        self.assertIn("社交", result["plans"][0]["title"])

    def test_missing_named_does_not_pretend_hero(self) -> None:
        result = match_pack.rank_plans("使用 dsimage 模板：不存在的模板")
        self.assertTrue(result["notes"])
        self.assertNotEqual(result["plans"][0]["path"], "scenes/01-hero-image.json")
        self.assertEqual(result["plans"][0]["title"], "默认电商模板")


class MergeTests(unittest.TestCase):
    def test_text_rules_keep_extra_keys_only(self) -> None:
        notes: list[str] = []
        merged = update_skill.merge_text_rules(
            {"headline": "new"},
            {"headline": "user old", "extra": "keep"},
            notes,
            "",
        )
        self.assertEqual(merged["headline"], "new")
        self.assertEqual(merged["extra"], "keep")

    def test_is_library_json_client_root(self) -> None:
        self.assertTrue(
            update_skill.is_library_json(Path("references/templates/01-默认电商模板.json"))
        )
        self.assertTrue(
            update_skill.is_library_json(
                Path("references/templates/01-默认电商模板/01-默认电商模板.json")
            )
        )
        self.assertTrue(
            update_skill.is_library_json(Path("references/templates/BeautyU/要求.json"))
        )
        self.assertTrue(
            update_skill.is_library_json(
                Path("references/templates/BeautyU/01-箱包单品报价模板.json")
            )
        )
        self.assertTrue(
            update_skill.is_library_json(
                Path("references/templates/BeautyU/01-箱包单品报价模板/01-箱包单品报价模板.json")
            )
        )
        self.assertTrue(
            update_skill.is_library_json(
                Path("references/templates/BeautyU/风格/01-旧.json")
            )
        )

    def test_client_meta_lists_template_files(self) -> None:
        import json

        client = ROOT.parent / "references" / "templates" / "BeautyU"
        meta = json.loads((client / "要求.json").read_text(encoding="utf-8"))
        pkgs = sorted(
            p.name
            for p in client.iterdir()
            if p.is_dir() and (p / f"{p.name}.json").is_file()
        )
        self.assertEqual(sorted(meta["templates"]), pkgs)

    def test_merge_client_meta_unions_templates(self) -> None:
        merged, notes = update_skill.merge_client_meta(
            {"templates": ["01-a"], "name": "new"},
            {"templates": ["02-b"], "name": "user"},
            "t",
        )
        self.assertEqual(merged["name"], "user")
        self.assertIn("01-a", merged["templates"])
        self.assertIn("02-b", merged["templates"])
        self.assertTrue(any("templates" in n for n in notes))

    def test_migrate_kind_folders_to_client_root(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            client = dest / "references" / "templates" / "Acme"
            kind = client / "风格"
            kind.mkdir(parents=True)
            (kind / "01-测试.json").write_text("{}", encoding="utf-8")
            side = kind / "01-测试"
            side.mkdir()
            (side / "h1.png").write_text("x", encoding="utf-8")
            (client / "要求.json").write_text("{}", encoding="utf-8")
            report: list[str] = []
            update_skill.migrate_flat_templates(dest, report)
            pkg = client / "01-测试"
            self.assertTrue((pkg / "01-测试.json").is_file())
            self.assertTrue((pkg / "h1.png").is_file())
            self.assertFalse((client / "01-测试.json").is_file())
            self.assertFalse(kind.exists())


def _touch_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-image")


def _write_png(path: Path, width: int, height: int, rgb: tuple[int, int, int] = (200, 100, 50)) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


class QueuePackTests(unittest.TestCase):
    def _batch(self, tmp: Path) -> tuple[Path, Path, dict]:
        source = tmp / "春季新品"
        output = tmp / "春季新品-成图"
        for name in ("双肩包-黑", "双肩包-米", "登机箱"):
            _touch_image(source / name / "正面.jpg")
        args = argparse.Namespace(
            source=str(source),
            output=str(output),
            template="templates/BeautyU/01-箱包单品报价模板/01-箱包单品报价模板.json",
            lock=None,
            only=[],
            skip=["登机箱"],
            workers=3,
            concurrency=None,
            notes="字不要改",
        )
        brief_path = queue_pack.init_brief(args)
        brief = queue_pack.load_brief(brief_path)
        return brief_path, output, brief

    def test_init_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            brief_path, output, brief = self._batch(Path(tmp))
            self.assertTrue(brief_path.is_file())
            self.assertEqual(brief["notes"], "字不要改")
            self.assertEqual(brief["gen_concurrency"], 32)
            self.assertEqual(queue_pack.clamp_gen_concurrency(99), 64)
            self.assertTrue(brief.get("style_lock"))
            rows = queue_pack.scan(brief)
            by_name = {row["name"]: row["status"] for row in rows}
            self.assertEqual(by_name["双肩包-黑"], "prompt")
            self.assertEqual(by_name["双肩包-米"], "prompt")
            self.assertEqual(by_name["登机箱"], "skip")
            self.assertEqual(
                queue_pack.next_products(rows, 3, retry=False),
                sorted(["双肩包-黑", "双肩包-米"]),
            )
            self.assertEqual(output, Path(brief["output_dir"]))

    def test_jobs_without_png_is_gen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _brief_path, output, brief = self._batch(Path(tmp))
            jobs_dir = output / "_prompts" / "双肩包-黑"
            jobs_dir.mkdir(parents=True)
            (jobs_dir / "jobs.json").write_text(
                json.dumps({
                    "output_dir": "../../双肩包-黑",
                    "jobs": [{"slot": "H1", "prompt": "hero"}],
                }),
                encoding="utf-8",
            )
            rows = queue_pack.scan(brief)
            by_name = {row["name"]: row["status"] for row in rows}
            self.assertEqual(by_name["双肩包-黑"], "gen")
            self.assertEqual(queue_pack.next_products(rows, 3, retry=False), ["双肩包-米"])
            self.assertEqual(queue_pack.next_products(rows, 3, retry=True), ["双肩包-米", "双肩包-黑"])

    def test_complete_slots_are_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _brief_path, output, brief = self._batch(Path(tmp))
            name = "双肩包-黑"
            jobs_dir = output / "_prompts" / name
            jobs_dir.mkdir(parents=True)
            (jobs_dir / "jobs.json").write_text(
                json.dumps({
                    "output_dir": f"../../{name}",
                    "jobs": [
                        {"slot": "H1", "prompt": "hero"},
                        {"slot": "H2", "prompt": "detail"},
                    ],
                }),
                encoding="utf-8",
            )
            _touch_image(output / name / "h1.png")
            _touch_image(output / name / "h2.png")
            rows = queue_pack.scan(brief)
            by_name = {row["name"]: row["status"] for row in rows}
            self.assertEqual(by_name[name], "done")


class FastSwapTests(unittest.TestCase):
    def _fast_batch(self, tmp: Path, **kwargs) -> tuple[Path, Path, dict]:
        source = tmp / "春季新品"
        output = tmp / "春季新品-成图"
        masters = tmp / "样板"
        _touch_image(masters / "h1.png")
        _touch_image(masters / "h4-背面.png")
        _touch_image(source / "双肩包-黑" / "正面.jpg")
        _touch_image(source / "双肩包-米" / "正面.jpg")
        _touch_image(source / "双肩包-米" / "背面.jpg")
        args = argparse.Namespace(
            source=str(source),
            output=str(output),
            template=None,
            lock=None,
            only=[],
            skip=[],
            workers=3,
            concurrency=None,
            notes="",
            fast=True,
            masters=str(masters),
            category="双肩包",
            max_px=800,
            max_bytes="2MB",
            swap_prompt=None,
            pilot="双肩包-黑",
        )
        for key, value in kwargs.items():
            setattr(args, key, value)
        brief_path = queue_pack.init_brief(args)
        return brief_path, output, queue_pack.load_brief(brief_path)

    def test_rules_template_without_masters_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "春季新品"
            _touch_image(source / "双肩包-黑" / "正面.jpg")
            args = argparse.Namespace(
                source=str(source),
                output=str(Path(tmp) / "out"),
                template="templates/BeautyU/01-箱包单品报价模板/01-箱包单品报价模板.json",
                lock=None,
                only=[],
                skip=[],
                workers=3,
                concurrency=None,
                notes="",
                fast=True,
                masters=None,
                category="双肩包",
                max_px=None,
                max_bytes=None,
                swap_prompt=None,
                pilot=None,
            )
            with self.assertRaises(SystemExit):
                queue_pack.init_brief(args)

    def test_init_infers_pack_and_deliver(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            brief_path, _output, brief = self._fast_batch(Path(tmp))
            self.assertTrue(brief_path.is_file())
            self.assertEqual(brief["run"], "fast")
            self.assertEqual(brief["lock"], "master")
            self.assertEqual(brief["category"], "双肩包")
            self.assertEqual(brief["deliver"]["max_px"], 800)
            self.assertEqual(brief["deliver"]["max_bytes"], 2 * 1024 * 1024)
            self.assertEqual(brief.get("inspect_every"), 0)
            self.assertEqual(brief["generation"]["resolution"], "1k")
            slots = {item["slot"]: item for item in brief["pack"]}
            self.assertEqual(slots["H1"]["product_ref"], "front")
            self.assertEqual(slots["H4"]["product_ref"], "back")
            self.assertEqual(brief["swap_prompt"], swap_fast.DEFAULT_PROMPT)
            self.assertIn("Replace only the product", brief["swap_prompt"])

    def test_pilot_skips_missing_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            brief_path, output, brief = self._fast_batch(Path(tmp))
            report = swap_fast.fill_product(brief, "双肩包-黑")
            self.assertEqual(report["jobs"], 1)
            self.assertEqual(report["skipped"][0]["slot"], "H4")
            jobs = json.loads((output / "_prompts" / "双肩包-黑" / "jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(jobs["jobs"][0]["slot"], "H1")
            self.assertEqual(jobs["jobs"][0]["prompt_file"], "../swap_prompt.txt")
            self.assertEqual(jobs["jobs"][0]["resolution"], "1k")
            self.assertEqual(jobs["defaults"]["resolution"], "1k")
            self.assertEqual(len(jobs["jobs"][0]["image"]), 2)
            self.assertTrue(jobs["jobs"][0]["image"][0].endswith("h1.png"))
            self.assertTrue(jobs["jobs"][0]["image"][1].endswith("正面.jpg"))
            prompt = (output / "_prompts" / "swap_prompt.txt").read_text(encoding="utf-8")
            self.assertIn("Keep layout, text, icons, and background unchanged", prompt)
            rows = queue_pack.scan(queue_pack.load_brief(brief_path))
            by_name = {row["name"]: row["status"] for row in rows}
            self.assertEqual(by_name["双肩包-黑"], "gen")
            self.assertEqual(by_name["双肩包-米"], "prompt")

    def test_blast_fills_remaining_and_uses_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _brief_path, output, brief = self._fast_batch(Path(tmp))
            swap_fast.fill_product(brief, "双肩包-黑")
            reports = swap_fast.fill_products(brief, ["双肩包-黑", "双肩包-米"])
            rice = next(item for item in reports if item["name"] == "双肩包-米")
            self.assertEqual(rice["jobs"], 2)
            jobs = json.loads((output / "_prompts" / "双肩包-米" / "jobs.json").read_text(encoding="utf-8"))
            by_slot = {job["slot"]: job for job in jobs["jobs"]}
            self.assertTrue(by_slot["H4"]["image"][1].endswith("背面.jpg"))

    def test_set_prompt_unlocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            brief_path, output, brief = self._fast_batch(Path(tmp))
            queue_pack.apply_set_prompt(brief, "Replace the bag only.")
            queue_pack.persist_brief(brief_path, brief)
            saved = queue_pack.load_brief(brief_path)
            self.assertEqual(saved["swap_prompt"], "Replace the bag only.")
            self.assertFalse(saved["prompt_locked"])
            text = (output / "_prompts" / "swap_prompt.txt").read_text(encoding="utf-8")
            self.assertIn("Replace the bag only", text)

    def test_pick_product_image_does_not_use_front_for_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "品"
            _touch_image(folder / "正面.jpg")
            self.assertIsNone(swap_fast.pick_product_image(folder, "back"))
            _touch_image(folder / "背面.jpg")
            picked = swap_fast.pick_product_image(folder, "back")
            self.assertIsNotNone(picked)
            self.assertEqual(picked.name, "背面.jpg")

    def test_parse_bytes(self) -> None:
        self.assertEqual(swap_fast.parse_bytes("2MB"), 2 * 1024 * 1024)
        self.assertEqual(swap_fast.parse_bytes(800), 800)

    def test_parse_resolution_rejects_pixels(self) -> None:
        with self.assertRaises(SystemExit):
            swap_fast.parse_resolution("800")
        with self.assertRaises(SystemExit):
            swap_fast.parse_resolution("1024x1024")
        with self.assertRaises(SystemExit):
            swap_fast.parse_resolution("800*800")
        self.assertEqual(swap_fast.parse_resolution("2k"), "2k")

    def test_ratio_from_pixels(self) -> None:
        self.assertEqual(swap_fast.ratio_from_wh(800, 800), "1:1")
        self.assertEqual(swap_fast.ratio_from_wh(1920, 1080), "16:9")
        self.assertEqual(swap_fast.ratio_from_wh(1080, 1920), "9:16")
        self.assertEqual(swap_fast.ratio_from_wh(1024, 1280), "4:5")
        parsed = swap_fast.parse_output_size("800*800")
        self.assertEqual(parsed["ratio"], "1:1")
        self.assertEqual(parsed["width"], 800)
        self.assertEqual(parsed["height"], 800)

    def test_infer_pack_reads_master_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            masters = Path(tmp) / "样板"
            _write_png(masters / "h1.png", 16, 9)
            _write_png(masters / "h4-背面.png", 16, 9)
            pack = swap_fast.infer_pack(masters)
            by_slot = {item["slot"]: item for item in pack}
            self.assertEqual(by_slot["H1"]["ratio"], "16:9")
            self.assertEqual(by_slot["H4"]["ratio"], "16:9")

    def test_output_size_square_rejects_widescreen_masters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "春季新品"
            masters = Path(tmp) / "样板"
            _write_png(masters / "h1.png", 16, 9)
            _touch_image(source / "双肩包-黑" / "正面.jpg")
            args = argparse.Namespace(
                source=str(source),
                output=str(Path(tmp) / "out"),
                template=None,
                lock=None,
                only=[],
                skip=[],
                workers=3,
                concurrency=None,
                notes="",
                fast=True,
                masters=str(masters),
                category="双肩包",
                max_px=None,
                max_bytes=None,
                output_size="800x800",
                swap_prompt=None,
                pilot=None,
            )
            with self.assertRaises(SystemExit):
                queue_pack.init_brief(args)

    def test_output_size_square_on_square_masters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _brief_path, _output, brief = self._fast_batch(Path(tmp), output_size="800x800")
            self.assertEqual(brief["deliver"]["width"], 800)
            self.assertEqual(brief["deliver"]["height"], 800)
            self.assertEqual(brief["deliver"]["ratio"], "1:1")

    def test_fill_jobs_use_inferred_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _brief_path, output, brief = self._fast_batch(Path(tmp))
            swap_fast.fill_product(brief, "双肩包-黑")
            jobs = json.loads((output / "_prompts" / "双肩包-黑" / "jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(jobs["jobs"][0]["size"], "1:1")
            self.assertEqual(jobs["defaults"]["size"], "1:1")

    def test_resolution_override_lands_in_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _brief_path, output, brief = self._fast_batch(Path(tmp), resolution="2k")
            self.assertEqual(brief["generation"]["resolution"], "2k")
            swap_fast.fill_product(brief, "双肩包-黑")
            jobs = json.loads((output / "_prompts" / "双肩包-黑" / "jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(jobs["defaults"]["resolution"], "2k")
            self.assertEqual(jobs["jobs"][0]["resolution"], "2k")

    def test_inspect_every_limits_wave(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            brief_path, output, brief = self._fast_batch(Path(tmp), inspect_every=1)
            self.assertEqual(brief["inspect_every"], 1)
            swap_fast.fill_products(brief, ["双肩包-黑", "双肩包-米"])
            rows = queue_pack.scan(queue_pack.load_brief(brief_path))
            args = argparse.Namespace(product=[])
            pending = queue_pack.names_with(rows, "gen")
            self.assertEqual(set(pending), {"双肩包-黑", "双肩包-米"})
            wave = queue_pack.wave_names(brief, rows, args)
            self.assertEqual(wave, pending[:1])
            brief["inspect_every"] = 0
            self.assertEqual(queue_pack.wave_names(brief, rows, args), pending)

    def test_deliver_resizes_when_pillow_present(self) -> None:
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h1.png"
            Image.new("RGB", (1600, 1600), (10, 20, 30)).save(path)
            out = swap_fast.deliver_image(path, 800, 2 * 1024 * 1024)
            with Image.open(out) as image:
                self.assertEqual(image.size, (800, 800))

    def test_deliver_keeps_widescreen_ratio(self) -> None:
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h1.png"
            Image.new("RGB", (1600, 900), (10, 20, 30)).save(path)
            out = swap_fast.deliver_image(path, 800, None)
            with Image.open(out) as image:
                self.assertEqual(image.size, (800, 450))

    def test_deliver_square_canvas_rejects_widescreen(self) -> None:
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h1.png"
            Image.new("RGB", (1600, 900), (10, 20, 30)).save(path)
            with self.assertRaises(SystemExit):
                swap_fast.deliver_image(path, None, None, width=800, height=800)

    def test_deliver_square_canvas_shrinks_square(self) -> None:
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h1.png"
            Image.new("RGB", (1600, 1600), (10, 20, 30)).save(path)
            out = swap_fast.deliver_image(path, None, None, width=800, height=800)
            with Image.open(out) as image:
                self.assertEqual(image.size, (800, 800))


class JobPoolTests(unittest.TestCase):
    def test_skip_existing_does_not_call_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _touch_image(out / "h1.png")
            args = argparse.Namespace(format="png")
            job = {
                "slot": "H1",
                "prompt": "should not run",
                "args": args,
                "output_dir": out,
                "job_id": "H1",
                "label": "H1",
            }
            results = gen_image.run_job_pool(
                [job],
                concurrency=1,
                skip_existing=True,
                base_url="",
                api_key="",
                model="",
                mode="sync",
            )
            self.assertEqual(results["H1"][0], "skip")


if __name__ == "__main__":
    unittest.main()
