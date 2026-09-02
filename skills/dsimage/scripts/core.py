#!/usr/bin/env python3
"""dsimage 核心库：模板、扫品、组 jobs、状态、交付、预览。CLI 在 dsimage.py。

模板 = 一个文件夹：template.json + 示例图（h1.png…）+ 可选 assets/。
mode=replace：每槽固定 prompt，脚本直接组 jobs 出图，模型不介入。
mode=smart：每槽 brief，脚本给每个品写 brief.md + prompts.json 骨架，模型填完再出图。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gen_image  # noqa: E402

SKILL_ROOT = ROOT.parent
TEMPLATES_DIR = SKILL_ROOT / "templates"
TEMPLATE_FILE = "template.json"
WORK_DIR = "_dsimage"
BATCH_FILE = "batch.json"
PROMPTS_FILE = "prompts.json"
BRIEF_FILE = "brief.md"
JOBS_FILE = "jobs.json"
MODES = ("replace", "smart")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
SLOT_FILE_RE = re.compile(r"^h\d+$", re.I)
SKU_RE = re.compile(r"[A-Za-z]{1,4}-?\d{3,}")
PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")
ALLOWED_PLACEHOLDERS = {"vary", "sku"}
DEFAULT_REFS = {"replace": ["@example", "@product.front"], "smart": ["@product.front"]}
DEFAULT_OUTPUT = {"ratio": "1:1", "resolution": "1k", "format": "png", "quality": "high"}
BYTES_RE = re.compile(r"^(\d+)(k|kb|m|mb|g|gb)?$", re.I)

SWAP_PREAMBLE = (
    "The first reference image is a locked layout master. The second reference image is the "
    "product to insert. Replace only the product in the master with the product from the second "
    "reference, keeping the exact master layout, background, typography, icons, callout lines, "
    "labels, grid, lighting, reflections, camera angle, scale and composition. Do not restyle, do "
    "not redraw the page, do not add or remove labels/icons/text, do not change the font. The new "
    "product must match the second reference exactly in shape, color, material, structure, "
    "hardware, logo and any charms, and must appear in the exact same pose, angle and position as "
    "the product in the master."
)


DEFAULT_DERIVE_BACK = {
    "prompt": (
        "Generate a clean studio product photo of the BACK of the exact product shown in the first "
        "image: straight rear view facing the camera, centered, on a plain light neutral background. "
        "Same color, material, stitching, hardware, proportions and scale as the first image; show only "
        "what would be visible from behind, do not invent features that the front view rules out. "
        "No text, no props, no people, no shadows on the background."
    ),
    "refs": ["@product.front"],
}


class DsError(Exception):
    """用户可读的失败原因。CLI 打印后退出 1。"""


def fail(message: str) -> None:
    raise DsError(message)


# ── 通用 ──────────────────────────────────────────────────

def natural_key(text: str) -> list[Any]:
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", text)]


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        fail(f"无法读取 {path}：{exc}")
    except json.JSONDecodeError as exc:
        fail(f"{path} 不是有效 JSON：{exc}")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES]
    return sorted(files, key=lambda p: natural_key(p.name))


def slot_images(folder: Path) -> list[Path]:
    return [p for p in list_images(folder) if SLOT_FILE_RE.match(p.stem)]


def parse_bytes(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        fail("max_bytes 不能是布尔值")
    if isinstance(value, int):
        if value <= 0:
            fail("max_bytes 必须大于 0")
        return value
    match = BYTES_RE.match(str(value).strip().replace(" ", ""))
    if not match:
        fail(f"无法解析体积：{value!r}（例如 2097152 或 2MB）")
    unit = (match.group(2) or "").lower().rstrip("b")
    return int(match.group(1)) * {"": 1, "k": 1024, "m": 1024 ** 2, "g": 1024 ** 3}[unit]


def image_size(path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return None


def ratio_of(width: int, height: int) -> str:
    target = width / height
    best, best_err = "1:1", float("inf")
    for item in gen_image.VALID_RATIOS:
        if item == "auto":
            continue
        left, right = item.split(":")
        err = abs(int(left) / int(right) - target)
        if err < best_err:
            best, best_err = item, err
    return best


# ── 模板 ──────────────────────────────────────────────────

def list_templates() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not TEMPLATES_DIR.is_dir():
        return items
    for folder in sorted(TEMPLATES_DIR.iterdir(), key=lambda p: natural_key(p.name)):
        if folder.is_dir() and (folder / TEMPLATE_FILE).is_file():
            try:
                data = read_json(folder / TEMPLATE_FILE)
            except DsError:
                data = {}
            items.append({
                "name": folder.name,
                "mode": data.get("mode", "?"),
                "category": data.get("category", ""),
                "slots": len(data.get("slots") or []),
                "path": folder,
            })
    return items


def find_template(name_or_path: str) -> Path:
    raw = Path(name_or_path)
    candidates = [raw, TEMPLATES_DIR / name_or_path]
    for candidate in candidates:
        folder = candidate.parent if candidate.name == TEMPLATE_FILE else candidate
        if (folder / TEMPLATE_FILE).is_file():
            return folder.resolve()
    names = "、".join(item["name"] for item in list_templates()) or "（空）"
    fail(f"找不到模板「{name_or_path}」。库里有：{names}")


def load_template(folder: Path) -> dict[str, Any]:
    data = read_json(folder / TEMPLATE_FILE)
    if not isinstance(data, dict):
        fail(f"{folder / TEMPLATE_FILE} 顶层应为对象")
    data["_dir"] = folder
    return data


def template_output(tpl: dict[str, Any]) -> dict[str, Any]:
    out = dict(DEFAULT_OUTPUT)
    raw = tpl.get("output") if isinstance(tpl.get("output"), dict) else {}
    for key in ("ratio", "resolution", "format", "quality"):
        if raw.get(key):
            out[key] = str(raw[key]).lower()
    if isinstance(raw.get("deliver"), dict):
        out["deliver"] = raw["deliver"]
    return out


def default_kind(tpl: dict[str, Any]) -> str | None:
    kinds = tpl.get("product_kinds")
    if isinstance(kinds, dict) and kinds:
        return next(iter(kinds))
    return None


def slot_refs(tpl: dict[str, Any], slot: dict[str, Any], kind: str | None = None) -> list[str]:
    by_kind = slot.get("refs_by_kind") if isinstance(slot.get("refs_by_kind"), dict) else {}
    refs = by_kind.get(kind) if kind else None
    if not refs:
        refs = slot.get("refs")
    if isinstance(refs, list) and refs:
        return [str(r) for r in refs]
    return list(DEFAULT_REFS[tpl.get("mode", "replace")])


def product_kind(tpl: dict[str, Any], product: dict[str, Any]) -> str | None:
    return product.get("kind") or default_kind(tpl)


def derive_back_spec(tpl: dict[str, Any]) -> dict[str, Any]:
    """模板写了 derive.back 用模板的，否则用通用背面派生。"""
    derive = tpl.get("derive") if isinstance(tpl.get("derive"), dict) else {}
    spec = derive.get("back")
    if isinstance(spec, dict) and str(spec.get("prompt") or "").strip():
        return {"prompt": str(spec["prompt"]), "refs": list(spec.get("refs") or ["@product.front"])}
    return {"prompt": DEFAULT_DERIVE_BACK["prompt"], "refs": list(DEFAULT_DERIVE_BACK["refs"])}


def slot_ids(tpl: dict[str, Any]) -> list[str]:
    return [str(s["id"]) for s in tpl.get("slots") or []]


def check_slot_ids(tpl: dict[str, Any], wanted: list[str] | None) -> None:
    if not wanted:
        return
    known = {s.lower() for s in slot_ids(tpl)}
    bad = [s for s in wanted if s.lower() not in known]
    if bad:
        fail(f"模板没有这些槽位：{'、'.join(bad)}。有：{'、'.join(slot_ids(tpl))}")


def slot_uses_back(tpl: dict[str, Any], slot: dict[str, Any], kind: str | None) -> bool:
    return "@product.back" in slot_refs(tpl, slot, kind)


def check_template(tpl: dict[str, Any]) -> list[str]:
    """返回问题列表；空列表 = 通过。"""
    errors: list[str] = []
    folder: Path = tpl["_dir"]
    mode = tpl.get("mode")
    if not tpl.get("name"):
        errors.append("缺 name")
    if mode not in MODES:
        errors.append(f"mode 应为 replace / smart，实际 {mode!r}")
        mode = "replace"
    out = template_output(tpl)
    if out["ratio"] not in gen_image.VALID_RATIOS or out["ratio"] == "auto":
        errors.append(f"output.ratio 非法：{out['ratio']}")
    if out["resolution"] not in gen_image.VALID_RESOLUTIONS:
        errors.append(f"output.resolution 应为 1k/2k/4k，实际 {out['resolution']}")
    if out["format"] not in gen_image.VALID_FORMATS:
        errors.append(f"output.format 应为 png/jpeg/webp，实际 {out['format']}")
    deliver = out.get("deliver")
    if deliver is not None:
        if not isinstance(deliver, dict):
            errors.append("output.deliver 应为对象")
        else:
            if ("width" in deliver) != ("height" in deliver):
                errors.append("output.deliver 的 width/height 必须成对")
            if deliver.get("width") and deliver.get("height"):
                if ratio_of(int(deliver["width"]), int(deliver["height"])) != out["ratio"]:
                    errors.append("output.deliver 宽高比例与 output.ratio 不一致，交付会变形")
            try:
                parse_bytes(deliver.get("max_bytes"))
            except DsError as exc:
                errors.append(f"output.deliver.max_bytes：{exc}")
    if mode == "smart" and not str(tpl.get("style") or "").strip():
        errors.append("smart 模板必须写 style（全套统一的风格锁）")
    kinds = tpl.get("product_kinds")
    if kinds is not None and (not isinstance(kinds, dict) or not kinds):
        errors.append("product_kinds 应为非空对象：{品类键: 说明}")
    kind_keys = set(kinds) if isinstance(kinds, dict) else set()

    derive = tpl.get("derive") if isinstance(tpl.get("derive"), dict) else {}
    for key, spec in derive.items():
        if key != "back":
            errors.append(f"derive 只支持 back（正面图永远来自产品，其他视角不派生），实际 {key!r}")
            continue
        if not isinstance(spec, dict) or not str(spec.get("prompt") or "").strip():
            errors.append(f"derive.{key} 缺 prompt")
            continue
        for ref in spec.get("refs") or ["@product.front"]:
            if ref == "@product.back" or ref == "@example":
                errors.append(f"derive.{key}.refs 不能用 {ref}")
            elif not str(ref).startswith("@") and not (folder / str(ref)).is_file():
                errors.append(f"derive.{key} 引用的文件不存在：{ref}")

    slots = tpl.get("slots")
    if not isinstance(slots, list) or not slots:
        errors.append("slots 为空")
        return errors
    seen: set[str] = set()
    for slot in slots:
        if not isinstance(slot, dict) or not slot.get("id"):
            errors.append(f"槽位缺 id：{slot}")
            continue
        sid = str(slot["id"])
        if sid.lower() in seen:
            errors.append(f"槽位 id 重复：{sid}")
        seen.add(sid.lower())
        if not SLOT_FILE_RE.match(sid):
            errors.append(f"槽位 id 应为 H1、H2… 这种形式，实际 {sid}")
        example = slot.get("example")
        if example and not (folder / str(example)).is_file():
            errors.append(f"{sid} 的示例图不存在：{example}")
        refs = list(slot_refs(tpl, slot))
        refs_by_kind = slot.get("refs_by_kind")
        if refs_by_kind is not None:
            if not isinstance(refs_by_kind, dict):
                errors.append(f"{sid} refs_by_kind 应为对象")
            else:
                for key, value in refs_by_kind.items():
                    if key not in kind_keys:
                        errors.append(f"{sid} refs_by_kind 的键 {key!r} 不在 product_kinds 里")
                    if not isinstance(value, list) or not value:
                        errors.append(f"{sid} refs_by_kind[{key!r}] 应为非空列表")
                    else:
                        refs += [str(r) for r in value]
        for ref in refs:
            if ref == "@example":
                if not example:
                    errors.append(f"{sid} refs 用了 @example 但没有 example")
            elif ref in ("@product.front", "@product.back"):
                pass
            elif ref.startswith("@"):
                errors.append(f"{sid} refs 有未知引用：{ref}（允许 @example / @product.front / @product.back / 模板内文件）")
            elif not (folder / ref).is_file():
                errors.append(f"{sid} 引用的文件不存在：{ref}")
        if mode == "replace":
            if not example:
                errors.append(f"{sid} 缺示例图（replace 模板每槽必须有 example）")
            prompt = str(slot.get("prompt") or "")
            if not prompt.strip():
                errors.append(f"{sid} 缺 prompt")
            texts = [prompt]
            by_kind = slot.get("prompt_by_kind")
            if by_kind is not None:
                if not isinstance(by_kind, dict):
                    errors.append(f"{sid} prompt_by_kind 应为对象")
                else:
                    for key, text in by_kind.items():
                        if key not in kind_keys:
                            errors.append(f"{sid} prompt_by_kind 的键 {key!r} 不在 product_kinds 里")
                        texts.append(str(text))
            vary = slot.get("vary")
            uses_vary = any("{vary}" in t for t in texts)
            if uses_vary and not (isinstance(vary, list) and vary):
                errors.append(f"{sid} prompt 用了 {{vary}} 但没有 vary 列表")
            if vary and not uses_vary:
                errors.append(f"{sid} 有 vary 列表但 prompt 里没有 {{vary}}")
            for text in texts:
                unknown = set(PLACEHOLDER_RE.findall(text)) - ALLOWED_PLACEHOLDERS
                if unknown:
                    errors.append(f"{sid} prompt 有未知占位符：{sorted(unknown)}（只允许 {{vary}} {{sku}}）")
        else:
            if not str(slot.get("brief") or "").strip():
                errors.append(f"{sid} 缺 brief（smart 模板每槽写要表达什么）")
    if kind_keys and slots:
        used = {k for s in slots for field in ("prompt_by_kind", "refs_by_kind")
                if isinstance(s.get(field), dict) for k in s[field]}
        unused = kind_keys - used - {default_kind(tpl)}
        if unused:
            errors.append(f"product_kinds 里这些品类没有任何槽位用到：{sorted(unused)}")
    return errors


def init_template(name: str, *, mode: str, from_dir: Path | None = None,
                  slot_count: int = 0, category: str = "", language: str = "") -> Path:
    if mode not in MODES:
        fail(f"mode 应为 replace / smart，实际 {mode!r}")
    folder = TEMPLATES_DIR / name
    if folder.exists():
        fail(f"模板已存在：{folder}")
    images: list[Path] = []
    if from_dir is not None:
        images = list_images(from_dir)
        if not images:
            fail(f"示例夹里没有图：{from_dir}")
    elif slot_count <= 0:
        fail("没有示例夹时要给 --slots 张数")
    folder.mkdir(parents=True)
    slots: list[dict[str, Any]] = []
    mapping: list[str] = []
    count = len(images) if images else slot_count
    ratio = DEFAULT_OUTPUT["ratio"]
    for index in range(1, count + 1):
        slot: dict[str, Any] = {"id": f"H{index}", "purpose": ""}
        if images:
            src = images[index - 1]
            example = f"h{index}{src.suffix.lower()}"
            shutil.copy2(src, folder / example)
            slot["example"] = example
            mapping.append(f"{example} ← {src.name}")
            if index == 1:
                size = image_size(folder / example)
                if size:
                    ratio = ratio_of(*size)
        if mode == "replace":
            slot["prompt"] = SWAP_PREAMBLE + f" H{index}: <这一页要保留什么、产品怎么摆>. Negative: <禁止什么>."
        else:
            slot["brief"] = ""
        slots.append(slot)
    data: dict[str, Any] = {
        "name": name,
        "mode": mode,
        "category": category,
        "language": language,
        "output": {"ratio": ratio, "resolution": "1k", "format": "png", "quality": "high"},
        "style": "",
        "text_policy": "",
        "slots": slots,
        "notes": ["init 生成的骨架，待填。示例图对应：" + "；".join(mapping)] if mapping else ["init 生成的骨架，待填"],
    }
    write_json(folder / TEMPLATE_FILE, data)
    return folder


def freeze_template(batch: dict[str, Any], sku: str, new_name: str) -> Path:
    """把 smart 批次里某个品这一轮的成图 + 实际用过的 prompt 冻成 replace 模板。"""
    tpl = load_template(Path(batch["template"]))
    if tpl.get("mode") != "smart":
        fail("freeze 只用于 smart 模板的批次；replace 模板本来就是冻住的")
    product = find_product(batch, sku)
    out_dir = Path(batch["output"]) / sku
    prompts = read_prompts(batch, sku, require_complete=True)
    folder = TEMPLATES_DIR / new_name
    if folder.exists():
        fail(f"模板已存在：{folder}")
    fmt = template_output(tpl)["format"]
    missing = [s["id"] for s in tpl["slots"] if gen_image._existing_output(out_dir, str(s["id"]).lower(), fmt) is None]
    if missing:
        fail(f"{sku} 还有槽位没出图，不能冻：{'、'.join(missing)}")
    folder.mkdir(parents=True)
    slots: list[dict[str, Any]] = []
    for slot in tpl["slots"]:
        sid = str(slot["id"])
        src = gen_image._existing_output(out_dir, sid.lower(), fmt)
        example = f"{sid.lower()}{src.suffix.lower()}"
        shutil.copy2(src, folder / example)
        slots.append({
            "id": sid,
            "purpose": slot.get("purpose", ""),
            "example": example,
            "refs": ["@example", "@product.front"],
            "prompt": SWAP_PREAMBLE + " " + sid + ": " + prompts[sid].strip(),
        })
    data = {
        "name": new_name,
        "mode": "replace",
        "category": tpl.get("category", ""),
        "language": tpl.get("language", ""),
        "output": tpl.get("output") or DEFAULT_OUTPUT,
        "text_policy": tpl.get("text_policy", "冻结母版全部文字、图标、版式；只换产品"),
        "slots": slots,
        "notes": [
            f"由 smart 模板「{tpl.get('name')}」的品 {product['sku']} 冻结而来",
            "每槽 prompt = 换货前缀 + 该品当时的生成 prompt，请通读一遍把「生成」口吻改成「保留」口吻",
        ],
    }
    if tpl.get("model"):
        data["model"] = tpl["model"]
    write_json(folder / TEMPLATE_FILE, data)
    return folder


# ── 扫品 ──────────────────────────────────────────────────

def _group_by_sku(folder: Path, images: list[Path]) -> dict[str, list[Path]]:
    buckets: dict[str, list[Path]] = {}
    unlabeled: list[Path] = []
    for path in images:
        codes = SKU_RE.findall(path.stem)
        if codes:
            buckets.setdefault(codes[0], []).append(path)
        else:
            unlabeled.append(path)
    if len(buckets) >= 2:
        if unlabeled:
            names = "、".join(p.name for p in unlabeled)
            fail(f"{folder.name} 里既有带编号的图也有没编号的图，拆不开：{names}")
        return buckets
    if len(buckets) == 1:
        sku, files = next(iter(buckets.items()))
        return {sku: files + unlabeled}
    if len(SKU_RE.findall(folder.name)) >= 2:
        fail(f"{folder.name} 是号段夹，但图片文件名没有商品编号，拆不开")
    return {folder.name: images}


def make_product(sku: str, folder_name: str, files: list[Path]) -> dict[str, Any]:
    """一张图就是白图；多张图留空，由 Agent 看图后用 set --front / --back 指定。"""
    return {
        "sku": sku,
        "folder": folder_name,
        "front": str(files[0].resolve()) if len(files) == 1 else None,
        "back": None,
        "images": [str(p.resolve()) for p in files],
        "kind": None,
        "vary": {},
    }


def scan_source(source: Path) -> list[dict[str, Any]]:
    source = source.resolve()
    if source.is_file():
        if source.suffix.lower() not in IMAGE_SUFFIXES:
            fail(f"不是图片：{source}")
        return [make_product(source.stem, source.parent.name, [source])]
    if not source.is_dir():
        fail(f"源不存在：{source}")
    direct = list_images(source)
    subdirs = [p for p in sorted(source.iterdir(), key=lambda p: natural_key(p.name))
               if p.is_dir() and not p.name.startswith((".", "_")) and list_images(p)]
    if direct and not subdirs:
        products = []
        for sku, files in _group_by_sku(source, direct).items():
            products.append(make_product(sku, source.name, files))
        return products
    if not subdirs:
        fail(f"源目录里没有图：{source}")
    products: list[dict[str, Any]] = []
    seen: set[str] = set()
    for folder in subdirs:
        for sku, files in _group_by_sku(folder, list_images(folder)).items():
            if sku in seen:
                fail(f"商品编号重复：{sku}")
            seen.add(sku)
            products.append(make_product(sku, folder.name, files))
    return products


def loose_images(source: Path) -> list[Path]:
    """源根目录下既有子夹又有散图时，散图不归任何品；返回它们让 init 提醒。"""
    source = source.resolve()
    if not source.is_dir():
        return []
    direct = list_images(source)
    has_subdirs = any(p.is_dir() and not p.name.startswith((".", "_")) and list_images(p) for p in source.iterdir())
    return direct if (direct and has_subdirs) else []


def default_output_dir(source: Path) -> Path:
    source = source.resolve()
    name = source.stem if source.is_file() else source.name
    if name.endswith("系列"):
        name = name[:-2]
    return source.parent / f"{name}生成"


# ── 批次 ──────────────────────────────────────────────────

def batch_path(output: Path) -> Path:
    return output / WORK_DIR / BATCH_FILE


def work_dir(batch: dict[str, Any], sku: str) -> Path:
    return Path(batch["output"]) / WORK_DIR / sku


def init_batch(template: Path, source: Path, output: Path | None = None) -> dict[str, Any]:
    tpl = load_template(template)
    problems = check_template(tpl)
    if problems:
        fail("模板没过校验，先修：\n  " + "\n  ".join(problems))
    products = scan_source(source)
    kind = default_kind(tpl)
    for product in products:
        product["kind"] = kind
    out = (output or default_output_dir(source)).resolve()
    path = batch_path(out)
    if path.is_file():
        old = read_json(path)
        old_products = {p["sku"]: p for p in old.get("products", [])}
        for product in products:
            prev = old_products.get(product["sku"])
            if prev:
                product["kind"] = prev.get("kind") or kind
                product["vary"] = prev.get("vary") or {}
                if prev.get("front"):
                    product["front"] = prev["front"]
                if prev.get("back"):
                    product["back"] = prev["back"]
    batch = {
        "template": str(template),
        "mode": tpl["mode"],
        "source": str(source.resolve()),
        "output": str(out),
        "products": products,
    }
    write_json(path, batch)
    for product in products:
        copy_product_refs(out, product)
    return batch


def copy_product_refs(out: Path, product: dict[str, Any]) -> None:
    """把选定的白图/背面原图迁进该品成图夹（成品要求：套图 + 一张白图）。"""
    dest = out / product["sku"]
    dest.mkdir(parents=True, exist_ok=True)
    for key in ("front", "back"):
        src = product.get(key)
        if src and Path(src).is_file():
            target = dest / Path(src).name
            if not target.exists():
                shutil.copy2(src, target)


def has_front(product: dict[str, Any]) -> bool:
    return bool(product.get("front")) and Path(str(product["front"])).is_file()


def load_batch(output_or_batch: Path) -> dict[str, Any]:
    path = output_or_batch
    if path.is_dir():
        path = batch_path(path)
    if not path.is_file():
        fail(f"找不到批次文件：{path}（先 dsimage.py init）")
    batch = read_json(path)
    batch["_path"] = path
    if not Path(batch["template"]).is_dir():
        fail(f"批次引用的模板不存在了：{batch['template']}")
    return batch


def save_batch(batch: dict[str, Any]) -> None:
    payload = {k: v for k, v in batch.items() if not k.startswith("_")}
    write_json(batch["_path"], payload)


def find_product(batch: dict[str, Any], sku: str) -> dict[str, Any]:
    for product in batch["products"]:
        if product["sku"] == sku:
            return product
    fail(f"批次里没有商品 {sku}。有：{'、'.join(p['sku'] for p in batch['products'])}")


def select_products(batch: dict[str, Any], only: list[str] | None) -> list[dict[str, Any]]:
    if not only:
        return list(batch["products"])
    return [find_product(batch, sku) for sku in only]


# ── 组 jobs ───────────────────────────────────────────────

def slot_prompt(tpl: dict[str, Any], slot: dict[str, Any], product: dict[str, Any], index: int) -> str:
    kind = product_kind(tpl, product)
    by_kind = slot.get("prompt_by_kind") if isinstance(slot.get("prompt_by_kind"), dict) else {}
    text = str(by_kind.get(kind) or slot.get("prompt") or "")
    if "{vary}" in text:
        custom = str((product.get("vary") or {}).get(slot["id"]) or "").strip()
        if not custom:
            options = slot.get("vary") or []
            custom = str(options[index % len(options)]) if options else ""
        text = text.replace("{vary}", custom)
    return text.replace("{sku}", product["sku"]).strip()


def derived_back(batch: dict[str, Any], product: dict[str, Any], fmt: str) -> Path | None:
    return gen_image._existing_output(work_dir(batch, product["sku"]), "back", fmt)


def product_needs_back(tpl: dict[str, Any], product: dict[str, Any], only_slots: list[str] | None = None) -> bool:
    """这个品按当前品类，有没有槽位要用背面图。"""
    wanted = {s.lower() for s in only_slots} if only_slots else None
    kind = product_kind(tpl, product)
    return any(slot_uses_back(tpl, s, kind) for s in tpl["slots"]
               if not wanted or str(s["id"]).lower() in wanted)


def back_source(batch: dict[str, Any], tpl: dict[str, Any], product: dict[str, Any]) -> tuple[str, Path | None]:
    """背面图从哪来：('product', 路径) 真图；('derived', 路径) 已派生；('missing', None) 还没有。"""
    if product.get("back") and Path(product["back"]).is_file():
        return "product", Path(product["back"])
    derived = derived_back(batch, product, template_output(tpl)["format"])
    if derived is not None:
        return "derived", derived
    return "missing", None


def resolve_refs(refs: list[str], tpl: dict[str, Any], slot: dict[str, Any] | None,
                 batch: dict[str, Any], product: dict[str, Any]) -> tuple[list[str], bool]:
    """返回 (路径列表, 是否缺背面需派生)。"""
    folder: Path = tpl["_dir"]
    fmt = template_output(tpl)["format"]
    paths: list[str] = []
    need_back = False
    for ref in refs:
        if ref == "@example":
            if not slot or not slot.get("example"):
                fail(f"槽位 {slot and slot.get('id')} 没有 example，refs 却要 @example")
            paths.append(str(folder / str(slot["example"])))
        elif ref == "@product.front":
            paths.append(str(product["front"]))
        elif ref == "@product.back":
            if product.get("back") and Path(product["back"]).is_file():
                paths.append(str(product["back"]))
            else:
                derived = derived_back(batch, product, fmt)
                if derived is None:
                    need_back = True
                else:
                    paths.append(str(derived))
        elif ref.startswith("@"):
            fail(f"未知引用 {ref}")
        else:
            paths.append(str(folder / ref))
    return paths, need_back


def _job(slot_id: str, prompt: str, images: list[str], out: dict[str, Any], output_dir: Path,
         label: str) -> dict[str, Any]:
    return {
        "slot": slot_id,
        "prompt": prompt,
        "image": images,
        "size": out["ratio"],
        "resolution": out["resolution"],
        "format": out["format"],
        "quality": out["quality"],
        "output_dir": str(output_dir),
        "job_id": label,
        "label": label,
    }


def build_jobs(batch: dict[str, Any], tpl: dict[str, Any], product: dict[str, Any], index: int,
               only_slots: list[str] | None = None,
               prompts: dict[str, str] | None = None) -> dict[str, Any]:
    """返回 {"derive": [...], "slots": [...], "blocked": [(slot, reason)]}。"""
    out = template_output(tpl)
    sku = product["sku"]
    dest = Path(batch["output"]) / sku
    work = work_dir(batch, sku)
    wanted = {s.lower() for s in only_slots} if only_slots else None
    derive_jobs: list[dict[str, Any]] = []
    slot_jobs: list[dict[str, Any]] = []
    blocked: list[tuple[str, str]] = []
    derive_spec = derive_back_spec(tpl)
    back_queued = False
    if not has_front(product):
        reason = "还没选白图（set --front）" if not product.get("front") else f"白图文件不存在：{product['front']}"
        for slot in tpl["slots"]:
            if not wanted or str(slot["id"]).lower() in wanted:
                blocked.append((str(slot["id"]), reason))
        return {"derive": [], "slots": [], "blocked": blocked}
    for slot in tpl["slots"]:
        sid = str(slot["id"])
        if wanted and sid.lower() not in wanted:
            continue
        if tpl["mode"] == "smart":
            prompt = str((prompts or {}).get(sid) or "").strip()
            if not prompt:
                blocked.append((sid, "prompts.json 还没填"))
                continue
        else:
            prompt = slot_prompt(tpl, slot, product, index)
        refs = slot_refs(tpl, slot, product_kind(tpl, product))
        images, need_back = resolve_refs(refs, tpl, slot, batch, product)
        if need_back:
            if not back_queued:
                d_imgs, _ = resolve_refs(derive_spec["refs"], tpl, None, batch, product)
                derive_jobs.append(_job("back", str(derive_spec["prompt"]).replace("{sku}", sku),
                                        d_imgs, out, work, f"{sku}/back"))
                back_queued = True
            images = _with_pending_back(images, refs, work, out["format"])
        slot_jobs.append(_job(sid, prompt, images, out, dest, f"{sku}/{sid}"))
    return {"derive": derive_jobs, "slots": slot_jobs, "blocked": blocked}


def _with_pending_back(images: list[str], refs: list[str], work: Path, fmt: str) -> list[str]:
    """派生图还没生成时，按 refs 顺序把将来的 back 路径插进去。"""
    result: list[str] = []
    cursor = 0
    for ref in refs:
        if ref == "@product.back":
            result.append(str(work / f"back.{fmt}"))
        else:
            result.append(images[cursor])
            cursor += 1
    return result


def write_jobs_file(batch: dict[str, Any], sku: str, plan: dict[str, Any]) -> Path:
    path = work_dir(batch, sku) / JOBS_FILE
    write_json(path, {"derive": plan["derive"], "jobs": plan["slots"],
                      "blocked": [{"slot": s, "reason": r} for s, r in plan["blocked"]]})
    return path


def to_pool_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pool: list[dict[str, Any]] = []
    for job in jobs:
        args = argparse.Namespace(
            size=job["size"], resolution=job["resolution"], quality=job["quality"], n=1,
            image=list(job["image"]), format=job["format"], timeout=None, poll_interval=5,
        )
        pool.append({
            "slot": job["slot"], "prompt": job["prompt"], "args": args,
            "output_dir": Path(job["output_dir"]), "job_id": job["job_id"], "label": job["label"],
        })
    return pool


# ── smart：brief + prompts ────────────────────────────────

def write_smart_packet(batch: dict[str, Any], tpl: dict[str, Any], product: dict[str, Any]) -> Path:
    sku = product["sku"]
    work = work_dir(batch, sku)
    work.mkdir(parents=True, exist_ok=True)
    prompts_path = work / PROMPTS_FILE
    existing = read_json(prompts_path) if prompts_path.is_file() else {}
    if not isinstance(existing, dict):
        existing = {}
    prompts = {str(s["id"]): str(existing.get(str(s["id"])) or "") for s in tpl["slots"]}
    write_json(prompts_path, prompts)
    out = template_output(tpl)
    lines = [
        f"# {sku} · 模板「{tpl.get('name')}」（smart）",
        "",
        "把每槽 prompt 写进同目录 prompts.json（键 = 槽位 id，值 = 完整英文 prompt）。写完跑 run 出图。",
        "",
        "## 全套约束",
        f"- 品类：{tpl.get('category') or '（未写）'}；本品品类标签：{product.get('kind') or '（无）'}",
        f"- 图内文字语言：{tpl.get('language') or '（未写）'}",
        f"- 画幅 {out['ratio']}，{out['resolution']}，{out['format']}",
        f"- 文字策略：{tpl.get('text_policy') or '（未写）'}",
        "",
        "## 风格锁（每条 prompt 开头原样带上）",
        "",
        str(tpl.get("style") or "").strip(),
        "",
        "## 产品图",
        f"- 正面 / 白图：{product.get('front') or '（未选，先 set --front）'}",
        "- 背面：" + (product.get("back") or (
            "（无；有槽位要背面，出图时会先用正面图派生一张，可先 derive 看）"
            if product_needs_back(tpl, product) else "（无，本模板不需要）")),
    ]
    extra = [p for p in product.get("images", []) if p not in (product.get("front"), product.get("back"))]
    if extra:
        lines.append("- 其他：" + "；".join(extra))
    lines += ["", "## 槽位"]
    for slot in tpl["slots"]:
        sid = str(slot["id"])
        refs = slot_refs(tpl, slot, product_kind(tpl, product))
        lines += [
            "",
            f"### {sid} · {slot.get('purpose') or ''}",
            str(slot.get("brief") or "").strip(),
            f"- 参考图顺序：{' , '.join(refs)}",
        ]
        if slot.get("example"):
            lines.append(f"- 版式示例（看，不当母版）：{tpl['_dir'] / str(slot['example'])}")
    notes = tpl.get("notes") or []
    if notes:
        lines += ["", "## 备注", *[f"- {n}" for n in notes]]
    (work / BRIEF_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return work / BRIEF_FILE


def read_prompts(batch: dict[str, Any], sku: str, *, require_complete: bool = False) -> dict[str, str]:
    path = work_dir(batch, sku) / PROMPTS_FILE
    if not path.is_file():
        if require_complete:
            fail(f"{sku} 没有 prompts.json")
        return {}
    data = read_json(path)
    if not isinstance(data, dict):
        fail(f"{path} 应为对象：{{槽位: prompt}}")
    prompts = {str(k): str(v or "") for k, v in data.items()}
    if require_complete:
        empty = [k for k, v in prompts.items() if not v.strip()]
        if empty:
            fail(f"{sku} 的 prompts.json 还有空槽：{'、'.join(empty)}")
    return prompts


# ── 状态 ──────────────────────────────────────────────────

def product_status(batch: dict[str, Any], tpl: dict[str, Any], product: dict[str, Any]) -> dict[str, Any]:
    fmt = template_output(tpl)["format"]
    dest = Path(batch["output"]) / product["sku"]
    done, missing = [], []
    for slot in tpl["slots"]:
        sid = str(slot["id"])
        (done if gen_image._existing_output(dest, sid.lower(), fmt) else missing).append(sid)
    state = "done" if not missing else "pending"
    if missing and tpl["mode"] == "smart":
        prompts = read_prompts(batch, product["sku"])
        if any(not prompts.get(sid, "").strip() for sid in missing):
            state = "needs_prompts"
    if missing and not has_front(product):
        state = "needs_front" if not product.get("front") else "no_image"
    return {"sku": product["sku"], "kind": product.get("kind"), "done": done, "missing": missing, "state": state}


STATE_LABEL = {
    "done": "完成", "pending": "待出图", "needs_prompts": "待写 prompt",
    "needs_front": "待选白图", "no_image": "白图文件丢了",
}


def format_status(batch: dict[str, Any], tpl: dict[str, Any]) -> str:
    rows = [product_status(batch, tpl, p) for p in batch["products"]]
    tally: dict[str, int] = {}
    for row in rows:
        tally[row["state"]] = tally.get(row["state"], 0) + 1
    lines = [
        f"模板：{tpl.get('name')}（{tpl['mode']}）  {Path(batch['template'])}",
        f"源：{batch['source']}",
        f"成图：{batch['output']}",
        "  ".join(f"{STATE_LABEL[k]} {v}" for k, v in tally.items()),
        "",
    ]
    for row in rows:
        detail = f"{len(row['done'])}/{len(row['done']) + len(row['missing'])}"
        kind = f"  [{row['kind']}]" if row["kind"] else ""
        missing = f"  缺 {'、'.join(row['missing'])}" if row["missing"] and row["state"] != "done" else ""
        lines.append(f"{STATE_LABEL[row['state']]:6} {row['sku']:<14} {detail}{kind}{missing}")
    return "\n".join(lines)


# ── 交付压图 ──────────────────────────────────────────────

def _pil():
    try:
        from PIL import Image
    except ImportError:
        fail("这一步需要 Pillow：pip install pillow")
    return Image


def _save_under_bytes(image: Any, path: Path, max_bytes: int | None, fmt: str) -> Path:
    fmt = "jpeg" if fmt in ("jpg", "jpeg") else fmt
    work = image
    if fmt == "jpeg" and work.mode in {"RGBA", "P", "LA"}:
        work = work.convert("RGB")
    quality = 92
    while True:
        if fmt == "jpeg":
            work.save(path, format="JPEG", quality=quality, optimize=True)
        elif fmt == "webp":
            work.save(path, format="WEBP", quality=quality, method=6)
        else:
            work.save(path, format="PNG", optimize=True)
        if max_bytes is None or path.stat().st_size <= max_bytes or quality <= 40:
            break
        if fmt == "png":
            jpeg_path = path.with_suffix(".jpg")
            rgb = work.convert("RGB") if work.mode != "RGB" else work
            result = _save_under_bytes(rgb, jpeg_path, max_bytes, "jpeg")
            path.unlink(missing_ok=True)
            return result
        quality -= 8
    if max_bytes is not None and path.stat().st_size > max_bytes:
        fail(f"压到 quality=40 仍超过 {max_bytes} 字节：{path}")
    return path


def deliver_image(path: Path, spec: dict[str, Any]) -> Path:
    Image = _pil()
    width = int(spec["width"]) if spec.get("width") else None
    height = int(spec["height"]) if spec.get("height") else None
    max_px = int(spec["max_px"]) if spec.get("max_px") else None
    max_bytes = parse_bytes(spec.get("max_bytes"))
    with Image.open(path) as raw:
        image = raw.copy()
    resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
    if width and height:
        if ratio_of(width, height) != ratio_of(image.width, image.height):
            fail(f"{path.name} 是 {image.width}×{image.height}，交付要 {width}×{height}，比例不同不能压变形")
        if image.width > width or image.height > height:
            image.thumbnail((width, height), resample)
    elif max_px and (image.width > max_px or image.height > max_px):
        image.thumbnail((max_px, max_px), resample)
    return _save_under_bytes(image, path, max_bytes, path.suffix.lower().lstrip(".") or "png")


def deliver_batch(batch: dict[str, Any], tpl: dict[str, Any], only: list[str] | None = None) -> list[Path]:
    spec = template_output(tpl).get("deliver")
    if not isinstance(spec, dict) or not spec:
        fail("模板 output 里没有 deliver，不知道要压成多大。写 width/height 或 max_px，可选 max_bytes")
    changed: list[Path] = []
    for product in select_products(batch, only):
        folder = Path(batch["output"]) / product["sku"]
        for image in slot_images(folder):
            changed.append(deliver_image(image, spec))
    return changed


# ── 预览拼图 ──────────────────────────────────────────────

def preview_product(batch: dict[str, Any], tpl: dict[str, Any], product: dict[str, Any],
                    cell: int = 320) -> Path | None:
    Image = _pil()
    from PIL import ImageDraw

    folder = Path(batch["output"]) / product["sku"]
    fmt = template_output(tpl)["format"]
    tiles: list[tuple[str, Path | None]] = []
    for slot in tpl["slots"]:
        sid = str(slot["id"])
        tiles.append((sid, gen_image._existing_output(folder, sid.lower(), fmt)))
    if not any(path for _, path in tiles):
        return None
    cols = min(3, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    label_h = 28
    sheet = Image.new("RGB", (cols * cell, rows * (cell + label_h)), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    for index, (sid, path) in enumerate(tiles):
        x = (index % cols) * cell
        y = (index // cols) * (cell + label_h)
        if path:
            with Image.open(path) as raw:
                thumb = raw.convert("RGB")
                thumb.thumbnail((cell, cell))
            sheet.paste(thumb, (x + (cell - thumb.width) // 2, y + (cell - thumb.height) // 2))
        else:
            draw.rectangle([x + 8, y + 8, x + cell - 8, y + cell - 8], outline=(200, 200, 200))
        draw.text((x + 8, y + cell + 6), f"{sid}  {'' if path else '缺'}", fill=(40, 40, 40))
    out = work_dir(batch, product["sku"]) / "preview.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


# ── 生图 ──────────────────────────────────────────────────

def run_pool(jobs: list[dict[str, Any]], *, concurrency: int, redo: bool, env_file: str | None,
             api_mode: str | None, model_pin: str | None, label: str) -> list[str]:
    if not jobs:
        return []
    env_path = Path(env_file) if env_file else gen_image.find_default_env_file()
    gen_image.load_env_file(env_path)
    if model_pin:
        os.environ["IMG_MODEL"] = model_pin
    provider, base_url, model, api_key = gen_image.resolve_runtime()
    mode = gen_image.detect_mode(provider, base_url, api_mode)
    pool = to_pool_jobs(jobs)
    results = gen_image.run_job_pool(
        pool, concurrency=concurrency, skip_existing=not redo, base_url=base_url,
        api_key=api_key, model=model, mode=mode, log_label=label,
    )
    return gen_image.print_pool_results(pool, results)
