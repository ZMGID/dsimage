#!/usr/bin/env python3
"""校验 references/scenes/（情景库）与 references/templates/（模板库）的完整性。

情景 = 一类图的拍法规范（不含流程）；模板分风格（style，引用情景）与替换（replace，母版套图换品）。
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
KIND_FOLDER = {"风格": "style", "替换": "replace"}
LEGACY_TOP = {"风格模板", "替换模板"}
ALLOWED_CLIENT_FILES = {CLIENT_META_NAME, "说明.md"}
LEGACY_CLIENT_META = "_甲方.json"
ALLOWED_CLIENT_DIRS = {"风格", "替换"}

SCENE_REQUIRED = ["id", "name", "keywords", "trigger_phrases", "prompt_template",
                  "default_ratio", "composition_rules", "text_rules",
                  "pitfalls", "examples", "supports_image_reference"]
TEMPLATE_REQUIRED = ["id", "name", "template_meta", "keywords", "trigger_phrases",
                     "text_rules", "pack", "workflow",
                     "examples", "supports_image_reference"]
CLIENT_REQUIRED = ["id", "name", "language", "generation", "style"]
TEMPLATE_TYPES = {"style", "replace"}
REPLACE_PRODUCT_REFS = {"front", "back", "side", "detail", "colorway"}
REPLACE_EDITABLE = {"sku", "price", "color_name", "product_name", "currency"}
EXAMPLE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


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


def check_style_pack(fname: str, images: list) -> None:
    for img in images:
        if not (isinstance(img, dict) and img.get("slot") and img.get("purpose") and img.get("scene")):
            fail(fname, f"pack 项缺少 slot/purpose/scene: {img}")
            continue
        if img["scene"] not in scene_names:
            fail(fname, f"pack 引用的情景不存在：{img['scene']}")


def check_replace_pack(fname: str, json_path: str, d: dict, images: list) -> None:
    if d.get("supports_image_reference") is not True:
        fail(fname, "替换模板 supports_image_reference 必须为 true")
    rules = d.get("text_rules") if isinstance(d.get("text_rules"), dict) else {}
    if not rules.get("policy"):
        fail(fname, "替换模板 text_rules.policy 不能为空")
    fields = rules.get("editable_fields")
    if not isinstance(fields, list):
        fail(fname, "替换模板 text_rules.editable_fields 应为数组（没有可改字段则 []）")
    else:
        for item in fields:
            if item not in REPLACE_EDITABLE:
                fail(fname, f"editable_fields 非法值：{item!r}（允许 {sorted(REPLACE_EDITABLE)}）")
    example_dir = os.path.join(
        os.path.dirname(json_path), os.path.splitext(os.path.basename(json_path))[0]
    )
    if not os.path.isdir(example_dir):
        fail(fname, f"替换模板缺少母版文件夹：{os.path.basename(example_dir)}/")
    for img in images:
        if not isinstance(img, dict):
            fail(fname, f"pack 项不是对象: {img}")
            continue
        if img.get("scene"):
            fail(fname, f"替换模板槽位 {img.get('slot')} 不应引用 scene，改用 example")
        example = img.get("example")
        pref = img.get("product_ref")
        if not (img.get("slot") and img.get("purpose") and example and pref):
            fail(fname, f"pack 项缺少 slot/purpose/example/product_ref: {img}")
            continue
        if pref not in REPLACE_PRODUCT_REFS:
            fail(fname, f"槽位 {img['slot']} product_ref 非法：{pref!r}")
        if os.path.isdir(example_dir):
            example_path = os.path.join(example_dir, str(example))
            if not os.path.isfile(example_path):
                fail(fname, f"母版不存在：{os.path.basename(example_dir)}/{example}")
            elif os.path.splitext(str(example))[1].lower() not in EXAMPLE_SUFFIXES:
                fail(fname, f"母版格式不支持：{example}（png/jpg/jpeg/webp）")


def client_dirs() -> list[str]:
    if not os.path.isdir(TEMPLATES_DIR):
        return []
    names: list[str] = []
    for name in sorted(os.listdir(TEMPLATES_DIR)):
        path = os.path.join(TEMPLATES_DIR, name)
        if not os.path.isdir(path) or name.startswith("_") or name in LEGACY_TOP:
            continue
        if os.path.isfile(os.path.join(TEMPLATES_DIR, name + ".json")):
            continue
        has_meta = os.path.isfile(os.path.join(path, CLIENT_META_NAME))
        has_kind = any(os.path.isdir(os.path.join(path, kind)) for kind in KIND_FOLDER)
        if has_meta or has_kind:
            names.append(name)
        else:
            for dirpath, _dirs, files in os.walk(path):
                if any(f.endswith(".json") for f in files):
                    fail(name, "零散模板直接放 templates/ 根目录；有甲方才建文件夹并写 要求.json")
                    break
    return names


def check_one_template(path: str, expected_type: str | None, client_meta: dict) -> None:
    rel = os.path.relpath(path, TEMPLATES_DIR).replace("\\", "/")
    try:
        d = json.load(open(path, encoding="utf-8"))
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
        if expected_type is None:
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

    ttype = d.get("template_type") or "style"
    if ttype not in TEMPLATE_TYPES:
        fail(rel, f"template_type 非法：{ttype!r}（允许 style/replace）")
        ttype = expected_type or "style"
    elif expected_type and ttype != expected_type:
        fail(rel, f"template_type 为 {ttype}，但文件在 {expected_type} 对应目录")
        ttype = expected_type

    meta = d.get("template_meta", {})
    brand = meta.get("brand", {}) if isinstance(meta, dict) else {}
    client_brand = client_meta.get("brand", {}) if isinstance(client_meta.get("brand"), dict) else {}
    merged_brand = {**client_brand, **brand} if isinstance(brand, dict) else client_brand
    if ttype == "style" or brand:
        if not hex_brand(merged_brand if isinstance(merged_brand, dict) else {}, ("background", "text", "accent")):
            fail(rel, "template_meta.brand 或甲方 要求.json 的 brand 缺少合法 hex（background/text/accent）")

    pack = d.get("pack", {})
    images = pack.get("images", []) if isinstance(pack, dict) else []
    if not images:
        fail(rel, "pack.images 为空")
    elif ttype == "replace":
        check_replace_pack(rel, path, d, images)
    else:
        check_style_pack(rel, images)


def load_client_meta(client: str) -> dict:
    path = os.path.join(TEMPLATES_DIR, client, CLIENT_META_NAME)
    if not os.path.isfile(path):
        return {}
    try:
        data = json.load(open(path, encoding="utf-8"))
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
            fail(rel, "甲方文件夹必须有 要求.json（语言、分辨率、格式、风格等共用要求）")
        return {}
    try:
        d = json.load(open(path, encoding="utf-8"))
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
    for key in ("keywords", "trigger_phrases", "examples"):
        if key in d and (not isinstance(d[key], list) or not d[key]):
            fail(fname, f"{key} 应为非空列表")
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
loose_files = sorted(
    p for p in glob.glob(os.path.join(TEMPLATES_DIR, "*.json"))
    if os.path.basename(p) != CLIENT_META_NAME
)
template_files: list[str] = list(loose_files)
for client in clients:
    for kind in KIND_FOLDER:
        kind_dir = os.path.join(TEMPLATES_DIR, client, kind)
        if os.path.isdir(kind_dir):
            template_files.extend(glob.glob(os.path.join(kind_dir, "*.json")))
template_files = sorted(template_files)
scene_names = {os.path.basename(f) for f in scene_files}
root_meta = os.path.join(TEMPLATES_DIR, CLIENT_META_NAME)
if os.path.isfile(root_meta):
    fail(CLIENT_META_NAME, "要求.json 只放在甲方文件夹里，不要放在 templates/ 根目录")
for old in LEGACY_TOP:
    if os.path.isdir(os.path.join(TEMPLATES_DIR, old)):
        fail(old, "旧目录已废弃：零散模板放 templates/ 根目录，有甲方才建文件夹")

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

# ── 模板库：零散根目录 + 可选甲方文件夹 ──
print("== 模板库 references/templates/ ==")
client_metas: dict[str, dict] = {}
for client in clients:
    client_metas[client] = check_client_meta(client)
    client_dir = os.path.join(TEMPLATES_DIR, client)
    for name in os.listdir(client_dir):
        if name.startswith(".") or name in ALLOWED_CLIENT_FILES or name in ALLOWED_CLIENT_DIRS:
            continue
        extra = os.path.join(client_dir, name)
        if os.path.isdir(extra):
            fail(f"{client}/{name}", "甲方文件夹内只放 要求.json、可选 说明.md、风格/、替换/")
        elif name == LEGACY_CLIENT_META:
            fail(f"{client}/{name}", "请改名为 要求.json")
        elif name.endswith(".json"):
            fail(f"{client}/{name}", "模板 JSON 应放在 风格/ 或 替换/ 下，不要和 要求.json 同级")

for path in loose_files:
    check_one_template(path, None, {})

for path in template_files:
    if path in loose_files:
        continue
    rel = os.path.relpath(path, TEMPLATES_DIR).replace("\\", "/")
    parts = rel.split("/")
    if len(parts) != 3 or parts[1] not in KIND_FOLDER:
        fail(rel, "甲方模板路径应为 甲方/风格/NN-名.json 或 甲方/替换/NN-名.json")
        continue
    client, kind, _fname = parts
    check_one_template(path, KIND_FOLDER[kind], client_metas.get(client) or {})

# ── SKILL.md 登记检查：每个情景/模板必须出现在匹配表里 ──
print("== SKILL.md 登记 ==")
try:
    skill_text = open(SKILL_MD, encoding="utf-8").read()
except OSError as exc:
    fail("SKILL.md", f"无法读取：{exc}")
    skill_text = ""
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
