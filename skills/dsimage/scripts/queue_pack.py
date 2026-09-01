#!/usr/bin/env python3
"""多品并发队列：状态看磁盘，主会话只调度。

2 个及以上品文件夹时用这个，不要在一条对话里按品串行。

  python scripts/queue_pack.py --init --source 春季新品 --template templates/BeautyU/01-箱包单品报价模板/01-箱包单品报价模板.json
  python scripts/queue_pack.py --queue 春季新品-成图/_prompts/批次.json
  python scripts/queue_pack.py --queue ... --next
  python scripts/queue_pack.py --queue ... --run --skip-existing   # 生图单独走，默认并发 32
"""
from __future__ import annotations

import argparse
import json
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


def product_images(folder: Path) -> list[Path]:
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )


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
    src = source_dir / name
    if not product_images(src):
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
    for folder in list_product_dirs(Path(brief["source_dir"])):
        status = classify_product(folder.name, brief)
        rows.append({"name": folder.name, "status": status})
    named = {row["name"] for row in rows}
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
        f"模板：{brief.get('template') or '（未写）'}  lock={brief.get('lock') or 'rules'}",
        f"品工人同时最多 {brief['product_workers']} 路（写 Prompt）",
        f"生图并发 {brief['gen_concurrency']}（--run 单独走）",
        "",
    ]
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
        f"源文件夹：{source / '{品名}'}",
        f"Prompt / jobs.json → {output / '_prompts' / '{品名}'}/",
        f"成图 → {output / '{品名}'}/  只放 h1.png 这类槽位图",
        "参考图只用该品源文件夹里的图。源图文件名按 SKILL「源图文件名」对槽。",
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
    source = Path(args.source).resolve()
    if not source.is_dir():
        fail(f"源目录不存在：{source}")
    output = Path(args.output).resolve() if args.output else source.parent / f"{source.name}-成图"
    template_path = resolve_template(args.template, Path.cwd())
    if args.template and template_path is None:
        fail(f"找不到模板：{args.template}")
    lock, style_lock = read_style_lock(template_path)
    if args.lock:
        lock = args.lock
    only = [x for x in (args.only or []) if x.strip()]
    skip = [x for x in (args.skip or []) if x.strip()]
    products = list_product_dirs(source)
    if only:
        missing = [name for name in only if not (source / name).is_dir()]
        if missing:
            fail("only 里没有这些子文件夹：" + "、".join(missing))
    elif len(products) < 2 and not skip:
        print("提示：源目录下品文件夹不足 2 个。批量并发按「2 个及以上」才走这条路。", file=sys.stderr)
    payload = {
        "source_dir": str(source),
        "output_dir": str(output),
        "template": template_rel(template_path),
        "lock": lock,
        "only": only,
        "skip": skip,
        "product_workers": max(1, min(8, args.workers)),
        "gen_concurrency": resolve_gen_concurrency(args),
        "notes": args.notes or "",
        "style_lock": style_lock,
    }
    brief_path = output / "_prompts" / BRIEF_NAME
    write_brief(brief_path, payload)
    output.mkdir(parents=True, exist_ok=True)
    return brief_path


def gen_namespace(args: argparse.Namespace) -> argparse.Namespace:
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
        resolution="1k",
        quality=None,
        n=1,
        image=None,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
        format="png",
    )


def collect_run_jobs(brief: dict[str, Any], rows: list[dict[str, str]],
                     args: argparse.Namespace) -> list[dict[str, Any]]:
    output = Path(brief["output_dir"])
    names = names_with(rows, "gen")
    if args.product:
        wanted = set(args.product)
        names = [name for name in names if name in wanted]
        extra = [name for name in args.product if name not in names]
        if extra:
            print("这些品现在不是待出图：" + "、".join(extra), file=sys.stderr)
    jobs: list[dict[str, Any]] = []
    dummy = gen_namespace(args)
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
    jobs = collect_run_jobs(brief, rows, args)
    if not jobs:
        print("没有待出图的槽位。有待写 Prompt 的品就 --next 派工人；都完成则停。")
        return
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="多品并发队列。状态看磁盘；--next 派品工人；--run 用全局并发出图。"
    )
    parser.add_argument("--init", action="store_true", help="扫描源目录，写入成图根/_prompts/批次.json")
    parser.add_argument("--source", help="--init 用的源大文件夹")
    parser.add_argument("--output", help="成图根目录；默认 {源目录名}-成图，与源同级")
    parser.add_argument("--template", help="模板 JSON 路径（相对 references/ 或绝对路径）")
    parser.add_argument("--lock", choices=("rules", "master"), help="覆盖模板里的 lock")
    parser.add_argument("--only", action="append", default=[], help="只做这些品文件夹名，可重复")
    parser.add_argument("--skip", action="append", default=[], help="跳过这些品文件夹名，可重复")
    parser.add_argument("--workers", type=int, default=3, help="品工人同时几路，默认 3，最大 8")
    parser.add_argument("--notes", default="", help="写进批次.json 的口头要求")
    parser.add_argument("--queue", help="批次.json 路径，或它所在的 _prompts/ 目录")
    parser.add_argument("--next", action="store_true", help="打印下一波待写 Prompt 的品 + 工人任务原文")
    parser.add_argument("-n", "--count", type=int, help="--next 派几个；默认用批次里的 product_workers")
    parser.add_argument("--retry", action="store_true", help="--next 时也派待出图的品（宿主补图 / 失败重做）")
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
    if not args.init and not args.queue:
        parser.error("请提供 --queue 批次.json，或用 --init --source 新建")
    return args


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
    rows = scan(brief)
    print(format_status(brief_path, brief, rows))

    if args.next:
        limit = args.count if args.count is not None else brief["product_workers"]
        names = next_products(rows, limit, retry=args.retry)
        print()
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
