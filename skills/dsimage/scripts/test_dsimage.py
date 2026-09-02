#!/usr/bin/env python3
"""不打真实 API 的单测：python scripts/test_dsimage.py"""
from __future__ import annotations

import json
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import core  # noqa: E402
import dsimage as _dsimage  # noqa: E402


class dsimage:  # noqa: N801
    """测试里静默跑 CLI。"""

    @staticmethod
    def main(argv: list[str]) -> int:
        import contextlib
        import io

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return _dsimage.main(argv)


def write_png(path: Path, width: int = 8, height: int = 8, rgb=(255, 255, 255)) -> Path:
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    return path


def replace_template(folder: Path, *, with_derive: bool = True) -> Path:
    folder.mkdir(parents=True)
    for i in (1, 2, 3):
        write_png(folder / f"h{i}.png")
    write_png(folder / "assets" / "logo.png")
    write_png(folder / "assets" / "back_ref.png")
    data = {
        "name": folder.name,
        "mode": "replace",
        "category": "双肩包",
        "language": "pt-BR",
        "output": {"ratio": "1:1", "resolution": "1k", "format": "png",
                   "deliver": {"width": 800, "height": 800, "max_bytes": "2MB"}},
        "product_kinds": {"backpack": "双肩包", "bag": "非背包"},
        "slots": [
            {"id": "H1", "purpose": "主图", "example": "h1.png",
             "prompt": "swap H1 for {sku}", "prompt_by_kind": {"bag": "swap H1 bag edition"}},
            {"id": "H2", "purpose": "背面", "example": "h2.png",
             "refs": ["@example", "@product.front", "@product.back"], "prompt": "swap H2 back"},
            {"id": "H3", "purpose": "模特", "example": "h3.png",
             "refs": ["@product.front", "assets/logo.png"],
             "prompt": "model page {vary}", "vary": ["pose A", "pose B"]},
        ],
        "notes": [],
    }
    if with_derive:
        data["derive"] = {"back": {"prompt": "draw back view", "refs": ["@product.front", "assets/back_ref.png"]}}
    core.write_json(folder / core.TEMPLATE_FILE, data)
    return folder


def smart_template(folder: Path) -> Path:
    folder.mkdir(parents=True)
    write_png(folder / "h1.png")
    core.write_json(folder / core.TEMPLATE_FILE, {
        "name": folder.name,
        "mode": "smart",
        "category": "水杯",
        "language": "zh",
        "style": "Campaign Style Lock: clean off-white background.",
        "output": {"ratio": "1:1", "resolution": "1k", "format": "png"},
        "slots": [
            {"id": "H1", "purpose": "主图", "example": "h1.png", "brief": "产品居中，写核心卖点"},
            {"id": "H2", "purpose": "细节", "brief": "微距材质"},
        ],
    })
    return folder


def client_source(root: Path) -> Path:
    source = root / "VE男包系列"
    write_png(source / "V26007-V26010" / "V26007.jpg")
    write_png(source / "V26007-V26010" / "V26008正面.jpg")
    write_png(source / "V26007-V26010" / "V26008背面.jpg")
    write_png(source / "V26025" / "未标题-7.png")
    return source


class TempTemplatesMixin:
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self._old_templates = core.TEMPLATES_DIR
        core.TEMPLATES_DIR = self.tmp / "templates"
        core.TEMPLATES_DIR.mkdir()

    def tearDown(self) -> None:
        core.TEMPLATES_DIR = self._old_templates
        shutil.rmtree(self.tmp, ignore_errors=True)


class ScanTests(TempTemplatesMixin, unittest.TestCase):
    def test_splits_range_folder_single_image_is_front(self) -> None:
        products = core.scan_source(client_source(self.tmp))
        by_sku = {p["sku"]: p for p in products}
        self.assertEqual(set(by_sku), {"V26007", "V26008", "V26025"})
        self.assertTrue(by_sku["V26007"]["front"].endswith("V26007.jpg"))
        self.assertIsNone(by_sku["V26008"]["front"], "多张图留给 Agent 选")
        self.assertEqual(len(by_sku["V26008"]["images"]), 2)
        self.assertIsNone(by_sku["V26007"]["back"])
        self.assertEqual(by_sku["V26025"]["folder"], "V26025")

    def test_single_folder_and_single_file(self) -> None:
        folder = self.tmp / "杯子"
        write_png(folder / "a.png")
        write_png(folder / "b.png")
        products = core.scan_source(folder)
        self.assertEqual([p["sku"] for p in products], ["杯子"])
        self.assertEqual(len(products[0]["images"]), 2)
        self.assertIsNone(products[0]["front"])
        single = core.scan_source(folder / "a.png")
        self.assertEqual(single[0]["sku"], "a")
        self.assertTrue(single[0]["front"].endswith("a.png"))

    def test_mixed_labeled_unlabeled_fails(self) -> None:
        source = self.tmp / "src"
        write_png(source / "V1-V2" / "V1001.png")
        write_png(source / "V1-V2" / "V1002.png")
        write_png(source / "V1-V2" / "杂图.png")
        with self.assertRaises(core.DsError):
            core.scan_source(source)

    def test_default_output_dir(self) -> None:
        self.assertEqual(core.default_output_dir(Path("D:/x/VE男包系列")).name, "VE男包生成")
        self.assertEqual(core.default_output_dir(Path("D:/x/春季新品")).name, "春季新品生成")



class TemplateCheckTests(TempTemplatesMixin, unittest.TestCase):
    def test_good_replace_passes(self) -> None:
        tpl = core.load_template(replace_template(core.TEMPLATES_DIR / "好模板"))
        self.assertEqual(core.check_template(tpl), [])

    def test_good_smart_passes(self) -> None:
        tpl = core.load_template(smart_template(core.TEMPLATES_DIR / "smart"))
        self.assertEqual(core.check_template(tpl), [])

    def test_replace_errors(self) -> None:
        folder = replace_template(core.TEMPLATES_DIR / "坏模板", with_derive=False)
        tpl = core.load_template(folder)
        (folder / "h2.png").unlink()
        tpl["slots"][0]["prompt"] = "hello {typo}"
        tpl["slots"][0]["prompt_by_kind"] = {"unknown": "x"}
        tpl["slots"][2]["vary"] = []
        tpl["slots"].append({"id": "H4", "purpose": "无图", "prompt": "x"})
        problems = "\n".join(core.check_template(tpl))
        self.assertIn("示例图不存在：h2.png", problems)
        self.assertIn("未知占位符", problems)
        self.assertIn("'unknown'", problems)
        self.assertIn("没有 vary 列表", problems)
        self.assertIn("H4 缺示例图", problems)

    def test_smart_errors(self) -> None:
        tpl = core.load_template(smart_template(core.TEMPLATES_DIR / "s"))
        tpl["style"] = ""
        tpl["slots"][1]["brief"] = ""
        problems = "\n".join(core.check_template(tpl))
        self.assertIn("style", problems)
        self.assertIn("H2 缺 brief", problems)

    def test_deliver_ratio_mismatch(self) -> None:
        tpl = core.load_template(replace_template(core.TEMPLATES_DIR / "r"))
        tpl["output"]["deliver"] = {"width": 800, "height": 1000}
        self.assertTrue(any("变形" in p for p in core.check_template(tpl)))

    def test_init_from_dir_and_blank(self) -> None:
        sample = self.tmp / "甲方示例"
        for name in ("主图.png", "2.png", "10.png"):
            write_png(sample / name, 16, 9)
        folder = core.init_template("新模板", mode="replace", from_dir=sample)
        data = core.read_json(folder / core.TEMPLATE_FILE)
        self.assertEqual([s["id"] for s in data["slots"]], ["H1", "H2", "H3"])
        self.assertTrue((folder / "h1.png").is_file() and (folder / "h3.png").is_file())
        self.assertIn("h2.png ← 10.png", data["notes"][0])
        blank = core.init_template("空", mode="smart", slot_count=2)
        self.assertEqual(core.read_json(blank / core.TEMPLATE_FILE)["slots"][1], {"id": "H2", "purpose": "", "brief": ""})
        with self.assertRaises(core.DsError):
            core.init_template("空", mode="smart", slot_count=2)
        self.assertEqual({t["name"] for t in core.list_templates()}, {"空", "新模板"})


class ReplaceRunTests(TempTemplatesMixin, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.template = replace_template(core.TEMPLATES_DIR / "背包")
        self.source = client_source(self.tmp)
        self.batch = core.init_batch(self.template, self.source)
        self.tpl = core.load_template(self.template)
        self.out = Path(self.batch["output"])
        front = self.source / "V26007-V26010" / "V26008正面.jpg"
        back = self.source / "V26007-V26010" / "V26008背面.jpg"
        self.assertEqual(dsimage.main(["set", str(self.out), "V26008", "--front", str(front), "--back", back.name]), 0)
        self.batch = core.load_batch(self.out)

    def test_init_layout(self) -> None:
        self.assertEqual(self.out.name, "VE男包生成")
        self.assertTrue(core.batch_path(self.out).is_file())
        self.assertTrue((self.out / "V26007" / "V26007.jpg").is_file())
        self.assertTrue((self.out / "V26008" / "V26008正面.jpg").is_file())
        self.assertTrue((self.out / "V26008" / "V26008背面.jpg").is_file())
        self.assertFalse((self.out / "V26007-V26010").exists())
        self.assertEqual(self.batch["products"][0]["kind"], "backpack")
        p8 = core.find_product(self.batch, "V26008")
        self.assertTrue(p8["front"].endswith("V26008正面.jpg"))
        self.assertTrue(p8["back"].endswith("V26008背面.jpg"))

    def test_undecided_front_blocks_and_shows_in_status(self) -> None:
        batch = core.init_batch(self.template, self.source, self.tmp / "out2")
        p8 = core.find_product(batch, "V26008")
        self.assertIsNone(p8["front"])
        plan = core.build_jobs(batch, self.tpl, p8, 1)
        self.assertEqual(plan["slots"], [])
        self.assertTrue(all("set --front" in r for _, r in plan["blocked"]))
        self.assertEqual(core.product_status(batch, self.tpl, p8)["state"], "needs_front")
        self.assertIn("待选白图", core.format_status(batch, self.tpl))

    def test_jobs_kind_vary_derive(self) -> None:
        p7 = core.find_product(self.batch, "V26007")
        p8 = core.find_product(self.batch, "V26008")
        plan7 = core.build_jobs(self.batch, self.tpl, p7, 0)
        by_slot = {j["slot"]: j for j in plan7["slots"]}
        self.assertEqual(by_slot["H1"]["prompt"], "swap H1 for V26007")
        self.assertEqual(by_slot["H1"]["image"][0], str(self.template / "h1.png"))
        self.assertEqual(by_slot["H3"]["prompt"], "model page pose A")
        self.assertEqual(by_slot["H3"]["image"][1], str(self.template / "assets" / "logo.png"))
        self.assertEqual(len(plan7["derive"]), 1)
        self.assertEqual(plan7["derive"][0]["output_dir"], str(core.work_dir(self.batch, "V26007")))
        self.assertTrue(by_slot["H2"]["image"][2].endswith("back.png"))
        self.assertEqual(plan7["blocked"], [])

        plan8 = core.build_jobs(self.batch, self.tpl, p8, 1)
        by_slot8 = {j["slot"]: j for j in plan8["slots"]}
        self.assertEqual(plan8["derive"], [])
        self.assertTrue(by_slot8["H2"]["image"][2].endswith("V26008背面.jpg"))
        self.assertEqual(by_slot8["H3"]["prompt"], "model page pose B")

        p7["kind"] = "bag"
        p7["vary"] = {"H3": "custom pose"}
        plan = core.build_jobs(self.batch, self.tpl, p7, 0, only_slots=["H1", "H3"])
        prompts = {j["slot"]: j["prompt"] for j in plan["slots"]}
        self.assertEqual(prompts, {"H1": "swap H1 bag edition", "H3": "model page custom pose"})

    def test_refs_by_kind_skips_back_for_bags(self) -> None:
        self.tpl["slots"][1]["refs_by_kind"] = {"bag": ["@example", "@product.front"]}
        self.assertEqual(core.check_template(self.tpl), [])
        p7 = core.find_product(self.batch, "V26007")
        p7["kind"] = "bag"
        plan = core.build_jobs(self.batch, self.tpl, p7, 0, only_slots=["H2"])
        self.assertEqual(plan["derive"], [])
        self.assertEqual(len(plan["slots"][0]["image"]), 2)
        self.tpl["slots"][1]["refs_by_kind"] = {"nope": ["@example"]}
        self.assertTrue(any("refs_by_kind" in p for p in core.check_template(self.tpl)))

    def test_derived_back_is_used_once_present(self) -> None:
        p7 = core.find_product(self.batch, "V26007")
        write_png(core.work_dir(self.batch, "V26007") / "back.png")
        plan = core.build_jobs(self.batch, self.tpl, p7, 0)
        self.assertEqual(plan["derive"], [])

    def test_no_derive_falls_back_to_default_prompt(self) -> None:
        self.tpl.pop("derive")
        self.assertEqual(core.check_template(self.tpl), [])
        plan = core.build_jobs(self.batch, self.tpl, core.find_product(self.batch, "V26007"), 0)
        self.assertEqual(plan["blocked"], [])
        self.assertEqual([j["slot"] for j in plan["slots"]], ["H1", "H2", "H3"])
        self.assertEqual(len(plan["derive"]), 1)
        self.assertEqual(plan["derive"][0]["prompt"], core.DEFAULT_DERIVE_BACK["prompt"])
        self.assertEqual(len(plan["derive"][0]["image"]), 1)
        self.tpl["derive"] = {"side": {"prompt": "x"}}
        self.assertTrue(any("只支持 back" in p for p in core.check_template(self.tpl)))

    def test_cli_derive_dry_run_and_skips(self) -> None:
        code = dsimage.main(["derive", str(self.out), "--dry-run"])
        self.assertEqual(code, 0)
        write_png(core.derived_back(self.batch, core.find_product(self.batch, "V26007"), "png") or
                  core.work_dir(self.batch, "V26007") / "back.png")
        self.assertIsNotNone(core.derived_back(self.batch, core.find_product(self.batch, "V26007"), "png"))
        self.assertEqual(core.back_source(self.batch, self.tpl, core.find_product(self.batch, "V26008"))[0], "product")
        self.assertEqual(core.back_source(self.batch, self.tpl, core.find_product(self.batch, "V26007"))[0], "derived")
        self.assertEqual(core.back_source(self.batch, self.tpl, core.find_product(self.batch, "V26025"))[0], "missing")

    def test_cli_set_validation(self) -> None:
        self.assertNotEqual(dsimage.main(["set", str(self.out), "V26007", "--vary", "H1", "x"]), 0, "H1 没有 {vary}")
        self.assertNotEqual(dsimage.main(["set", str(self.out), "V26007", "--vary", "H9", "x"]), 0, "没有 H9")
        self.assertEqual(dsimage.main(["set", str(self.out), "V26007", "--vary", "h3", "x"]), 0, "槽位 id 不分大小写")
        self.assertEqual(core.load_batch(self.out)["products"][0]["vary"], {"H3": "x"})
        self.assertNotEqual(dsimage.main(["run", str(self.out), "--dry-run", "--slot", "H7"]), 0, "未知槽位")
        write_png(core.work_dir(self.batch, "V26007") / "back.png")
        front = core.find_product(self.batch, "V26007")["front"]
        self.assertEqual(dsimage.main(["set", str(self.out), "V26007", "--back", front]), 0)
        self.assertIsNone(core.derived_back(self.batch, core.find_product(core.load_batch(self.out), "V26007"), "png"),
                          "指定真背面后删掉派生图")

    def test_loose_images_reported(self) -> None:
        write_png(self.source / "封面.png")
        self.assertEqual([p.name for p in core.loose_images(self.source)], ["封面.png"])
        self.assertEqual(len(core.scan_source(self.source)), 3)

    def test_status_and_format(self) -> None:
        write_png(self.out / "V26007" / "h1.png")
        row = core.product_status(self.batch, self.tpl, core.find_product(self.batch, "V26007"))
        self.assertEqual(row["state"], "pending")
        self.assertEqual(row["done"], ["H1"])
        for i in (1, 2, 3):
            write_png(self.out / "V26025" / f"h{i}.png")
        text = core.format_status(self.batch, self.tpl)
        self.assertIn("完成 1", text)
        self.assertIn("V26025", text)

    def test_cli_dry_run_writes_jobs(self) -> None:
        code = dsimage.main(["run", str(self.out), "--only", "V26007", "--dry-run"])
        self.assertEqual(code, 0)
        jobs = core.read_json(core.work_dir(self.batch, "V26007") / core.JOBS_FILE)
        self.assertEqual(len(jobs["jobs"]), 3)
        self.assertEqual(len(jobs["derive"]), 1)
        self.assertFalse((core.work_dir(self.batch, "V26008") / core.JOBS_FILE).exists())

    def test_cli_set_and_reinit_keeps_edits(self) -> None:
        code = dsimage.main(["set", str(self.out), "V26007", "--kind", "bag", "--vary", "H3", "hat on"])
        self.assertEqual(code, 0)
        batch = core.init_batch(self.template, self.source)
        p7 = core.find_product(batch, "V26007")
        self.assertEqual(p7["kind"], "bag")
        self.assertEqual(p7["vary"], {"H3": "hat on"})
        self.assertTrue(core.find_product(batch, "V26008")["front"].endswith("V26008正面.jpg"))
        self.assertNotEqual(dsimage.main(["set", str(self.out), "V26007", "--kind", "nope"]), 0)

    def test_init_rejects_broken_template(self) -> None:
        (self.template / "h1.png").unlink()
        with self.assertRaises(core.DsError):
            core.init_batch(self.template, self.source, self.tmp / "out2")


class SmartRunTests(TempTemplatesMixin, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.template = smart_template(core.TEMPLATES_DIR / "杯子smart")
        self.source = self.tmp / "杯子"
        write_png(self.source / "cup.png")
        self.batch = core.init_batch(self.template, self.source)
        self.tpl = core.load_template(self.template)
        self.out = Path(self.batch["output"])

    def test_packet_then_prompts(self) -> None:
        product = self.batch["products"][0]
        self.assertEqual(product["sku"], "杯子")
        self.assertEqual(core.product_status(self.batch, self.tpl, product)["state"], "needs_prompts")
        code = dsimage.main(["run", str(self.out), "--dry-run"])
        self.assertEqual(code, 0)
        work = core.work_dir(self.batch, "杯子")
        self.assertTrue((work / core.BRIEF_FILE).is_file())
        prompts = core.read_json(work / core.PROMPTS_FILE)
        self.assertEqual(prompts, {"H1": "", "H2": ""})
        brief = (work / core.BRIEF_FILE).read_text(encoding="utf-8")
        self.assertIn("Campaign Style Lock", brief)
        self.assertIn("产品居中", brief)
        self.assertIn("cup.png", brief)

        core.write_json(work / core.PROMPTS_FILE, {"H1": "hero prompt", "H2": ""})
        plan = core.build_jobs(self.batch, self.tpl, product, 0, None, core.read_prompts(self.batch, "杯子"))
        self.assertEqual([j["slot"] for j in plan["slots"]], ["H1"])
        self.assertEqual(plan["slots"][0]["image"], [product["front"]])
        self.assertEqual(plan["blocked"], [("H2", "prompts.json 还没填")])
        with self.assertRaises(core.DsError):
            core.read_prompts(self.batch, "杯子", require_complete=True)

    def test_brief_by_kind(self) -> None:
        self.tpl["product_kinds"] = {"mug": "杯", "bottle": "瓶"}
        self.tpl["slots"][0]["brief_by_kind"] = {"bottle": "瓶子要竖着拍", "nope": "x"}
        self.assertTrue(any("brief_by_kind" in p for p in core.check_template(self.tpl)))
        del self.tpl["slots"][0]["brief_by_kind"]["nope"]
        self.assertEqual(core.check_template(self.tpl), [])
        product = self.batch["products"][0]
        product["kind"] = "bottle"
        brief = core.write_smart_packet(self.batch, self.tpl, product).read_text(encoding="utf-8")
        self.assertIn("本品类（bottle）：瓶子要竖着拍", brief)
        product["kind"] = "mug"
        brief = core.write_smart_packet(self.batch, self.tpl, product).read_text(encoding="utf-8")
        self.assertNotIn("瓶子要竖着拍", brief)

    def test_freeze(self) -> None:
        work = core.work_dir(self.batch, "杯子")
        core.write_json(work / core.PROMPTS_FILE, {"H1": "hero prompt", "H2": "detail prompt"})
        with self.assertRaises(core.DsError):
            core.freeze_template(self.batch, "杯子", "冻结")
        write_png(self.out / "杯子" / "h1.png")
        write_png(self.out / "杯子" / "h2.png")
        folder = core.freeze_template(self.batch, "杯子", "冻结")
        frozen = core.load_template(folder)
        self.assertEqual(frozen["mode"], "replace")
        self.assertEqual(core.check_template(frozen), [])
        self.assertTrue(frozen["slots"][1]["prompt"].endswith("H2: detail prompt"))
        self.assertTrue((folder / "h2.png").is_file())


class GenTests(TempTemplatesMixin, unittest.TestCase):
    def test_gen_dry_run_and_validation(self) -> None:
        ref = write_png(self.tmp / "cup.png")
        out = self.tmp / "out"
        self.assertEqual(dsimage.main(["gen", "a cup", "--ref", str(ref), "--out", str(out), "--name", "cup", "--dry-run"]), 0)
        self.assertEqual(dsimage.main(["gen", "a cup", "--n", "3", "--out", str(out), "--dry-run"]), 0)
        prompt_file = self.tmp / "p.txt"
        prompt_file.write_text("from file", encoding="utf-8")
        self.assertEqual(dsimage.main(["gen", f"@{prompt_file}", "--out", str(out), "--dry-run"]), 0)
        self.assertNotEqual(dsimage.main(["gen", "x", "--ref", str(self.tmp / "nope.png"), "--dry-run"]), 0)
        self.assertNotEqual(dsimage.main(["gen", "x", "--ratio", "7:3", "--dry-run"]), 0)
        self.assertNotEqual(dsimage.main(["gen", "x", "--name", "a/b", "--dry-run"]), 0)
        self.assertNotEqual(dsimage.main(["gen", "@" + str(self.tmp / "missing.txt"), "--dry-run"]), 0)


class DeliverPreviewTests(TempTemplatesMixin, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        try:
            from PIL import Image  # noqa: F401
        except ImportError:
            self.skipTest("Pillow not installed")

    def test_deliver_shrinks_and_rejects_ratio(self) -> None:
        from PIL import Image

        path = self.tmp / "h1.png"
        Image.new("RGB", (1600, 1600), (10, 20, 30)).save(path)
        out = core.deliver_image(path, {"width": 800, "height": 800, "max_bytes": "2MB"})
        with Image.open(out) as image:
            self.assertEqual(image.size, (800, 800))
        wide = self.tmp / "h2.png"
        Image.new("RGB", (1600, 900)).save(wide)
        with self.assertRaises(core.DsError):
            core.deliver_image(wide, {"width": 800, "height": 800})
        out = core.deliver_image(wide, {"max_px": 800})
        with Image.open(out) as image:
            self.assertEqual(image.size, (800, 450))

    def test_deliver_batch_and_preview(self) -> None:
        from PIL import Image

        template = replace_template(core.TEMPLATES_DIR / "背包")
        source = self.tmp / "单品"
        write_png(source / "p.png")
        batch = core.init_batch(template, source)
        tpl = core.load_template(template)
        out = Path(batch["output"]) / "单品"
        Image.new("RGB", (1024, 1024), (200, 30, 30)).save(out / "h1.png")
        Image.new("RGB", (1024, 1024), (30, 200, 30)).save(out / "h2.png")
        changed = core.deliver_batch(batch, tpl)
        self.assertEqual(len(changed), 2)
        with Image.open(out / "h1.png") as image:
            self.assertEqual(image.size, (800, 800))
        preview = core.preview_product(batch, tpl, batch["products"][0])
        self.assertTrue(preview and preview.is_file())
        with Image.open(preview) as sheet:
            self.assertEqual(sheet.width, 3 * 320)


if __name__ == "__main__":
    unittest.main()
