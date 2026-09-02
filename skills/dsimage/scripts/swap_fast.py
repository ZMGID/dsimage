#!/usr/bin/env python3
"""lock=master 换货：Agent 看图选定白图后，一句提示词 + 母版/产品图由脚本填 jobs。

默认提示词只写在这里。填 jobs、交付压图都从这里走；CLI 入口仍是 queue_pack.py。
选哪张商品图是 Agent 的事，不要靠文件名猜完就出。
"""
from __future__ import annotations

import json
import math
import random
import re
import shutil
import struct
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
import queue_pack  # noqa: E402

DEFAULT_PROMPT = (
    "Replace only the product in the first image with the product from the second image. "
    "Keep layout, text, icons, and background unchanged."
)

PROMPT_FILE = "swap_prompt.txt"
SLOT_PROMPT = "swap_prompt-{slot}.txt"
REF_TOKENS = {
    "colorway": ("配色", "colorway", "多色", "色卡", "各色"),
    "detail": ("细节", "detail", "macro", "特写"),
    "back": ("背面", "back"),
    "side": ("侧面", "side"),
    "front": ("正面", "front", "主图", "hero"),
}
SKU_RE = re.compile(r"[A-Za-z]+-?\d{3,}")
COLOR_TOKENS = (
    "海军", "卡其", "黑", "白", "米", "红", "蓝", "绿", "灰", "棕", "粉",
    "杏", "橘", "紫", "驼",
)
SLOT_RE = re.compile(r"^h?(\d+)$", re.I)
SLOT_IN_NAME = re.compile(r"h(\d+)", re.I)
BYTES_RE = re.compile(r"^(\d+)(k|kb|m|mb|g|gb)?$", re.I)
WH_RE = re.compile(r"^\s*(\d+)\s*[x×*]\s*(\d+)\s*$", re.I)
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def fail(message: str) -> None:
    queue_pack.fail(message)


def default_output_dir(source: Path) -> Path:
    name = source.name
    if name.endswith("系列"):
        return source.parent / f"{name[:-2]}生成"
    return source.parent / f"{name}生成"


def sku_codes(text: str) -> list[str]:
    return SKU_RE.findall(text)


def color_of(stem: str) -> str | None:
    for token in COLOR_TOKENS:
        if token in stem:
            return token
    return None


def pick_colorway(files: list[Path], rng: random.Random) -> list[Path]:
    if len(files) <= 1:
        return list(files)
    groups: dict[str, list[Path]] = {}
    for path in files:
        color = color_of(path.stem)
        if color:
            groups.setdefault(color, []).append(path)
    if len(groups) >= 2:
        return list(groups[rng.choice(sorted(groups))])
    return list(files)


def expand_client_source(
    source: Path,
    rng: random.Random | None = None,
) -> list[dict[str, Any]]:
    rng = rng or random.Random()
    folders = queue_pack.list_product_dirs(source)
    if not folders:
        fail(f"源目录里没有带图的子文件夹：{source}")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for folder in folders:
        images = queue_pack.product_images(folder)
        buckets: dict[str, list[Path]] = {}
        unlabeled: list[Path] = []
        for path in images:
            codes = sku_codes(path.stem)
            if codes:
                buckets.setdefault(codes[0], []).append(path)
            else:
                unlabeled.append(path)
        if len(buckets) >= 2:
            if unlabeled:
                names = "、".join(path.name for path in unlabeled)
                fail(f"{folder.name} 里有带编号的图，也有没编号的图，拆不开：{names}")
            grouped = buckets
        elif len(buckets) == 1:
            sku, files = next(iter(buckets.items()))
            grouped = {sku: files + unlabeled}
        else:
            if len(sku_codes(folder.name)) >= 2:
                fail(f"{folder.name} 是号段夹，但图片文件名没有商品编号，拆不开")
            grouped = {folder.name: images}
        for sku, files in grouped.items():
            chosen = pick_colorway(files, rng)
            if not chosen:
                continue
            if sku in seen:
                fail(f"商品编号重复：{sku}")
            seen.add(sku)
            items.append({"sku": sku, "from_folder": folder.name, "files": chosen})
    if not items:
        fail(f"源目录没有可出的品：{source}")
    return items


def materialize_products(
    output: Path,
    items: list[dict[str, Any]],
    only: list[str] | None = None,
    skip: set[str] | None = None,
) -> None:
    skip = skip or set()
    wanted = [name for name in (only or []) if name]
    for item in items:
        sku = str(item["sku"])
        if sku in skip or (wanted and sku not in wanted):
            continue
        dest = output / sku
        dest.mkdir(parents=True, exist_ok=True)
        for src in item["files"]:
            target = dest / Path(src).name
            if not target.exists():
                shutil.copy2(src, target)


def resolve_product_names(
    items: list[dict[str, Any]],
    names: list[str],
) -> tuple[list[str], list[str]]:
    sku_set = {str(item["sku"]) for item in items}
    by_folder: dict[str, list[str]] = {}
    for item in items:
        by_folder.setdefault(str(item["from_folder"]), []).append(str(item["sku"]))
    resolved: list[str] = []
    missing: list[str] = []
    for name in names:
        if name in sku_set:
            resolved.append(name)
        elif name in by_folder:
            resolved.extend(by_folder[name])
        else:
            missing.append(name)
    return resolved, missing


def ratio_from_wh(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        return "1:1"
    divisor = math.gcd(width, height)
    simple = f"{width // divisor}:{height // divisor}"
    if simple in gen_image.VALID_RATIOS:
        return simple
    target = width / height
    best = "1:1"
    best_err = float("inf")
    for item in gen_image.VALID_RATIOS:
        if item == "auto" or ":" not in item:
            continue
        left, right = item.split(":", 1)
        err = abs(int(left) / int(right) - target)
        if err < best_err:
            best, best_err = item, err
    return best


def _jpeg_wh(data: bytes) -> tuple[int, int] | None:
    if data[:2] != b"\xff\xd8":
        return None
    index = 2
    length = len(data)
    while index + 9 < length:
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = (data[index + 5] << 8) | data[index + 6]
            width = (data[index + 7] << 8) | data[index + 8]
            if width > 0 and height > 0:
                return width, height
            return None
        if marker in {0xD8, 0xD9, 0x01} or 0xD0 <= marker <= 0xD7:
            index += 2
            continue
        if index + 3 >= length:
            break
        seglen = (data[index + 2] << 8) | data[index + 3]
        if seglen < 2:
            break
        index += 2 + seglen
    return None


def read_wh(path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image
        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        pass
    try:
        data = path.read_bytes()[:65536]
    except OSError:
        return None
    if len(data) >= 24 and data[:8] == PNG_MAGIC:
        width, height = struct.unpack(">II", data[16:24])
        if width > 0 and height > 0:
            return width, height
    return _jpeg_wh(data)


def ratio_of_image(path: Path, fallback: str = "1:1") -> str:
    size = read_wh(path)
    if size is None:
        return fallback
    return ratio_from_wh(*size)


def parse_output_size(value: Any) -> dict[str, Any] | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    folded = text.casefold()
    if ":" in text and "x" not in folded and "*" not in text and "×" not in text:
        try:
            ratio = gen_image.size_to_ratio(text)
        except gen_image.GenError as exc:
            fail(str(exc))
        if ratio == "auto":
            fail("交付比例不能是 auto")
        return {"ratio": ratio}
    match = WH_RE.match(text)
    if not match:
        fail(f"无法解析输出尺寸：{value!r}（用 宽x高、宽*高 或比例如 1:1）")
    width, height = int(match.group(1)), int(match.group(2))
    if width <= 0 or height <= 0:
        fail("输出宽高必须大于 0")
    return {"ratio": ratio_from_wh(width, height), "width": width, "height": height}


def require_pack_ratio(pack: list[Any], wanted: str, label: str) -> None:
    mismatched = []
    for item in pack:
        if not isinstance(item, dict):
            continue
        have = str(item.get("ratio") or "")
        if have != wanted:
            mismatched.append(f"{item.get('slot') or '?'} {have}")
    if not mismatched:
        return
    fail(
        f"要 {label}（生图 {wanted}），但这些槽位母版对不上：{'、'.join(mismatched)}。"
        f"不能变形压缩。按母版比例出，或换 {wanted} 母版。"
    )


def classify_stem(name: str) -> str | None:
    stem = Path(name).stem.casefold()
    for ref, tokens in REF_TOKENS.items():
        if any(token.casefold() in stem for token in tokens):
            return ref
    return None


def slot_from_name(name: str, index: int) -> str:
    stem = Path(name).stem.strip()
    match = SLOT_RE.match(stem)
    if match:
        return f"H{int(match.group(1))}"
    match = SLOT_IN_NAME.search(stem)
    if match:
        return f"H{int(match.group(1))}"
    return f"H{index}"


def pick_product_image(folder: Path, product_ref: str) -> Path | None:
    images = queue_pack.ref_images(folder)
    if not images:
        images = queue_pack.product_images(folder, skip_slots=True)
    if not images:
        return None
    if len(images) == 1:
        return images[0]
    classified = [(path, classify_stem(path.name)) for path in images]
    matches = [path for path, kind in classified if kind == product_ref]
    if matches:
        return matches[0]
    unlabeled = [path for path, kind in classified if kind is None]
    if unlabeled:
        return unlabeled[0]
    return classified[0][0]


def infer_pack(masters_dir: Path) -> list[dict[str, str]]:
    files = queue_pack.product_images(masters_dir)
    if not files:
        fail(f"母版文件夹里没有图：{masters_dir}")
    used: set[str] = set()
    slots: list[dict[str, str]] = []
    for index, path in enumerate(files, start=1):
        slot = slot_from_name(path.name, index)
        if slot.lower() in used:
            slot = f"H{index}"
        suffix = 2
        while slot.lower() in used:
            slot = f"H{index}{suffix}"
            suffix += 1
        used.add(slot.lower())
        slots.append({
            "slot": slot,
            "purpose": path.stem,
            "example": path.name,
            "product_ref": classify_stem(path.name) or "front",
            "ratio": ratio_of_image(path),
        })
    return slots


def pack_from_template(path: Path) -> list[dict[str, Any]]:
    data = queue_pack.load_json(path)
    if not data:
        fail(f"无法读取模板：{path}")
    lock, _style = queue_pack.read_style_lock(path)
    if lock != "master":
        fail(f"换货需要 lock=master 的模板，这份是 {lock}：{path}")
    pack = data.get("pack") if isinstance(data.get("pack"), dict) else {}
    images = pack.get("images") if isinstance(pack, dict) else []
    if not isinstance(images, list) or not images:
        fail(f"模板 pack.images 为空：{path}")
    slots: list[dict[str, Any]] = []
    for item in images:
        if not isinstance(item, dict):
            continue
        example = str(item.get("example") or "")
        slot = str(item.get("slot") or "")
        pref = str(item.get("product_ref") or "front")
        if not slot or not example:
            fail(f"模板槽位缺 slot/example：{item}")
        master = path.parent / example
        if not master.is_file():
            fail(f"母版不存在：{master}")
        slots.append({
            "slot": slot,
            "purpose": str(item.get("purpose") or slot),
            "example": example,
            "product_ref": pref,
            "ratio": ratio_of_image(master, fallback=str(item.get("ratio") or "1:1")),
        })
    if not slots:
        fail(f"模板没有可用槽位：{path}")
    return slots


def parse_bytes(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        fail("max_bytes 不能是布尔值")
    if isinstance(value, int):
        if value <= 0:
            fail("max_bytes 必须大于 0")
        return value
    text = str(value).strip().casefold().replace(" ", "")
    match = BYTES_RE.match(text)
    if not match:
        fail(f"无法解析体积：{value!r}（例如 2097152 或 2MB）")
    amount = int(match.group(1))
    unit = (match.group(2) or "").rstrip("b")
    factor = {"": 1, "k": 1024, "m": 1024 ** 2, "g": 1024 ** 3}[unit]
    result = amount * factor
    if result <= 0:
        fail("max_bytes 必须大于 0")
    return result


def parse_resolution(value: Any) -> str | None:
    if value is None or value == "":
        return None
    text = str(value).strip().casefold()
    text = {"1": "1k", "2": "2k", "4": "4k"}.get(text, text)
    if text.isdigit() or "x" in text or "×" in text or "*" in text:
        fail(
            f"{value!r} 不是生图档。生图用 1k / 2k / 4k；"
            "精确画布走 --output-size 宽x高（按同一比例生再缩）；只限长边走 --max-px"
        )
    if text not in gen_image.VALID_RESOLUTIONS:
        fail(f"resolution 应为 1k / 2k / 4k，实际 {value!r}")
    return text


def parse_inspect_every(value: Any) -> int:
    if value is None or value == "":
        return 0
    try:
        number = int(value)
    except (TypeError, ValueError):
        fail(f"inspect_every 应为整数（0 表示不停）：{value!r}")
    if number < 0:
        fail("inspect_every 不能为负数")
    return number


def apply_generation_overrides(
    gen: dict[str, Any],
    *,
    resolution: Any = None,
    fmt: Any = None,
    quality: Any = None,
) -> dict[str, Any]:
    out = dict(gen)
    parsed = parse_resolution(resolution)
    if parsed:
        out["resolution"] = parsed
    if fmt:
        text = str(fmt).strip().casefold()
        if text == "jpg":
            text = "jpeg"
        if text not in gen_image.VALID_FORMATS:
            fail(f"format 应为 png / jpeg / webp，实际 {fmt!r}")
        out["format"] = text
    if quality:
        text = str(quality).strip().casefold()
        if text not in {"low", "medium", "high"}:
            fail(f"quality 应为 low / medium / high，实际 {quality!r}")
        out["quality"] = text
    out["resolution"] = str(out.get("resolution") or "1k")
    out["format"] = str(out.get("format") or "png")
    out["quality"] = str(out.get("quality") or "high")
    return out


def parse_max_px(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        fail(f"max_px 应为整数：{value!r}")
    if number <= 0:
        fail("max_px 必须大于 0")
    return number


def generation_from_template(path: Path | None) -> dict[str, Any]:
    out = {"resolution": "1k", "format": "png", "quality": "high"}
    if path is None:
        return out
    data = queue_pack.load_json(path) or {}
    gen = data.get("generation") if isinstance(data.get("generation"), dict) else {}
    for key in ("resolution", "format", "quality"):
        if gen.get(key):
            out[key] = gen[key]
    client = path.parent.parent / "要求.json"
    if client.is_file():
        meta = queue_pack.load_json(client) or {}
        listed = [str(x) for x in (meta.get("templates") or [])]
        if path.parent.name in listed:
            client_gen = meta.get("generation") if isinstance(meta.get("generation"), dict) else {}
            for key in ("resolution", "format", "quality"):
                if key not in (data.get("generation") or {}) and client_gen.get(key):
                    out[key] = client_gen[key]
            deliver = client_gen.get("deliver") if isinstance(client_gen, dict) else None
            if isinstance(deliver, dict) and "deliver" not in gen:
                out["deliver"] = deliver
    if isinstance(gen.get("deliver"), dict):
        out["deliver"] = gen["deliver"]
    return out


def deliver_from(
    gen: dict[str, Any],
    max_px: Any = None,
    max_bytes: Any = None,
    output_size: Any = None,
) -> dict[str, Any]:
    raw = gen.get("deliver") if isinstance(gen.get("deliver"), dict) else {}
    spec = None
    if output_size not in (None, ""):
        spec = parse_output_size(output_size)
    elif raw.get("width") and raw.get("height"):
        spec = parse_output_size(f"{raw['width']}x{raw['height']}")
    elif raw.get("output_size"):
        spec = parse_output_size(raw.get("output_size"))
    elif raw.get("ratio"):
        spec = parse_output_size(raw.get("ratio"))
    px = parse_max_px(max_px if max_px is not None else raw.get("max_px"))
    size = parse_bytes(max_bytes if max_bytes is not None else raw.get("max_bytes"))
    out: dict[str, Any] = {}
    if spec:
        out["ratio"] = spec["ratio"]
        if spec.get("width") and spec.get("height"):
            out["width"] = spec["width"]
            out["height"] = spec["height"]
            box = max(spec["width"], spec["height"])
            if px is not None and px != box:
                fail("--max-px 和 --output-size 冲突：精确画布用 --output-size，只限长边用 --max-px")
            out["max_px"] = box
        elif px is not None:
            out["max_px"] = px
    elif px is not None:
        out["max_px"] = px
    if size is not None:
        out["max_bytes"] = size
    return out


def prompt_dir(brief: dict[str, Any]) -> Path:
    return Path(brief["output_dir"]) / "_prompts"


def write_prompt_files(brief: dict[str, Any]) -> Path:
    folder = prompt_dir(brief)
    folder.mkdir(parents=True, exist_ok=True)
    text = str(brief.get("swap_prompt") or DEFAULT_PROMPT).strip() or DEFAULT_PROMPT
    path = folder / PROMPT_FILE
    path.write_text(text + "\n", encoding="utf-8")
    slots = brief.get("swap_slots") if isinstance(brief.get("swap_slots"), dict) else {}
    for slot, body in slots.items():
        extra = str(body or "").strip()
        if not extra:
            continue
        (folder / SLOT_PROMPT.format(slot=slot)).write_text(extra + "\n", encoding="utf-8")
    return path


def prompt_file_for(brief: dict[str, Any], slot: str) -> str:
    slots = brief.get("swap_slots") if isinstance(brief.get("swap_slots"), dict) else {}
    if str(slots.get(slot) or "").strip():
        return f"../{SLOT_PROMPT.format(slot=slot)}"
    return f"../{PROMPT_FILE}"


def fill_product(brief: dict[str, Any], name: str) -> dict[str, Any]:
    source = queue_pack.product_dir(brief, name)
    masters = Path(brief["masters_dir"])
    pack = brief.get("pack")
    if not isinstance(pack, list) or not pack:
        fail("批次.json 没有 pack，先 --init（lock=master 模板或 --masters）")
    if not source.is_dir():
        fail(f"源品文件夹不存在：{source}")
    jobs: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    gen = brief.get("generation") if isinstance(brief.get("generation"), dict) else {}
    gen = apply_generation_overrides(gen)
    for item in pack:
        if not isinstance(item, dict):
            continue
        slot = str(item.get("slot") or "")
        example = str(item.get("example") or "")
        pref = str(item.get("product_ref") or "front")
        master = masters / example
        if not slot:
            continue
        if not master.is_file():
            skipped.append({"slot": slot, "reason": f"母版不存在：{example}"})
            continue
        product = pick_product_image(source, pref)
        if product is None:
            skipped.append({"slot": slot, "reason": f"没有可用的产品图，跳过"})
            continue
        jobs.append({
            "slot": slot,
            "prompt_file": prompt_file_for(brief, slot),
            "size": str(item.get("ratio") or "1:1"),
            "resolution": gen["resolution"],
            "format": gen["format"],
            "quality": gen["quality"],
            "image": [str(master.resolve()), str(product.resolve())],
        })
    if not jobs:
        fail(f"{name} 没有可出的槽位（缺母版或对不上产品角度）")
    dest = prompt_dir(brief) / name
    dest.mkdir(parents=True, exist_ok=True)
    write_prompt_files(brief)
    sizes = [str(job["size"]) for job in jobs]
    defaults: dict[str, Any] = {
        "resolution": gen["resolution"],
        "quality": gen["quality"],
        "format": gen["format"],
    }
    if len(set(sizes)) == 1:
        defaults["size"] = sizes[0]
    payload = {
        "output_dir": f"../../{name}",
        "defaults": defaults,
        "jobs": jobs,
    }
    (dest / "jobs.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (dest / "skipped.json").write_text(
        json.dumps({"skipped": skipped}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"name": name, "jobs": len(jobs), "skipped": skipped}


def product_names(brief: dict[str, Any]) -> list[str]:
    rows = queue_pack.scan(brief)
    names = [row["name"] for row in rows if row["status"] != "skip"]
    only = [str(x) for x in (brief.get("only") or []) if str(x).strip()]
    if only:
        return [name for name in names if name in only]
    return names


def fill_products(brief: dict[str, Any], names: list[str]) -> list[dict[str, Any]]:
    reports = [fill_product(brief, name) for name in names]
    return reports


def format_fill_report(reports: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in reports:
        lines.append(f"{item['name']}：写入 {item['jobs']} 槽")
        for skip in item.get("skipped") or []:
            lines.append(f"  跳过 {skip['slot']}：{skip['reason']}")
    return "\n".join(lines)


def _pil():
    try:
        from PIL import Image
    except ImportError:
        fail("交付压图需要 Pillow：pip install pillow")
    return Image


def _save_under_bytes(image: Any, path: Path, max_bytes: int | None, fmt: str) -> Path:
    fmt = fmt.lower()
    if fmt == "jpg":
        fmt = "jpeg"
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
            return _save_under_bytes(rgb, jpeg_path, max_bytes, "jpeg")
        quality -= 8
    if max_bytes is not None and path.stat().st_size > max_bytes and fmt == "jpeg":
        fail(f"压到 quality=40 仍超过 {max_bytes} 字节：{path}")
    return path


def deliver_image(
    path: Path,
    max_px: int | None,
    max_bytes: int | None,
    *,
    width: int | None = None,
    height: int | None = None,
    ratio: str | None = None,
) -> Path:
    Image = _pil()
    with Image.open(path) as raw:
        image = raw.copy()
    resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
    if width and height:
        want = ratio or ratio_from_wh(int(width), int(height))
        have = ratio_from_wh(image.width, image.height)
        if want != have:
            fail(
                f"{path.name} 是 {have}（{image.width}×{image.height}），"
                f"交付要 {width}×{height}（{want}）。不能压变形。"
                f"按 {have} 生图，或换 {want} 母版。"
            )
        if image.width > width or image.height > height:
            image.thumbnail((int(width), int(height)), resample)
    elif max_px and (image.width > max_px or image.height > max_px):
        image.thumbnail((max_px, max_px), resample)
    fmt = path.suffix.lower().lstrip(".") or "png"
    out = _save_under_bytes(image, path, max_bytes, fmt)
    if out != path and path.is_file():
        path.unlink()
    return out


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def deliver_brief(brief: dict[str, Any], names: list[str] | None = None) -> list[str]:
    spec = brief.get("deliver") if isinstance(brief.get("deliver"), dict) else {}
    max_px = parse_max_px(spec.get("max_px"))
    max_bytes = parse_bytes(spec.get("max_bytes"))
    width = _int_or_none(spec.get("width"))
    height = _int_or_none(spec.get("height"))
    ratio = str(spec["ratio"]) if spec.get("ratio") else None
    if max_px is None and max_bytes is None and not (width and height):
        fail(
            "批次没有交付尺寸。init 时加 --output-size 或 --max-px / --max-bytes，"
            "或出图后再改批次.json"
        )
    output = Path(brief["output_dir"])
    rows = queue_pack.scan(brief)
    done = [row["name"] for row in rows if row["status"] == "done"]
    if names:
        wanted = set(names)
        done = [name for name in done if name in wanted]
    changed: list[str] = []
    for name in done:
        folder = output / name
        if not folder.is_dir():
            continue
        for image in queue_pack.slot_images(folder):
            result = deliver_image(
                image,
                max_px,
                max_bytes,
                width=width,
                height=height,
                ratio=ratio,
            )
            changed.append(str(result))
    return changed
