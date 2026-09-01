#!/usr/bin/env python3
"""多品并发队列：状态看磁盘，主会话只调度。

2 个及以上品文件夹时用这个，不要在一条对话里按品串行。

  python scripts/queue_pack.py --init --source VE男包系列 --template templates/BeautyU/01-箱包单品报价模板/01-箱包单品报价模板.json
  python scripts/queue_pack.py --queue VE男包生成/_prompts/批次.json
  python scripts/queue_pack.py --queue ... --next
  python scripts/queue_pack.py --queue ... --run --skip-existing   # 生图单独走，默认并发 32

快跑（lock=master：Agent 看图选白图做原型，点头后脚本填 jobs，不派品工人）：

  python scripts/queue_pack.py --init --fast --source VE男包系列 --masters 样板套图 --category 双肩包
  python scripts/queue_pack.py --queue ... --pilot V26026 --run
  python scripts/queue_pack.py --queue ... --blast --run --skip-existing
  python scripts/queue_pack.py --queue ... --deliver
  # 默认同级「生成」；档位/画布由调用方填：--resolution --output-size / --max-px --max-bytes
"""
from __future__ import annotations

import argparse
import json
import re
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
REFERENCES = SKILL_ROOT / "references"
BRIEF_NAME = "批次.json"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
SKIP_DIR_NAMES = {"_prompts"}
SLOT_STEM_RE = re.compile(r"^h\d+$", re.I)
STATUS_ORDER = ("prompt", "gen", "done", "skip", "empty")
DEFAULT_GEN_CONCURRENCY = 32
MAX_GEN_CONCURRENCY = 64
STATUS_LABEL = {
    "prompt": "待写 Prompt",
    "gen": "待出图",
    "done": "完成",
    "skip": "跳过",
    "empty": "空文件夹",
}


def fail(message: str) -> None:
    print(f"错误：{message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def as_path(value: Any) -> Path | None:
    if not value:
        return None
    return Path(str(value))


def resolve_existing(path: Path, base: Path) -> Path:
    if path.is_absolute():
        return path
    for candidate in (base / path, Path.cwd() / path, path):
        if candidate.exists():
            return candidate.resolve()
    return (base / path).resolve()


def resolve_brief_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_dir():
        path = path / BRIEF_NAME
    return path.resolve()


def resolve_template(raw: str | None, base: Path) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    candidates = [
        path if path.is_absolute() else None,
        base / path,
        REFERENCES / path,
        REFERENCES / "templates" / path,
        SKILL_ROOT / path,
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate.resolve()
    return None


def template_rel(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.relative_to(REFERENCES).as_posix()
    except ValueError:
        return str(path)


def list_product_dirs(source_dir: Path) -> list[Path]:
    if not source_dir.is_dir():
        fail(f"源目录不存在：{source_dir}")
    products: list[Path] = []
    for entry in sorted(source_dir.iterdir(), key=lambda p: p.name):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in SKIP_DIR_NAMES:
            continue
        if product_images(entry):
            products.append(entry)
    return products


def product_images(folder: Path, *, skip_slots: bool = False) -> list[Path]:
    if not folder.is_dir():
        return []
    files: list[Path] = []
    for path in folder.iterdir():
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if skip_slots and SLOT_STEM_RE.match(path.stem):
            continue
        files.append(path)
    return sorted(files)


def ref_images(folder: Path) -> list[Path]:
    return product_images(folder, skip_slots=True)


def slot_images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        path for path in folder.iterdir()
        if path.is_file()
        and path.suffix.lower() in IMAGE_SUFFIXES
        and SLOT_STEM_RE.match(path.stem)
    )


def product_dir(brief: dict[str, Any], name: str) -> Path:
    dest = Path(brief["output_dir"]) / name
    if ref_images(dest):
        return dest
    return Path(brief["source_dir"]) / name


def product_names_of(brief: dict[str, Any]) -> list[str]:
    listed = [str(name) for name in (brief.get("products") or []) if str(name).strip()]
    if listed:
        return listed
    return [path.name for path in list_product_dirs(Path(brief["source_dir"]))]


def slots_from_jobs(jobs_path: Path) -> list[str]:
    data = load_json(jobs_path)
    if not data:
        return []
    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        return []
    slots: list[str] = []
    for item in jobs:
        if isinstance(item, dict) and item.get("slot"):
            slots.append(str(item["slot"]))
    return slots


def slot_done(output_dir: Path, slot: str, fmt: str = "png") -> bool:
    return gen_image._existing_output(output_dir, slot.lower(), fmt) is not None


def classify_product(name: str, brief: dict[str, Any]) -> str:
    only = [str(x) for x in (brief.get("only") or []) if str(x).strip()]
    skip = [str(x) for x in (brief.get("skip") or []) if str(x).strip()]
    if name in skip or (only and name not in only):
        return "skip"
    source_dir = Path(brief["source_dir"])
    output_dir = Path(brief["output_dir"])
    src = product_dir(brief, name)
    if not ref_images(src) and not product_images(source_dir / name):
        return "empty"
    jobs_path = output_dir / "_prompts" / name / "jobs.json"
    if not jobs_path.is_file():
        return "prompt"
    slots = slots_from_jobs(jobs_path)
    if not slots:
        return "prompt"
    dest = output_dir / name
    if all(slot_done(dest, slot) for slot in slots):
        return "done"
    return "gen"


def load_brief(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if not data:
        fail(f"无法读取批次文件：{path}")
    source = as_path(data.get("source_dir"))
    output = as_path(data.get("output_dir"))
    if source is None or output is None:
        fail("批次.json 必须有 source_dir 和 output_dir")
    base = path.parent
    data["source_dir"] = str(resolve_existing(source, base))
    data["output_dir"] = str(resolve_existing(output, base))
    workers = data.get("product_workers", 3)
    try:
        data["product_workers"] = max(1, min(8, int(workers)))
    except (TypeError, ValueError):
        data["product_workers"] = 3
    data["gen_concurrency"] = clamp_gen_concurrency(data.get("gen_concurrency"))
    return data


def clamp_gen_concurrency(value: Any) -> int:
    try:
        return max(1, min(MAX_GEN_CONCURRENCY, int(value)))
    except (TypeError, ValueError):
        return DEFAULT_GEN_CONCURRENCY


def resolve_gen_concurrency(args: argparse.Namespace, brief: dict[str, Any] | None = None) -> int:
    if getattr(args, "concurrency", None) is not None:
        return clamp_gen_concurrency(args.concurrency)
    if brief is not None:
        return clamp_gen_concurrency(brief.get("gen_concurrency"))
    return DEFAULT_GEN_CONCURRENCY


def scan(brief: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    named: set[str] = set()
    for name in product_names_of(brief):
        status = classify_product(name, brief)
        rows.append({"name": name, "status": status})
        named.add(name)
    only = [str(x) for x in (brief.get("only") or []) if str(x).strip()]
    for name in only:
        if name not in named:
            rows.append({"name": name, "status": "empty"})
    return rows


def counts(rows: list[dict[str, str]]) -> dict[str, int]:
    tally = {key: 0 for key in STATUS_ORDER}
    for row in rows:
        tally[row["status"]] = tally.get(row["status"], 0) + 1
    return tally


def names_with(rows: list[dict[str, str]], *statuses: str) -> list[str]:
    result: list[str] = []
    for status in statuses:
        result.extend(row["name"] for row in rows if row["status"] == status)
    return result


def format_status(brief_path: Path, brief: dict[str, Any], rows: list[dict[str, str]]) -> str:
    tally = counts(rows)
    lines = [
        f"批次：{brief_path}",
        f"源：{brief['source_dir']}",
        f"成图：{brief['output_dir']}",
        f"模板：{brief.get('template') or '（未写）'}  lock={brief.get('lock') or 'rules'}"
        + (f"  run={brief.get('run')}" if brief.get("run") == "fast" else ""),
        (
            "快跑：Agent 看图选白图；点头后脚本填 jobs，不要派品工人"
            if brief.get("run") == "fast"
            else f"品工人同时最多 {brief['product_workers']} 路（写 Prompt）"
        ),
        f"生图并发 {brief['gen_concurrency']}（--run 单独走）",
        "",
    ]
    if brief.get("run") == "fast":
        if brief.get("category"):
            lines.insert(-1, f"品类：{brief['category']}")
        deliver = brief.get("deliver") if isinstance(brief.get("deliver"), dict) else {}
        bits = []
        if deliver.get("width") and deliver.get("height"):
            label = f"{deliver['width']}×{deliver['height']}"
            if deliver.get("ratio"):
                label += f"（{deliver['ratio']}）"
            bits.append(label)
        elif deliver.get("max_px"):
            bits.append(f"长边≤{deliver['max_px']}（保持比例）")
        if deliver.get("max_bytes"):
            bits.append(f"≤{deliver['max_bytes']}B")
        if bits:
            lines.insert(-1, "交付：" + "，".join(bits))
        gen = brief.get("generation") if isinstance(brief.get("generation"), dict) else {}
        if gen.get("resolution") or gen.get("format"):
            lines.insert(
                -1,
                "生图："
                + "/".join(
                    str(gen.get(k) or "")
                    for k in ("resolution", "format", "quality")
                    if gen.get(k)
                ),
            )
        every = inspect_every_of(brief)
        if every:
            lines.insert(-1, f"抽检：每 {every} 个品停一次")
        else:
            lines.insert(-1, "抽检：关（铺完再问）")
    for key in STATUS_ORDER:
        lines.append(f"{STATUS_LABEL[key]:8} {tally[key]}")
    notes = str(brief.get("notes") or "").strip()
    if notes:
        lines.extend(["", f"notes：{notes}"])
    for status in ("prompt", "gen"):
        items = names_with(rows, status)
        if not items:
            continue
        lines.extend(["", STATUS_LABEL[status] + "："])
        lines.extend(f"  {name}" for name in items)
    return "\n".join(lines)


def next_products(rows: list[dict[str, str]], limit: int, *, retry: bool) -> list[str]:
    statuses = ("prompt", "gen") if retry else ("prompt",)
    return names_with(rows, *statuses)[: max(0, limit)]


def format_worker_brief(
    brief_path: Path,
    brief: dict[str, Any],
    names: list[str],
    *,
    retry: bool,
) -> str:
    output = Path(brief["output_dir"])
    source = Path(brief["source_dir"])
    notes = str(brief.get("notes") or "").strip() or "（无）"
    style_lock = str(brief.get("style_lock") or "").strip()
    lock = str(brief.get("lock") or "rules")
    template = str(brief.get("template") or "").strip() or "（批次未写模板，用 SKILL 已命中的那份）"
    lines = [
        f"下一波 {len(names)} 个品工人（同时派，不要串行）：",
        *[f"  - {name}" for name in names],
        "",
        "每个子代理只做名单里的一个品。派发时把任务里的 {品名} 换成上面的那一个。",
        "把下面整段放进子代理任务：",
        "",
        "使用 dsimage。你只做这一个品，做完即停，不要接下一个。",
        f"批次文件：{brief_path}",
        f"规矩只认这份批次.json（notes：{notes}）。不要问里面已经有的要求。",
        f"模板：{template}  lock={lock}",
        f"甲方源（只读）：{source}",
        f"Prompt / jobs.json → {output / '_prompts' / '{品名}'}/",
        f"成图 → {output / '{品名}'}/  套图 h1.png… + 已迁白图",
        "参考图用该品成图夹里迁来的产品图。源图文件名按 SKILL「源图文件名」对槽。不要改甲方源夹。",
    ]
    if style_lock:
        lines.append("Campaign Style Lock 用批次.json 的 style_lock 原文，不要改写。")
    lines.extend([
        "出图通道：有生图 API → 只写 Prompt 和 jobs.json，不要调用 gen_image（调度会 queue_pack --run）。",
        "无 API、走宿主生图 → 写完 Prompt 后按 SKILL 给本品派槽位子代理，同时最多 2 路。",
        "禁止读取其他品文件夹，禁止改批次.json，禁止把 txt 写进成图目录。",
        "返回：品名、写入的槽位、失败原因。不要汇报其他品。",
    ])
    if retry:
        lines.append("本波含待出图的品：jobs.json 已在的不要重写 Prompt，只补缺的槽位。")
    return "\n".join(lines)


def read_style_lock(template_path: Path | None) -> tuple[str, str]:
    if template_path is None:
        return "rules", ""
    data = load_json(template_path) or {}
    lock = str(data.get("lock") or data.get("template_type") or "rules")
    if lock in {"replace", "master"}:
        return "master", ""
    if lock in {"style"}:
        lock = "rules"
    return lock, str(data.get("style_lock") or "")


def write_brief(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def init_brief(args: argparse.Namespace) -> Path:
    import swap_fast

    source = Path(args.source).resolve()
    if not source.is_dir():
        fail(f"源目录不存在：{source}")
    output = Path(args.output).resolve() if args.output else swap_fast.default_output_dir(source)
    template_path = resolve_template(args.template, Path.cwd())
    if args.template and template_path is None:
        fail(f"找不到模板：{args.template}")
    lock, style_lock = read_style_lock(template_path)
    if args.lock:
        lock = args.lock
    only = [x for x in (args.only or []) if x.strip()]
    skip = [x for x in (args.skip or []) if x.strip()]
    expanded = swap_fast.expand_client_source(source)
    only, missing_only = swap_fast.resolve_product_names(expanded, only)
    if missing_only:
        fail("only 里没有这些商品：" + "、".join(missing_only))
    skip, missing_skip = swap_fast.resolve_product_names(expanded, skip)
    if missing_skip:
        fail("skip 里没有这些商品：" + "、".join(missing_skip))
    products = list_product_dirs(source)
    if not only and len(products) < 2 and len(expanded) < 2 and not skip and not getattr(args, "fast", False):
        print("提示：源目录下品文件夹不足 2 个。批量并发按「2 个及以上」才走这条路。", file=sys.stderr)
    swap_fast.materialize_products(output, expanded, only=only, skip=set(skip))
    payload = {
        "source_dir": str(source),
        "output_dir": str(output),
        "template": template_rel(template_path),
        "lock": lock,
        "only": only,
        "skip": skip,
        "products": [item["sku"] for item in expanded],
        "product_workers": max(1, min(8, args.workers)),
        "gen_concurrency": resolve_gen_concurrency(args),
        "notes": args.notes or "",
        "style_lock": style_lock,
    }
    if getattr(args, "fast", False):
        payload.update(
            build_fast_payload(
                args, source, template_path, lock,
                expanded=expanded, only=only, skip=skip,
            )
        )
    brief_path = output / "_prompts" / BRIEF_NAME
    write_brief(brief_path, payload)
    output.mkdir(parents=True, exist_ok=True)
    return brief_path


def build_fast_payload(
    args: argparse.Namespace,
    source: Path,
    template_path: Path | None,
    lock: str,
    *,
    expanded: list[dict[str, Any]],
    only: list[str],
    skip: list[str],
) -> dict[str, Any]:
    import swap_fast

    masters_raw = getattr(args, "masters", None)
    if not masters_raw and template_path is None:
        fail("快跑需要 --template（lock=master）或 --masters 母版文件夹")
    if lock == "master" and template_path is not None:
        pack = swap_fast.pack_from_template(template_path)
        masters = Path(masters_raw).resolve() if masters_raw else template_path.parent.resolve()
        if not masters.is_dir():
            fail(f"母版文件夹不存在：{masters}")
        missing = [str(item.get("example")) for item in pack if not (masters / str(item.get("example"))).is_file()]
        if missing:
            fail("母版文件夹缺这些文件：" + "、".join(missing))
        lock = "master"
    elif masters_raw:
        masters = Path(masters_raw).resolve()
        if not masters.is_dir():
            fail(f"母版文件夹不存在：{masters}")
        pack = swap_fast.infer_pack(masters)
        lock = "master"
    else:
        fail("这份模板是按规则画的。快跑要母版图：换成 lock=master 的模板，或加 --masters")
    gen = swap_fast.apply_generation_overrides(
        swap_fast.generation_from_template(template_path),
        resolution=getattr(args, "resolution", None),
        fmt=getattr(args, "gen_format", None),
        quality=getattr(args, "quality", None),
    )
    deliver = swap_fast.deliver_from(
        gen,
        getattr(args, "max_px", None),
        getattr(args, "max_bytes", None),
        output_size=getattr(args, "output_size", None),
    )
    if deliver.get("ratio"):
        label = getattr(args, "output_size", None) or (
            f"{deliver['width']}x{deliver['height']}"
            if deliver.get("width") and deliver.get("height")
            else deliver["ratio"]
        )
        swap_fast.require_pack_ratio(pack, deliver["ratio"], str(label))
    prompt = str(getattr(args, "swap_prompt", None) or swap_fast.DEFAULT_PROMPT).strip()
    skip_set = set(skip)
    named = [str(item["sku"]) for item in expanded if item["sku"] not in skip_set]
    if only:
        named = [name for name in named if name in only]
    pilot = str(getattr(args, "pilot", None) or "").strip()
    if pilot:
        resolved, missing = swap_fast.resolve_product_names(expanded, [pilot])
        if missing:
            fail(f"试跑品不在源目录：{pilot}")
        pilot = resolved[0]
    elif named:
        pilot = named[0]
    if pilot and named and pilot not in named:
        fail(f"试跑品不在源目录：{pilot}")
    inspect_every = swap_fast.parse_inspect_every(getattr(args, "inspect_every", None))
    payload: dict[str, Any] = {
        "run": "fast",
        "lock": lock,
        "style_lock": "",
        "masters_dir": str(masters),
        "pack": pack,
        "swap_prompt": prompt,
        "swap_slots": {},
        "prompt_locked": False,
        "pilot": pilot,
        "category": str(getattr(args, "category", None) or "").strip(),
        "generation": {k: gen[k] for k in ("resolution", "format", "quality")},
        "inspect_every": inspect_every,
    }
    if deliver:
        payload["deliver"] = deliver
    return payload


def is_fast(brief: dict[str, Any]) -> bool:
    return str(brief.get("run") or "") == "fast"


def format_fast_next(brief_path: Path, brief: dict[str, Any], rows: list[dict[str, str]]) -> str:
    q = f"python scripts/queue_pack.py --queue \"{brief_path}\""
    prompt = str(brief.get("swap_prompt") or "").strip()
    first_line = prompt.splitlines()[0] if prompt else ""
    lines = [
        "快跑。不要派品工人写 Prompt。",
        f"提示词：{first_line}",
        f"试跑品：{brief.get('pilot') or '（未写）'}",
        f"提示词已锁：{'是' if brief.get('prompt_locked') else '否'}",
        "",
    ]
    if names_with(rows, "prompt") and not brief.get("prompt_locked"):
        pilot = str(brief.get("pilot") or names_with(rows, "prompt")[0])
        lines.append("还没试跑。先出一套：")
        lines.append(f"{q} --pilot {pilot} --run")
    elif names_with(rows, "prompt"):
        every = inspect_every_of(brief)
        if every:
            lines.append(f"提示词已锁。抽检每 {every} 个品停一次，先填 jobs 再按波出图：")
            lines.append(f"{q} --blast")
            lines.append(f"{q} --run --skip-existing")
        else:
            lines.append("提示词已锁，铺开剩余型号：")
            lines.append(f"{q} --blast --run --skip-existing")
    elif names_with(rows, "gen"):
        every = inspect_every_of(brief)
        pending = names_with(rows, "gen")
        wave = pending[:every] if every else pending
        lines.append("jobs 已齐，出图：")
        if every:
            lines.append(f"下一波 {len(wave)} 个（每 {every} 个停）：" + "、".join(wave))
        lines.append(f"{q} --run --skip-existing")
    elif names_with(rows, "done") and not names_with(rows, "prompt", "gen"):
        lines.append("全部完成。有交付尺寸就 --deliver；然后问用户要不要检查成图。")
        if isinstance(brief.get("deliver"), dict) and brief.get("deliver"):
            lines.append(f"{q} --deliver")
    else:
        lines.append("这一波没有可做的品。")
    return "\n".join(lines)


def apply_set_prompt(brief: dict[str, Any], text: str, slot: str | None = None) -> None:
    import swap_fast

    body = text.strip()
    if not body:
        fail("提示词不能为空")
    if slot:
        slots = dict(brief.get("swap_slots") or {})
        slots[slot] = body
        brief["swap_slots"] = slots
    else:
        brief["swap_prompt"] = body
    brief["prompt_locked"] = False
    swap_fast.write_prompt_files(brief)


def run_fast_fill(brief: dict[str, Any], names: list[str]) -> str:
    import swap_fast

    if not names:
        fail("没有要填 jobs 的品")
    reports = swap_fast.fill_products(brief, names)
    return swap_fast.format_fill_report(reports)


def inspect_every_of(brief: dict[str, Any]) -> int:
    import swap_fast

    return swap_fast.parse_inspect_every(brief.get("inspect_every"))


def wave_names(brief: dict[str, Any], rows: list[dict[str, str]],
               args: argparse.Namespace) -> list[str]:
    names = names_with(rows, "gen")
    if getattr(args, "product", None):
        wanted = set(args.product)
        names = [name for name in names if name in wanted]
        extra = [name for name in args.product if name not in names]
        if extra:
            print("这些品现在不是待出图：" + "、".join(extra), file=sys.stderr)
        return names
    every = inspect_every_of(brief)
    if every:
        return names[:every]
    return names


def gen_namespace(args: argparse.Namespace, brief: dict[str, Any] | None = None) -> argparse.Namespace:
    gen = brief.get("generation") if isinstance((brief or {}).get("generation"), dict) else {}
    return argparse.Namespace(
        prompt=None,
        prompt_file=None,
        batch=None,
        concurrency=resolve_gen_concurrency(args),
        skip_existing=args.skip_existing,
        output_dir="generated-images",
        env_file=args.env_file,
        mode=args.mode,
        size="1:1",
        resolution=str(gen.get("resolution") or "1k"),
        quality=gen.get("quality") or "high",
        n=1,
        image=None,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
        format=str(gen.get("format") or "png"),
    )


def collect_run_jobs(brief: dict[str, Any], rows: list[dict[str, str]],
                     args: argparse.Namespace) -> list[dict[str, Any]]:
    output = Path(brief["output_dir"])
    names = wave_names(brief, rows, args)
    jobs: list[dict[str, Any]] = []
    dummy = gen_namespace(args, brief)
    for name in names:
        jobs_path = output / "_prompts" / name / "jobs.json"
        try:
            dest, loaded = gen_image.load_batch(jobs_path, dummy)
        except gen_image.GenError as exc:
            print(f"跳过 {name}：{exc}", file=sys.stderr)
            continue
        for job in loaded:
            slot = job["slot"]
            job["output_dir"] = dest
            job["job_id"] = f"{name}/{slot}"
            job["label"] = f"{name}/{slot}"
            jobs.append(job)
    return jobs


def run_queue(brief: dict[str, Any], rows: list[dict[str, str]],
              args: argparse.Namespace) -> None:
    names = wave_names(brief, rows, args)
    jobs = collect_run_jobs(brief, rows, args)
    if not jobs:
        print("没有待出图的槽位。快跑用 --pilot / --blast 填 jobs；普通批次用 --next 派工人。")
        return
    every = inspect_every_of(brief)
    if every and names and not getattr(args, "product", None):
        leftover = max(0, len(names_with(rows, "gen")) - len(names))
        print(f"这一波出 {len(names)} 个品（每 {every} 个停）：" + "、".join(names)
              + (f"；之后还剩 {leftover} 个" if leftover else ""))
    env_file = Path(args.env_file) if args.env_file else gen_image.find_default_env_file()
    gen_image.load_env_file(env_file)
    _provider, base_url, model, api_key = gen_image.resolve_runtime()
    mode = gen_image.detect_mode(_provider, base_url, args.mode)
    results = gen_image.run_job_pool(
        jobs,
        concurrency=resolve_gen_concurrency(args, brief),
        skip_existing=args.skip_existing,
        base_url=base_url,
        api_key=api_key,
        model=model,
        mode=mode,
        log_label="queue",
    )
    failed = gen_image.print_pool_results(
        jobs, results, extra=f"成图根：{brief['output_dir']}"
    )
    if failed:
        raise SystemExit(1)
    if every and names and not getattr(args, "product", None):
        leftover = names_with(scan(brief), "gen")
        print()
        print("这一波已出：" + "、".join(names))
        if leftover:
            print(
                f"请检查这 {len(names)} 套。没问题再 --run --skip-existing 出下一波"
                f"（还剩 {len(leftover)} 个）。不对就改提示词，只重跑有问题的品。"
            )
        else:
            print("没有待出图的了。有交付尺寸就 --deliver。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="多品并发队列。状态看磁盘；普通批次 --next 派品工人；快跑 --pilot / --blast 填 jobs；--run 出图。"
    )
    parser.add_argument("--init", action="store_true", help="扫描源目录，写入成图根/_prompts/批次.json")
    parser.add_argument("--source", help="--init 用的源大文件夹")
    parser.add_argument("--output", help="成图根目录；默认把「系列」换成「生成」，与源同级")
    parser.add_argument("--template", help="模板 JSON 路径（相对 references/ 或绝对路径）")
    parser.add_argument("--lock", choices=("rules", "master"), help="覆盖模板里的 lock")
    parser.add_argument("--fast", action="store_true", help="快跑：Agent 选白图做原型；点头后脚本填 jobs。需要母版")
    parser.add_argument("--masters", help="快跑母版文件夹（h1.png…）。有 lock=master 模板可不写")
    parser.add_argument("--category", help="快跑品类（如 双肩包），只记录在批次里")
    parser.add_argument("--max-px", dest="max_px", type=int, help="交付长边像素上限；保持比例，不变形")
    parser.add_argument("--output-size", dest="output_size", help="交付画布，宽x高；按这个比例生图再缩小，对不上就拒绝，不变形压")
    parser.add_argument("--max-bytes", dest="max_bytes", help="交付体积上限，例如 2MB")
    parser.add_argument("--resolution", help="生图档 1k / 2k / 4k；不要填 800 或 1024x1024")
    parser.add_argument("--format", dest="gen_format", help="生图格式 png / jpeg / webp")
    parser.add_argument("--quality", help="生图质量 low / medium / high")
    parser.add_argument("--inspect-every", dest="inspect_every", type=int, default=None,
                        help="快跑：每 N 个品停下来检查；默认 0 不停")
    parser.add_argument("--swap-prompt", dest="swap_prompt", help="快跑提示词；不写用脚本默认句")
    parser.add_argument("--only", action="append", default=[], help="只做这些品文件夹名，可重复")
    parser.add_argument("--skip", action="append", default=[], help="跳过这些品文件夹名，可重复")
    parser.add_argument("--workers", type=int, default=3, help="品工人同时几路，默认 3，最大 8")
    parser.add_argument("--notes", default="", help="写进批次.json 的口头要求")
    parser.add_argument("--queue", help="批次.json 路径，或它所在的 _prompts/ 目录")
    parser.add_argument("--next", action="store_true", help="打印下一波待写 Prompt 的品 + 工人任务原文")
    parser.add_argument("-n", "--count", type=int, help="--next 派几个；默认用批次里的 product_workers")
    parser.add_argument("--retry", action="store_true", help="--next 时也派待出图的品（宿主补图 / 失败重做）")
    parser.add_argument("--pilot", metavar="NAME", help="快跑：试跑这一个品（init 时记下；queue 时填 jobs）")
    parser.add_argument("--blast", action="store_true", help="快跑：按已锁提示词给剩余型号填 jobs")
    parser.add_argument("--set-prompt", dest="set_prompt", help="快跑：改共用提示词并解锁，需再试跑")
    parser.add_argument("--set-slot-prompt", nargs=2, metavar=("SLOT", "TEXT"), help="快跑：覆盖某一槽提示词")
    parser.add_argument("--deliver", action="store_true", help="快跑：按批次 deliver 压已完成成图")
    parser.add_argument("--run", action="store_true", help="把所有待出图槽位丢进全局并发池（有 API 时用）")
    parser.add_argument("--product", action="append", default=[], help="--run 只出这些品")
    parser.add_argument("--concurrency", type=int, default=None, help="生图全局槽位并发；默认用批次.json 的 gen_concurrency（32），最大 64；429 自动减半")
    parser.add_argument("--skip-existing", action="store_true", help="--run 跳过已有成图的槽位")
    parser.add_argument("--env-file", help="生图 .env；不指定则按 gen_image 规则查找")
    parser.add_argument("--mode", choices=gen_image.API_MODES, help="覆盖 API 模式")
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--timeout", type=int)
    args = parser.parse_args()
    if args.init and not args.source:
        parser.error("--init 需要 --source")
    if args.fast and not args.init:
        parser.error("--fast 只和 --init 一起用（之后用 --pilot / --blast）")
    if not args.init and not args.queue:
        parser.error("请提供 --queue 批次.json，或用 --init --source 新建")
    return args


def apply_fast_overrides(brief: dict[str, Any], args: argparse.Namespace) -> list[str]:
    import swap_fast

    notes: list[str] = []
    if getattr(args, "inspect_every", None) is not None:
        brief["inspect_every"] = swap_fast.parse_inspect_every(args.inspect_every)
        every = brief["inspect_every"]
        notes.append("抽检已关（一口气出完）" if every == 0 else f"抽检：每 {every} 个品停一次")
    res = getattr(args, "resolution", None)
    fmt = getattr(args, "gen_format", None)
    quality = getattr(args, "quality", None)
    if res or fmt or quality:
        gen = brief.get("generation") if isinstance(brief.get("generation"), dict) else {}
        brief["generation"] = swap_fast.apply_generation_overrides(
            gen, resolution=res, fmt=fmt, quality=quality
        )
        notes.append(
            "生图档："
            + "/".join(str(brief["generation"].get(k)) for k in ("resolution", "format", "quality"))
        )
    out_size = getattr(args, "output_size", None)
    max_px = getattr(args, "max_px", None)
    max_bytes = getattr(args, "max_bytes", None)
    if out_size or max_px is not None or max_bytes:
        gen = brief.get("generation") if isinstance(brief.get("generation"), dict) else {}
        merged = dict(gen)
        if isinstance(brief.get("deliver"), dict):
            merged["deliver"] = brief["deliver"]
        deliver = swap_fast.deliver_from(merged, max_px, max_bytes, output_size=out_size)
        if deliver.get("ratio"):
            label = out_size or (
                f"{deliver['width']}x{deliver['height']}"
                if deliver.get("width") and deliver.get("height")
                else deliver["ratio"]
            )
            swap_fast.require_pack_ratio(brief.get("pack") or [], deliver["ratio"], str(label))
        brief["deliver"] = deliver
        if deliver.get("width") and deliver.get("height"):
            notes.append(f"交付：{deliver['width']}×{deliver['height']}（{deliver.get('ratio')}）")
        elif deliver.get("max_px"):
            notes.append(f"交付长边≤{deliver['max_px']}（保持比例）")
    return notes


def persist_brief(brief_path: Path, brief: dict[str, Any]) -> None:
    keys = (
        "source_dir", "output_dir", "template", "lock", "only", "skip",
        "product_workers", "gen_concurrency", "notes", "style_lock",
        "run", "masters_dir", "pack", "swap_prompt", "swap_slots",
        "prompt_locked", "pilot", "category", "generation", "deliver",
        "inspect_every", "products",
    )
    payload = {key: brief[key] for key in keys if key in brief}
    write_brief(brief_path, payload)


def main() -> None:
    args = parse_args()
    if args.init:
        brief_path = init_brief(args)
        print(f"已写入 {brief_path}")
    else:
        brief_path = resolve_brief_path(args.queue)
        if not brief_path.is_file():
            fail(f"找不到批次文件：{brief_path}")

    brief = load_brief(brief_path)

    if is_fast(brief) and not args.init:
        notes = apply_fast_overrides(brief, args)
        if notes:
            persist_brief(brief_path, brief)
            for line in notes:
                print(line)
            if getattr(args, "resolution", None) or getattr(args, "gen_format", None) or getattr(args, "quality", None):
                import swap_fast

                filled = [
                    name for name in swap_fast.product_names(brief)
                    if (Path(brief["output_dir"]) / "_prompts" / name / "jobs.json").is_file()
                ]
                if filled:
                    print("分辨率/格式已改，重写已有 jobs：")
                    print(run_fast_fill(brief, filled))

    if args.set_prompt or args.set_slot_prompt:
        if not is_fast(brief):
            fail("--set-prompt 只用于快跑批次")
        if args.set_prompt:
            apply_set_prompt(brief, args.set_prompt)
        if args.set_slot_prompt:
            apply_set_prompt(brief, args.set_slot_prompt[1], args.set_slot_prompt[0])
        persist_brief(brief_path, brief)
        print("已更新提示词。改过之后先 --pilot 再铺开。")

    if args.pilot and is_fast(brief):
        brief["pilot"] = args.pilot
        print(run_fast_fill(brief, [args.pilot]))
        persist_brief(brief_path, brief)
        if not args.blast:
            args.product = [args.pilot]
    elif args.pilot and not is_fast(brief):
        fail("--pilot 只用于快跑批次")

    if args.blast:
        if not is_fast(brief):
            fail("--blast 只用于快跑批次")
        import swap_fast

        rows_now = scan(brief)
        if not names_with(rows_now, "gen", "done"):
            fail("还没有试跑一套。先 --pilot 出一套，用户点头后再 --blast")
        names = swap_fast.product_names(brief)
        print(run_fast_fill(brief, names))
        brief["prompt_locked"] = True
        persist_brief(brief_path, brief)

    if args.deliver:
        if not is_fast(brief):
            fail("--deliver 只用于快跑批次")
        import swap_fast

        changed = swap_fast.deliver_brief(brief, args.product or None)
        if not changed:
            print("没有可压的成图（先出完再 --deliver）。")
        else:
            print("已按交付尺寸处理：")
            for path in changed:
                print(path)

    rows = scan(brief)
    print(format_status(brief_path, brief, rows))

    if args.next:
        print()
        if is_fast(brief):
            print(format_fast_next(brief_path, brief, rows))
            return
        limit = args.count if args.count is not None else brief["product_workers"]
        names = next_products(rows, limit, retry=args.retry)
        if not names:
            if names_with(rows, "gen") and not args.retry:
                print("没有待写 Prompt 的品。有 API 就跑：")
                print(f"python scripts/queue_pack.py --queue \"{brief_path}\" --run --skip-existing")
            elif names_with(rows, "done") and not names_with(rows, "prompt", "gen"):
                print("全部完成。整批收口一次即可，不要每个品问要不要建模板。")
            else:
                print("这一波没有可派的品。")
            return
        print(format_worker_brief(brief_path, brief, names, retry=args.retry))
        return

    if args.run:
        print()
        run_queue(brief, rows, args)


if __name__ == "__main__":
    main()
