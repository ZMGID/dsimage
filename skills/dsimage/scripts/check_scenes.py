#!/usr/bin/env python3
"""校验 references/scenes/（情景库）与 references/templates/（模板库）的完整性。

情景 = 一类图的拍法规范（不含流程）。模板只有一种，用 lock=rules|master 区分按规则画还是母版换货。
规范依据：scenes/_SCENE_SPEC.md 与 templates/_TEMPLATE_SPEC.md。
"""
from __future__ import annotations
import glob
import json
import os
import re
import sys

# Windows 控制台默认 GBK，重配为 UTF-8 避免中文输出崩溃
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_MD = os.path.join(BASE_DIR, "SKILL.md")
SCENES_DIR = os.path.join(BASE_DIR, "references", "scenes")
TEMPLATES_DIR = os.path.join(BASE_DIR, "references", "templates")
CLIENT_META_NAME = "要求.json"
LEGACY_KIND = ("风格", "替换")
LEGACY_TOP = {"风格模板", "替换模板"}
ALLOWED_CLIENT_FILES = {CLIENT_META_NAME, "说明.md"}
LEGACY_CLIENT_META = "_甲方.json"
LOCK_ALIASES = {"rules": "rules", "master": "master", "style": "rules", "replace": "master"}

SCENE_REQUIRED = ["id", "name", "keywords", "trigger_phrases", "prompt_template",
                  "default_ratio", "composition_rules", "text_rules",
                  "pitfalls", "examples", "supports_image_reference"]
TEMPLATE_REQUIRED = ["id", "name", "template_meta", "keywords", "trigger_phrases",
                     "text_rules", "pack", "workflow",
                     "examples", "supports_image_reference"]
CLIENT_REQUIRED = ["id", "name", "templates", "language", "generation", "style"]
ANTI_AI_REQUIRED = {"06-social-media.json", "07-ugc-style.json", "15-livestream.json"}
MASTER_PRODUCT_REFS = {"front", "back", "side", "detail", "colorway"}
MASTER_EDITABLE = {"sku", "price", "color_name", "product_name", "currency"}
EXAMPLE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def read_json(path: str):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


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


def resolve_lock(fname: str, d: dict) -> str:
    raw_lock = d.get("lock")
    raw_legacy = d.get("template_type")
    lock = LOCK_ALIASES.get(raw_lock) if isinstance(raw_lock, str) else None
    legacy = LOCK_ALIASES.get(raw_legacy) if isinstance(raw_legacy, str) else None
    if lock:
        if legacy and legacy != lock:
            fail(fname, f"lock={raw_lock!r} 与 template_type={raw_legacy!r} 不一致")
        return lock
    if legacy:
        return legacy
    if raw_lock not in (None, ""):
        fail(fname, f"lock 应为 rules/master，实际 {raw_lock!r}")
    elif raw_legacy not in (None, ""):
        fail(fname, f"旧字段 template_type 应为 style/replace，实际 {raw_legacy!r}")
    return "rules"


def list_example_files(pkg_dir: str) -> list[str]:
    if not os.path.isdir(pkg_dir):
        return []
    names: list[str] = []
    for name in os.listdir(pkg_dir):
        path = os.path.join(pkg_dir, name)
        if os.path.isfile(path) and os.path.splitext(name)[1].lower() in EXAMPLE_SUFFIXES:
            names.append(name)
    return names


def check_named_image(fname: str, json_path: str, example: str, label: str) -> None:
    example_path = os.path.join(os.path.dirname(json_path), str(example))
    if not os.path.isfile(example_path):
        fail(fname, f"{label}不存在：{os.path.basename(os.path.dirname(json_path))}/{example}")
    elif os.path.splitext(str(example))[1].lower() not in EXAMPLE_SUFFIXES:
        fail(fname, f"{label}格式不支持：{example}（png/jpg/jpeg/webp）")


def check_rules_pack(fname: str, json_path: str, images: list) -> None:
    named = 0
    for img in images:
        if not (isinstance(img, dict) and img.get("slot") and img.get("purpose") and img.get("scene")):
            fail(fname, f"pack 项缺少 slot/purpose/scene: {img}")
            continue
        if img["scene"] not in scene_names:
            fail(fname, f"pack 引用的情景不存在：{img['scene']}")
        example = img.get("example")
        if example:
            named += 1
            check_named_image(fname, json_path, str(example), "示例图")
    if named == 0:
        files = list_example_files(os.path.dirname(json_path))
        if not files:
            fail(fname, "每个模板至少放 1 张示例图（建议 H1 用 h1.png）。lock=rules 出图仍用用户产品图，示例图只作版式参考，不要当母版换货")
        else:
            fail(fname, "文件夹里有图，但 pack 没有 example。至少给一个槽（建议 H1）写 example 指向该文件")


def check_master_pack(fname: str, json_path: str, d: dict, images: list) -> None:
    if d.get("supports_image_reference") is not True:
        fail(fname, "lock=master 时 supports_image_reference 必须为 true")
    rules = d.get("text_rules") if isinstance(d.get("text_rules"), dict) else {}
    if not rules.get("policy"):
        fail(fname, "lock=master 时 text_rules.policy 不能为空")
    fields = rules.get("editable_fields")
    if not isinstance(fields, list):
        fail(fname, "lock=master 时 text_rules.editable_fields 应为数组（没有可改字段则 []）")
    else:
        for item in fields:
            if item not in MASTER_EDITABLE:
                fail(fname, f"editable_fields 非法值：{item!r}（允许 {sorted(MASTER_EDITABLE)}）")
    for img in images:
        if not isinstance(img, dict):
            fail(fname, f"pack 项不是对象: {img}")
            continue
        if img.get("scene"):
            fail(fname, f"lock=master 槽位 {img.get('slot')} 不应引用 scene，改用 example")
        example = img.get("example")
        pref = img.get("product_ref")
        if not (img.get("slot") and img.get("purpose") and example and pref):
            fail(fname, f"pack 项缺少 slot/purpose/example/product_ref: {img}")
            continue
        if pref not in MASTER_PRODUCT_REFS:
            fail(fname, f"槽位 {img['slot']} product_ref 非法：{pref!r}")
        check_named_image(fname, json_path, str(example), "母版")


def pkg_json(pkg_dir: str) -> str | None:
    name = os.path.basename(pkg_dir)
    path = os.path.join(pkg_dir, name + ".json")
    return path if os.path.isfile(path) else None


def client_dirs() -> list[str]:
    if not os.path.isdir(TEMPLATES_DIR):
        return []
    names: list[str] = []
    for name in sorted(os.listdir(TEMPLATES_DIR)):
        path = os.path.join(TEMPLATES_DIR, name)
        if not os.path.isdir(path) or name.startswith("_") or name in LEGACY_TOP:
            continue
        has_meta = os.path.isfile(os.path.join(path, CLIENT_META_NAME))
        has_kind = any(os.path.isdir(os.path.join(path, kind)) for kind in LEGACY_KIND)
        if has_meta or has_kind:
            names.append(name)
        elif pkg_json(path):
            continue
        else:
            for dirpath, _dirs, files in os.walk(path):
                if any(f.endswith(".json") for f in files):
                    fail(name, "一个模板一个文件夹：零散的放 templates/NN-名/NN-名.json；有甲方才建文件夹并写 要求.json")
                    break
    return names


def check_one_template(path: str, client_meta: dict) -> None:
    rel = os.path.relpath(path, TEMPLATES_DIR).replace("\\", "/")
    try:
        d = read_json(path)
    except json.JSONDecodeError as exc:
        fail(rel, f"JSON 解析失败：{exc}")
        return
    for key in TEMPLATE_REQUIRED:
        if key not in d or d[key] in ("", None, [], {}):
            fail(rel, f"缺少必填字段或为空：{key}")
    check_common(rel, d)
    if d.get("generation"):
        check_generation(rel, d)
    elif not client_meta.get("generation"):
        if not client_meta:
            fail(rel, "零散模板必须自己写 generation")
        else:
            fail(rel, "模板未写 generation，且甲方 要求.json 也没有")
    check_keywords(rel, d)

    steps = d.get("workflow", [])
    if isinstance(steps, list):
        if len(steps) < 5:
            fail(rel, f"workflow 应至少 5 步，实际 {len(steps)}")
        for step in steps:
            if isinstance(step, str) and any(w in step for w in ("按需调整", "注意效果", "合理搭配")):
                fail(rel, f"workflow 含空话：{step}")

    lock = resolve_lock(rel, d)

    meta = d.get("template_meta", {})
    brand = meta.get("brand", {}) if isinstance(meta, dict) else {}
    client_brand = client_meta.get("brand", {}) if isinstance(client_meta.get("brand"), dict) else {}
    merged_brand = {**client_brand, **brand} if isinstance(brand, dict) else client_brand
    if lock == "rules" or brand:
        if not hex_brand(merged_brand if isinstance(merged_brand, dict) else {}, ("background", "text", "accent")):
            fail(rel, "template_meta.brand 或甲方 要求.json 的 brand 缺少合法 hex（background/text/accent）")

    pack = d.get("pack", {})
    images = pack.get("images", []) if isinstance(pack, dict) else []
    if not images:
        fail(rel, "pack.images 为空")
    elif lock == "master":
        check_master_pack(rel, path, d, images)
    else:
        check_rules_pack(rel, path, images)


def load_client_meta(client: str) -> dict:
    path = os.path.join(TEMPLATES_DIR, client, CLIENT_META_NAME)
    if not os.path.isfile(path):
        return {}
    try:
        data = read_json(path)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def check_client_meta(client: str) -> dict:
    rel = f"{client}/{CLIENT_META_NAME}"
    path = os.path.join(TEMPLATES_DIR, client, CLIENT_META_NAME)
    if not os.path.isfile(path):
        legacy = os.path.join(TEMPLATES_DIR, client, LEGACY_CLIENT_META)
        if os.path.isfile(legacy):
            fail(rel, "请把 _甲方.json 改名为 要求.json")
        else:
            fail(rel, "甲方文件夹必须有 要求.json（templates 列出本文件夹模板目录名，以及语言、分辨率、格式、风格）")
        return {}
    try:
        d = read_json(path)
    except json.JSONDecodeError as exc:
        fail(rel, f"JSON 解析失败：{exc}")
        return {}
    if not isinstance(d, dict):
        fail(rel, "应为 JSON 对象")
        return {}
    if "&" in client:
        fail(client, "甲方文件夹名不要含 &（Windows 会出事），BEAUTY&U 写成 BeautyU")
    if d.get("id") != client:
        fail(rel, f"id 应与文件夹名一致：{client!r}，实际 {d.get('id')!r}")
    for key in CLIENT_REQUIRED:
        if key not in d or d[key] in ("", None, [], {}):
            fail(rel, f"缺少必填字段或为空：{key}")
    check_generation(rel, d)
    brand = d.get("brand") if isinstance(d.get("brand"), dict) else {}
    for key in ("background", "text", "accent"):
        if key in brand:
            v = brand.get(key, "")
            if not (isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v)):
                fail(rel, f"brand.{key} 应为 hex 颜色，实际 {v!r}")
    listed = d.get("templates")
    actual = sorted(
        n for n in os.listdir(os.path.join(TEMPLATES_DIR, client))
        if pkg_json(os.path.join(TEMPLATES_DIR, client, n))
    )
    names: list[str] = []
    seen: set[str] = set()
    if isinstance(listed, list):
        for item in listed:
            if not isinstance(item, str) or item.endswith(".json") or "/" in item.replace("\\", "/"):
                fail(rel, f"templates 项应为同目录模板文件夹名（不要带 .json），实际 {item!r}")
                continue
            if item in seen:
                fail(rel, f"templates 重复：{item}")
                continue
            seen.add(item)
            names.append(item)
    if sorted(names) != actual:
        fail(rel, f"templates 必须与文件夹内模板目录一一对应。列出 {sorted(names)}，实际 {actual}")
    return d


def hex_brand(brand: dict, keys: tuple[str, ...]) -> bool:
    return all(
        isinstance(brand.get(key), str) and re.fullmatch(r"#[0-9a-fA-F]{6}", brand[key])
        for key in keys
    )


def check_common(fname: str, d: dict) -> None:
    stem = os.path.splitext(os.path.basename(fname))[0]
    expected_id = stem.split("-", 1)[1] if "-" in stem else stem
    if d.get("id") != expected_id:
        fail(fname, f"id 应为 {expected_id!r}，实际 {d.get('id')!r}")
    for key, minimum in (("keywords", 5), ("trigger_phrases", 3), ("examples", 1)):
        items = d.get(key)
        if isinstance(items, list) and 0 < len(items) < minimum:
            fail(fname, f"{key} 应至少 {minimum} 个，实际 {len(items)}")
    raw = json.dumps(d, ensure_ascii=False)
    for var in set(re.findall(r"\{[A-Za-z][A-Za-z0-9_-]*\}", raw)):
        if not re.fullmatch(r"\{[a-z][a-z0-9_]*\}", var):
            fail(fname, f"占位符 {var} 不符合 snake_case 命名")


def check_keywords(fname: str, d: dict) -> None:
    seen_in_file: set[str] = set()
    for kw in d.get("keywords", []):
        k = kw.lower()
        if k in seen_in_file:
            fail(fname, f"keywords 文件内重复：{kw}")
            continue
        seen_in_file.add(k)
        if k in all_keywords and all_keywords[k] != fname:
            fail(fname, f"keywords 与 {all_keywords[k]} 重复：{kw}")
        all_keywords[k] = fname


errors = 0
all_keywords: dict[str, str] = {}
scene_files = sorted(glob.glob(os.path.join(SCENES_DIR, "*.json")))
clients = client_dirs()
loose_files: list[str] = []
for name in sorted(os.listdir(TEMPLATES_DIR)) if os.path.isdir(TEMPLATES_DIR) else []:
    if name.startswith("_") or name in LEGACY_TOP:
        continue
    path = os.path.join(TEMPLATES_DIR, name)
    if name.endswith(".json") and os.path.isfile(path) and name != CLIENT_META_NAME:
        fail(name, "零散模板应放进同名文件夹：NN-名/NN-名.json")
        continue
    if os.path.isdir(path) and name not in clients:
        json_path = pkg_json(path)
        if json_path:
            loose_files.append(json_path)
        elif any(n.endswith(".json") for n in os.listdir(path) if os.path.isfile(os.path.join(path, n))):
            fail(name, "模板文件夹内应有与文件夹同名的 JSON")
template_files: list[str] = list(loose_files)
for client in clients:
    client_dir = os.path.join(TEMPLATES_DIR, client)
    for name in sorted(os.listdir(client_dir)):
        pkg = os.path.join(client_dir, name)
        json_path = pkg_json(pkg) if os.path.isdir(pkg) else None
        if json_path:
            template_files.append(json_path)
        elif name.endswith(".json") and name != CLIENT_META_NAME and os.path.isfile(pkg):
            fail(f"{client}/{name}", "甲方模板应放进同名文件夹：甲方/NN-名/NN-名.json")
template_files = sorted(template_files)
scene_names = {os.path.basename(f) for f in scene_files}
root_meta = os.path.join(TEMPLATES_DIR, CLIENT_META_NAME)
if os.path.isfile(root_meta):
    fail(CLIENT_META_NAME, "要求.json 只放在甲方文件夹里，不要放在 templates/ 根目录")
for old in LEGACY_TOP:
    if os.path.isdir(os.path.join(TEMPLATES_DIR, old)):
        fail(old, "旧目录已废弃：零散模板放 templates/NN-名/NN-名.json，有甲方才建文件夹")

# ── 情景库：拍法规范，无流程 ──
print("== 情景库 references/scenes/ ==")
for path in scene_files:
    fname = os.path.basename(path)
    try:
        d = read_json(path)
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
    if isinstance(d.get("examples"), list) and len(d["examples"]) < 2:
        fail(fname, f"examples 应至少 2 条，实际 {len(d['examples'])}")
    pitfalls = d.get("pitfalls")
    if isinstance(pitfalls, list) and not (3 <= len(pitfalls) <= 5):
        fail(fname, f"pitfalls 应为 3-5 条，实际 {len(pitfalls)}")
    tips = d.get("anti_ai_tips")
    if "anti_ai_tips" in d and not (isinstance(tips, str) and tips.strip()):
        fail(fname, "anti_ai_tips 为空则省略该键")
    if fname in ANTI_AI_REQUIRED and not (isinstance(tips, str) and tips.strip()):
        fail(fname, "UGC/社媒/直播情景必须写 anti_ai_tips")
    if re.search(r"\b8K\b", json.dumps(d, ensure_ascii=False), re.I):
        fail(fname, "不要写 8K（分辨率由 generation 决定，禁止暗示升采样）")
    cr = d.get("composition_rules", {})
    if isinstance(cr, dict):
        for key in ("product_ratio", "whitespace", "angles"):
            if key not in cr:
                fail(fname, f"composition_rules 缺 {key}")
        for key in ("product_ratio", "whitespace"):
            value = cr.get(key)
            if isinstance(value, str) and not re.search(r"\d", value):
                fail(fname, f"composition_rules.{key} 必须含数字或范围")
        for a in cr.get("angles", []):
            if not (isinstance(a, dict) and a.get("angle") and a.get("prompt")):
                fail(fname, f"angles 项缺少 angle 或 prompt: {a}")
    check_generation(fname, d)
    check_keywords(fname, d)

# ── 模板库：零散根目录 + 可选甲方文件夹 ──
print("== 模板库 references/templates/ ==")
client_metas: dict[str, dict] = {}
for client in clients:
    client_metas[client] = check_client_meta(client)
    client_dir = os.path.join(TEMPLATES_DIR, client)
    for name in os.listdir(client_dir):
        if name.startswith(".") or name in ALLOWED_CLIENT_FILES:
            continue
        extra = os.path.join(client_dir, name)
        if name in LEGACY_KIND and os.path.isdir(extra):
            fail(f"{client}/{name}", "不要再分 风格/ 替换/，把模板放进 甲方/NN-名/NN-名.json")
        elif os.path.isdir(extra):
            if pkg_json(extra):
                continue
            fail(f"{client}/{name}", "多余文件夹（每个模板一个文件夹，内含同名 JSON 和示例图/母版）")
        elif name == LEGACY_CLIENT_META:
            fail(f"{client}/{name}", "请改名为 要求.json")
        elif name.endswith(".json"):
            fail(f"{client}/{name}", "甲方模板应放进同名文件夹：甲方/NN-名/NN-名.json")
        else:
            fail(f"{client}/{name}", "甲方文件夹内只放 要求.json、可选 说明.md、各模板文件夹")

for path in loose_files:
    rel = os.path.relpath(path, TEMPLATES_DIR).replace("\\", "/")
    parts = rel.split("/")
    if len(parts) != 2 or parts[1] != parts[0] + ".json":
        fail(rel, "零散模板路径应为 NN-名/NN-名.json")
        continue
    check_one_template(path, {})

for path in template_files:
    if path in loose_files:
        continue
    rel = os.path.relpath(path, TEMPLATES_DIR).replace("\\", "/")
    parts = rel.split("/")
    if len(parts) != 3 or parts[2] != parts[1] + ".json":
        fail(rel, "甲方模板路径应为 甲方/NN-名/NN-名.json")
        continue
    check_one_template(path, client_metas.get(parts[0]) or {})

# ── SKILL.md 登记检查：每个情景/模板必须出现在匹配表里 ──
print("== SKILL.md 登记 ==")
skill_text = ""
try:
    with open(SKILL_MD, encoding="utf-8") as skill_file:
        skill_text = skill_file.read()
except OSError as exc:
    fail("SKILL.md", f"无法读取：{exc}")
if skill_text:
    for path in scene_files:
        fname = os.path.basename(path)
        if fname not in skill_text:
            fail(fname, "未在 SKILL.md 匹配表登记")
    for path in template_files:
        rel = os.path.relpath(path, TEMPLATES_DIR).replace("\\", "/")
        marker = f"templates/{rel}"
        if marker not in skill_text and rel not in skill_text:
            fail(rel, "未在 SKILL.md 匹配表登记")

print(f"\n共校验 {len(scene_files)} 个情景 + {len(clients)} 个甲方 + {len(template_files)} 个模板")
if errors:
    print(f"发现 {errors} 个问题，请修复后重跑")
    sys.exit(1)
print("全部通过 ✓")
