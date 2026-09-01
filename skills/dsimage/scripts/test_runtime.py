#!/usr/bin/env python3
"""不打真实 API 的运行时单测。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gen_image  # noqa: E402
import match_pack  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
