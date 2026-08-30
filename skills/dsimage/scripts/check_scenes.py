#!/usr/bin/env python3
"""校验 references/scenes/（情景库）与 references/templates/（模板库）的完整性。

情景 = 一类图的拍法规范（不含流程）；模板 = 品牌/语言/图片包/执行流程，通过 pack 引用情景。
规范依据：scenes/_SCENE_SPEC.md 与 templates/_TEMPLATE_SPEC.md。
"""
import glob
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENES_DIR = os.path.join(BASE_DIR, "references", "scenes")
TEMPLATES_DIR = os.path.join(BASE_DIR, "references", "templates")

SCENE_REQUIRED = ["id", "name", "keywords", "trigger_phrases", "prompt_template",
                  "default_ratio", "composition_rules", "text_rules",
                  "pitfalls", "examples", "supports_image_reference"]
TEMPLATE_REQUIRED = ["id", "name", "template_meta", "keywords", "trigger_phrases",
                     "text_rules", "pack", "workflow", "generation",
                     "examples", "supports_image_reference"]


def fail(fname: str, msg: str) -> None:
    print(f"  [x] {fname}: {msg}")
    global errors
    errors += 1


def check_generation(fname: str, d: dict) -> None:
    gen = d.get("generation")
    if gen is None:
        return
    if not isinstance(gen, dict):
        fail(fname, "generation 应为对象")
        return
    for key, allowed in (("resolution", {"1k", "2k", "4k"}),
                         ("format", {"png", "jpeg", "webp"}),
                         ("quality", {"low", "medium", "high"})):
        value = gen.get(key)
        if value is not None and value not in allowed:
            fail(fname, f"generation.{key} 非法值：{value}（允许 {'/'.join(sorted(allowed))}）")
    unknown = set(gen) - {"resolution", "format", "quality"}
    if unknown:
        fail(fname, f"generation 含未知键：{sorted(unknown)}")


def check_common(fname: str, d: dict) -> None:
    stem = os.path.splitext(fname)[0]
    expected_id = stem.split("-", 1)[1] if "-" in stem else stem
    if d.get("id") != expected_id:
        fail(fname, f"id 应为 {expected_id!r}，实际 {d.get('id')!r}")
    for key in ("keywords", "trigger_phrases", "examples"):
        if key in d and (not isinstance(d[key], list) or not d[key]):
            fail(fname, f"{key} 应为非空列表")
    raw = json.dumps(d, ensure_ascii=False)
    for var in set(re.findall(r"\{[a-zA-Z-]+\}", raw)):
        if not re.fullmatch(r"\{[a-z_]+\}", var):
            fail(fname, f"占位符 {var} 不符合 snake_case 命名")


def check_keywords(fname: str, d: dict) -> None:
    for kw in d.get("keywords", []):
        k = kw.lower()
        if k in all_keywords and all_keywords[k] != fname:
            fail(fname, f"keywords 与 {all_keywords[k]} 重复：{kw}")
        all_keywords[k] = fname


errors = 0
all_keywords: dict[str, str] = {}
scene_files = sorted(glob.glob(os.path.join(SCENES_DIR, "*.json")))
template_files = sorted(glob.glob(os.path.join(TEMPLATES_DIR, "*.json")))
scene_names = {os.path.basename(f) for f in scene_files}

# ── 情景库：拍法规范，无流程 ──
print("== 情景库 references/scenes/ ==")
for path in scene_files:
    fname = os.path.basename(path)
    try:
        d = json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(fname, f"JSON 解析失败：{exc}")
        continue
    for key in SCENE_REQUIRED:
        if key not in d or d[key] in ("", None, [], {}):
            fail(fname, f"缺少必填字段或为空：{key}")
    if "workflow" in d:
        fail(fname, "情景不应包含 workflow（执行流程归模板层）")
    check_common(fname, d)
    for key in ("keywords", "trigger_phrases", "pitfalls"):
        if key in d and (not isinstance(d[key], list) or not d[key]):
            fail(fname, f"{key} 应为非空列表")
    cr = d.get("composition_rules", {})
    if isinstance(cr, dict):
        for key in ("product_ratio", "whitespace", "angles"):
            if key not in cr:
                fail(fname, f"composition_rules 缺 {key}")
        for a in cr.get("angles", []):
            if not (isinstance(a, dict) and a.get("angle") and a.get("prompt")):
                fail(fname, f"angles 项缺少 angle 或 prompt: {a}")
    check_generation(fname, d)
    check_keywords(fname, d)

# ── 模板库：品牌/语言/图片包/执行流程 ──
print("== 模板库 references/templates/ ==")
for path in template_files:
    fname = os.path.basename(path)
    try:
        d = json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(fname, f"JSON 解析失败：{exc}")
        continue
    for key in TEMPLATE_REQUIRED:
        if key not in d or d[key] in ("", None, [], {}):
            fail(fname, f"缺少必填字段或为空：{key}")
    check_common(fname, d)
    check_generation(fname, d)
    check_keywords(fname, d)

    # workflow 空话检查（流程只存在于模板）
    steps = d.get("workflow", [])
    if isinstance(steps, list):
        if len(steps) < 5:
            fail(fname, f"workflow 应至少 5 步，实际 {len(steps)}")
        for step in steps:
            if isinstance(step, str) and any(w in step for w in ("按需调整", "注意效果", "合理搭配")):
                fail(fname, f"workflow 含空话：{step}")

    # template_meta.brand 颜色必须 hex
    meta = d.get("template_meta", {})
    brand = meta.get("brand", {}) if isinstance(meta, dict) else {}
    for key in ("background", "text", "accent"):
        v = brand.get(key, "")
        if not (isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v)):
            fail(fname, f"template_meta.brand.{key} 应为 hex 颜色，实际 {v!r}")

    # pack 引用的情景必须真实存在
    pack = d.get("pack", {})
    images = pack.get("images", []) if isinstance(pack, dict) else []
    if not images:
        fail(fname, "pack.images 为空")
    for img in images:
        if not (isinstance(img, dict) and img.get("slot") and img.get("purpose") and img.get("scene")):
            fail(fname, f"pack 项缺少 slot/purpose/scene: {img}")
            continue
        if img["scene"] not in scene_names:
            fail(fname, f"pack 引用的情景不存在：{img['scene']}")

print(f"\n共校验 {len(scene_files)} 个情景 + {len(template_files)} 个模板")
if errors:
    print(f"发现 {errors} 个问题，请修复后重跑")
    sys.exit(1)
print("全部通过 ✓")
