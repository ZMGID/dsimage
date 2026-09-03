#!/usr/bin/env python3
"""dsimage 命令行。所有命令在技能目录下跑：python scripts/dsimage.py <子命令>

  template list                          看库里有哪些模板
  template init <名> --from <示例夹>      从甲方示例套图建模板骨架（--mode replace|smart）
  template init <名> --blank --slots 9 [--client 甲方]   从零建骨架；--client 放进甲方夹并写入 要求.json
  template check <名>                    校验模板夹（甲方里的可用 甲方/名）
  template freeze <成图根> <SKU> <新名> [--client 甲方]

  template client <甲方>                 建甲方夹和空的 要求.json（先填共用要求）

  sort [--source 大文件夹]               列出源里的品（不改甲方源）
  sort --source <大文件夹> --group 外套=SKU1,SKU2 --group 裤装=SKU3
  sort <分类.json>                      按 分类.json 把品拷到源夹同级「分类」根
  init --template <名> --source <甲方夹或单品夹或图片> [--out <成图根>]
  run <成图根> [--only SKU ...] [--slot H1 ...] [--redo] [--dry-run] [--concurrency N]
  derive <成图根> [--only SKU ...] [--redo]   只派生背面参考图（品没背面图、模板要背面时），先看再 run
  status <成图根>
  deliver <成图根> [--only SKU ...]
  preview <成图根> [--only SKU ...]
  set <成图根> <SKU> [--kind K] [--front 路径] [--back 路径] [--vary H8 "文字"]

  gen "<prompt>" [--ref 图 ...] [--ratio 4:5] [--out 目录] [--name 名] [--n 3]   不走模板，直接出图

  setup env --provider openai|grok|gemini|custom [--base-url URL] --key KEY [--model M]   写 .env 并列出模型
  setup models                            拉服务商模型列表
  setup model <名>                        定模型并试出一张
  setup test                              试出一张 + 列模板
  update [--from <仓库夹|zip>] [--dry-run]  自更新技能文件，保留 .env 和自建模板
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import core  # noqa: E402
import gen_image  # noqa: E402

DEFAULT_CONCURRENCY = 9
SKILL_DIR = ROOT.parent
REPO_ZIP = "https://github.com/ZMGID/dsimage/archive/refs/heads/main.zip"
MANAGED_FILES = ("SKILL.md", "SETUP.md")
MANAGED_DIRS = ("guides", "knowledge", "scripts")
ENV_KEYS = ("IMG_PROVIDER", "IMG_MODEL", "IMG_API_KEY", "IMG_BASE_URL")


def cmd_template(args: argparse.Namespace) -> int:
    if args.action == "list":
        items = core.list_templates()
        if not items:
            print("库里没有模板。用 template init 建一个。")
            return 0
        for item in items:
            label = item.get("key") or item["name"]
            print(f"{label:<32} {item['mode']:<8} {item['slots']} 槽  {item['category']}")
        return 0
    if args.action == "init":
        from_dir = Path(args.source).resolve() if args.source else None
        folder = core.init_template(
            args.name, mode=args.mode, from_dir=from_dir, slot_count=args.slots,
            category=args.category or "", language=args.language or "",
            client=args.client or "",
        )
        print(f"已建模板夹：{folder}")
        if args.client:
            print(f"已写入 {args.client}/{core.REQUIRE_FILE} 的 templates。共用语言/风格/分辨率写在那份文件里，本套差异才写进 template.json。")
        print("下一步：填 template.json（purpose、prompt/brief、style、language），再 template check。")
        return 0
    if args.action == "check":
        folder = core.find_template(args.name)
        problems = core.check_template(core.load_template(folder))
        if problems:
            print(f"{folder.name}：{len(problems)} 个问题")
            for item in problems:
                print(f"  [x] {item}")
            return 1
        print(f"{folder.name}：通过")
        return 0
    if args.action == "freeze":
        batch = core.load_batch(Path(args.output))
        folder = core.freeze_template(batch, args.sku, args.name, client=args.client or "")
        print(f"已冻成 replace 模板：{folder}")
        print("请通读 template.json 每槽 prompt，把生成口吻改成保留口吻，再 template check。")
        return 0
    if args.action == "client":
        folder = core.ensure_client(args.name)
        print(f"甲方夹：{folder}")
        print(f"共用要求：{folder / core.REQUIRE_FILE}")
        print("先填 language / style / generation / brand，跟用户确认后再分类、再建各套模板。")
        return 0
    raise AssertionError(args.action)


def cmd_init(args: argparse.Namespace) -> int:
    template = core.find_template(args.template)
    source = Path(args.source)
    if not source.exists():
        core.fail(f"源不存在：{source}")
    out = Path(args.out).resolve() if args.out else core.default_output_dir(source)
    old_path = core.batch_path(out)
    old_template = core.read_json(old_path).get("template") if old_path.is_file() else None
    batch = core.init_batch(template, source, out)
    tpl = core.load_template(template)
    root = Path(batch["output"])
    print(f"批次：{core.batch_path(root)}")
    print(f"模板：{tpl.get('name')}（{tpl['mode']}）  共 {len(batch['products'])} 个品")
    kinds = tpl.get("product_kinds") if isinstance(tpl.get("product_kinds"), dict) else {}
    if kinds:
        print("品类标签：" + "；".join(f"{k}={v}" for k, v in kinds.items()) + f"  默认 {core.default_kind(tpl)}")
    if old_template and Path(old_template).resolve() != template.resolve():
        print(f"注意：这个成图根之前是用模板「{Path(old_template).name}」出的，已有的 h*.png 不会自动重出，"
              "换模板要 run --redo。")
    loose = core.loose_images(source)
    if loose:
        print(f"注意：源根目录下有 {len(loose)} 张散图不属于任何品，已忽略："
              + "、".join(p.name for p in loose[:5]) + ("…" if len(loose) > 5 else ""))
    print()
    undecided: list[str] = []
    need_back: list[str] = []
    for product in batch["products"]:
        if product.get("front"):
            line = f"{product['sku']:<14} 白图 {Path(product['front']).name}"
            if product.get("back"):
                line += f"  背面 {Path(product['back']).name}"
            elif core.product_needs_back(tpl, product):
                line += "  背面 派生"
                need_back.append(product["sku"])
            print(line)
        else:
            undecided.append(product["sku"])
            print(f"{product['sku']:<14} 待选白图，夹里 {len(product['images'])} 张：")
            for path in product["images"]:
                print(f"{'':16}{path}")
    print()
    print("下一步：")
    pilot = " ".join(p["sku"] for p in batch["products"][:2]) or "<SKU>"
    if undecided:
        print(f"  1) {len(undecided)} 个品有多张图。逐张打开看，选白底/抠图的商品图（不是场景图、不是合成好的主图）：")
        print("     set <成图根> <SKU> --front <路径>   有背面图再加 --back <路径>。没选的品 run 时不出。")
    if kinds:
        print(f"  2) 品类不是「{core.default_kind(tpl)}」的先标：set <成图根> <SKU> --kind <标签>")
    if need_back:
        print(f"  3) {len(need_back)} 个品没有背面图，模板有槽位要背面，出图前会先派生一张。"
              f"试出品先 derive <成图根> --only {pilot} 看派生对不对，再 run。")
    if tpl["mode"] == "replace":
        print(f"  4) 试出两个：run <成图根> --only {pilot}，preview 看完。"
              "有问题改模板后 redo 这两个，点头再 run 全部。")
    else:
        print(f"  4) 试出两个：先 run --only {pilot} 拿 brief；写完这两个 prompts.json（不要照抄 brief），"
              "再 run --only 这两个出图。点头后再给其余写 prompt、run 全部。")
    return 0


def _groups_from_map(data: object) -> dict[str, list[str]]:
    if not isinstance(data, dict):
        core.fail("分类.json 顶层应为对象")
    raw = data.get("groups")
    if not isinstance(raw, dict) or not raw:
        core.fail("分类.json 要有 groups：大类 → 品编号列表")
    groups: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, str):
            groups[str(key)] = [s.strip() for s in value.split(",") if s.strip()]
        elif isinstance(value, list):
            groups[str(key)] = [str(x).strip() for x in value if str(x).strip()]
        else:
            core.fail(f"大类「{key}」的品列表格式不对")
    return groups


def cmd_sort(args: argparse.Namespace) -> int:
    source: Path | None = Path(args.source) if args.source else None
    output = Path(args.out) if args.out else None
    groups: dict[str, list[str]] = {}
    if args.plan:
        data = core.read_json(Path(args.plan))
        groups = _groups_from_map(data)
        if source is None:
            src = data.get("source") if isinstance(data, dict) else None
            if not src:
                core.fail("分类.json 缺 source，或用 --source 指定")
            source = Path(str(src))
        if output is None and isinstance(data, dict) and data.get("output"):
            output = Path(str(data["output"]))
    elif args.group:
        for item in args.group:
            if "=" not in item:
                core.fail("--group 写成 大类=SKU,SKU")
            name, rest = item.split("=", 1)
            groups[name.strip()] = [s.strip() for s in rest.split(",") if s.strip()]
    if source is None:
        core.fail("sort 要给分类.json，或 --source")
    if not source.exists():
        core.fail(f"源不存在：{source}")
    if not groups:
        products = core.scan_source(source)
        print(f"源里 {len(products)} 个品（甲方源不会改）：")
        for product in products:
            n = len(product["images"])
            extra = "已认白图" if product.get("front") and n == 1 else f"{n} 张"
            print(f"  {product['sku']:<14} 夹 {product['folder']:<20} {extra}")
        print("大类即可（外套 / 裤装这种，不要按颜色尺码拆）。跟用户确认后再：")
        print("  sort --source <大文件夹> --group 外套=SKU,SKU --group 裤装=SKU")
        return 0
    dest = core.sort_products(source, groups, output)
    print(f"已分类到 {dest}（甲方源没改）")
    for name, skus in groups.items():
        print(f"  {name}  {len(skus)} 品")
    print("下一步：每个大类做一份模板（--client 甲方），template check 过了，再对该类 init，run --only 先出 2 个。")
    return 0


def _plan_all(batch: dict, tpl: dict, products: list[dict], args: argparse.Namespace) -> dict[str, dict]:
    """给每个品组 jobs 并写 jobs.json；已出的槽位按 --redo 决定要不要重出。"""
    fmt = core.template_output(tpl)["format"]
    index_of = {p["sku"]: i for i, p in enumerate(batch["products"])}
    plans: dict[str, dict] = {}
    for product in products:
        prompts = core.read_prompts(batch, product["sku"]) if tpl["mode"] == "smart" else None
        plan = core.build_jobs(batch, tpl, product, index_of[product["sku"]], args.slot, prompts)
        if not getattr(args, "redo", False):
            dest = Path(batch["output"]) / product["sku"]
            plan["slots"] = [j for j in plan["slots"]
                             if gen_image._existing_output(dest, j["slot"].lower(), fmt) is None]
        kind = core.product_kind(tpl, product)
        slot_by_id = {str(s["id"]): s for s in tpl["slots"]}
        if not any(core.slot_uses_back(tpl, slot_by_id[j["slot"]], kind) for j in plan["slots"]):
            plan["derive"] = []
        core.write_jobs_file(batch, product["sku"], plan)
        plans[product["sku"]] = plan
    return plans


def _load_for_run(args: argparse.Namespace) -> tuple[dict, dict, list[dict]]:
    batch = core.load_batch(Path(args.output))
    tpl = core.load_template(Path(batch["template"]))
    problems = core.check_template(tpl)
    if problems:
        core.fail("模板没过校验：\n  " + "\n  ".join(problems))
    core.check_slot_ids(tpl, getattr(args, "slot", None))
    return batch, tpl, core.select_products(batch, args.only)


def cmd_derive(args: argparse.Namespace) -> int:
    """只派生背面参考图，不出槽位。让 Agent 先看派生图对不对。"""
    batch, tpl, products = _load_for_run(args)
    fmt = core.template_output(tpl)["format"]
    todo: list[dict] = []
    skipped: list[str] = []
    for product in products:
        if not core.product_needs_back(tpl, product, args.slot):
            skipped.append(f"{product['sku']}（这个品类没有槽位要背面）")
            continue
        origin, path = core.back_source(batch, tpl, product)
        if origin == "product":
            skipped.append(f"{product['sku']}（有真背面图 {path.name}）")
            continue
        if origin == "derived" and not args.redo:
            skipped.append(f"{product['sku']}（已派生 {path}，--redo 重派）")
            continue
        if origin == "derived" and args.redo:
            path.unlink()
        if not core.has_front(product):
            skipped.append(f"{product['sku']}（还没选白图）")
            continue
        spec = core.derive_back_spec(tpl)
        refs, _ = core.resolve_refs(spec["refs"], tpl, None, batch, product)
        todo.append(core._job("back", spec["prompt"].replace("{sku}", product["sku"]), refs,
                              core.template_output(tpl), core.work_dir(batch, product["sku"]),
                              f"{product['sku']}/back"))
    for line in skipped:
        print(f"跳过 {line}")
    if not todo:
        print("没有要派生的。")
        return 0
    source = "模板 derive.back" if (tpl.get("derive") or {}).get("back") else "通用背面派生 prompt"
    print(f"派生 {len(todo)} 张背面参考（{source}）" + ("，dry-run 不打接口" if args.dry_run else ""))
    if args.dry_run:
        for job in todo:
            print(f"  {job['label']}  refs: {', '.join(Path(p).name for p in job['image'])}")
        return 0
    failed = core.run_pool(todo, concurrency=args.concurrency, redo=True, env_file=args.env_file,
                           api_mode=args.mode, model_pin=tpl.get("model"), label="derive")
    print()
    print("派生图（打开看：是不是同一个产品的背面、颜色/材质/五金对不对）：")
    for job in todo:
        path = gen_image._existing_output(Path(job["output_dir"]), "back", fmt)
        print(f"  {job['label'].split('/')[0]:<14} {path or '失败'}")
    print("不对：改模板 derive.back 的 prompt 后 derive --redo；或自己找一张背面图 set --back <路径>。对了就 run。")
    return 1 if failed else 0


def _run_wave(jobs: list[dict], args: argparse.Namespace, tpl: dict, label: str) -> list[str]:
    if args.dry_run or not jobs:
        return []
    return core.run_pool(
        jobs, concurrency=args.concurrency, redo=args.redo, env_file=args.env_file,
        api_mode=args.mode, model_pin=tpl.get("model"), label=label,
    )


def cmd_run(args: argparse.Namespace) -> int:
    batch, tpl, products = _load_for_run(args)
    fmt = core.template_output(tpl)["format"]
    slot_by_id = {str(s["id"]): s for s in tpl["slots"]}

    waiting: list[str] = []
    for product in products:
        if tpl["mode"] == "smart" and core.product_status(batch, tpl, product)["state"] == "needs_prompts":
            core.write_smart_packet(batch, tpl, product)
            waiting.append(product["sku"])
    plans = _plan_all(batch, tpl, products, args)

    derive_jobs = [j for plan in plans.values() for j in plan["derive"]]
    blocked = [(sku, s, r) for sku, plan in plans.items() for s, r in plan["blocked"]]
    shown = [(sku, s, r) for sku, s, r in blocked if not (tpl["mode"] == "smart" and r.startswith("prompts.json"))]

    print(f"派生参考 {len(derive_jobs)}，槽位 {sum(len(p['slots']) for p in plans.values())}，卡住 {len(blocked)}"
          + ("（dry-run，不打接口）" if args.dry_run else ""))
    by_reason: dict[str, list[str]] = {}
    for sku, slot, reason in shown:
        by_reason.setdefault(f"{sku}：{reason}", []).append(slot)
    for key, slots in by_reason.items():
        print(f"  卡住 {key}（{'、'.join(slots)}）")
    if waiting:
        print()
        print("现在停：按每份 brief.md 写完该品 prompts.json（brief 只是骨架，打开产品图按这件货写），写齐再 run。")
        for sku in waiting:
            print(f"  {core.work_dir(batch, sku) / core.BRIEF_FILE}")

    failed: list[str] = []
    derived_now: list[tuple[str, Path]] = []
    if derive_jobs and not args.dry_run:
        print()
        print(f"先派生 {len(derive_jobs)} 张背面参考图…")
        failed += _run_wave(derive_jobs, args, tpl, "derive")
        for product in products:
            plan = plans[product["sku"]]
            if not plan["derive"]:
                continue
            derived = core.derived_back(batch, product, fmt)
            if derived is None:
                print(f"  {product['sku']} 背面派生失败，这次跳过需要背面的槽位")
                kind = core.product_kind(tpl, product)
                plan["slots"] = [j for j in plan["slots"] if not core.slot_uses_back(tpl, slot_by_id[j["slot"]], kind)]
            else:
                derived_now.append((product["sku"], derived))
    slot_jobs = [j for plan in plans.values() for j in plan["slots"]]
    if slot_jobs:
        print()
        failed += _run_wave(slot_jobs, args, tpl, "run")
    elif not derive_jobs and not waiting and not blocked:
        print("没有要出的槽位（都已存在）。要重出加 --redo。")

    print()
    print(core.format_status(batch, tpl))
    if derived_now:
        print()
        print("这次新派生的背面图（顺手看一眼，不对就 set --back 或 derive --redo，再 run --redo 相关槽位）：")
        for sku, path in derived_now:
            print(f"  {sku:<14} {path}")
    if args.only and not waiting and slot_jobs and not failed and not args.dry_run:
        print()
        print("试出完了。preview 看图；有问题改模板后 redo 这两个，没问题再 run（不带 --only）。")
    if failed:
        print()
        print("失败的槽位再跑一次同样的 run 即可只补缺的。", file=sys.stderr)
        return 1
    return 0


def cmd_gen(args: argparse.Namespace) -> int:
    """单张 / 几张图，不走模板。prompt 以 @ 开头则读文件。"""
    prompt = args.prompt
    if prompt.startswith("@"):
        path = Path(prompt[1:])
        if not path.is_file():
            core.fail(f"prompt 文件不存在：{path}")
        prompt = path.read_text(encoding="utf-8").strip()
    if not prompt:
        core.fail("prompt 是空的")
    refs: list[str] = []
    for ref in args.ref or []:
        p = Path(ref)
        if not p.is_file():
            core.fail(f"参考图不存在：{p}")
        if p.suffix.lower() not in core.IMAGE_SUFFIXES:
            core.fail(f"不是图片：{p}")
        refs.append(str(p.resolve()))
    if args.ratio not in gen_image.VALID_RATIOS or args.ratio == "auto":
        core.fail(f"--ratio 应为 {'/'.join(r for r in gen_image.VALID_RATIOS if r != 'auto')}，实际 {args.ratio}")
    if args.n < 1:
        core.fail("--n 至少 1")
    out_dir = Path(args.out).resolve()
    name = args.name or time.strftime("image-%Y%m%d-%H%M%S")
    if not re.fullmatch(r"[\w\-. ]+", name):
        core.fail(f"--name 只能用字母数字下划线横线：{name!r}")
    spec = {"ratio": args.ratio, "resolution": args.resolution, "format": args.format, "quality": args.quality}
    names = [name] if args.n == 1 else [f"{name}-{i}" for i in range(1, args.n + 1)]
    jobs = [core._job(n, prompt, refs, spec, out_dir, n) for n in names]
    print(f"{len(jobs)} 张 → {out_dir}  画幅 {args.ratio} {args.resolution} {args.format}"
          + (f"  参考图 {len(refs)} 张" if refs else "") + ("  （dry-run）" if args.dry_run else ""))
    if args.dry_run:
        for job in jobs:
            print(f"  {job['slot']}.{args.format}  refs: {', '.join(Path(r).name for r in refs) or '无'}")
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    failed = core.run_pool(jobs, concurrency=args.concurrency, redo=args.redo, env_file=args.env_file,
                           api_mode=args.mode, model_pin=args.model, label="gen")
    log = out_dir / core.WORK_DIR / "gen.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        for n in names:
            fh.write(json.dumps({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "name": n, "prompt": prompt,
                                 "refs": refs, **spec, "model": args.model or ""}, ensure_ascii=False) + "\n")
    print(f"prompt 已记到 {log}（改图时从这里拿上一版）")
    return 1 if failed else 0


def cmd_status(args: argparse.Namespace) -> int:
    batch = core.load_batch(Path(args.output))
    tpl = core.load_template(Path(batch["template"]))
    print(core.format_status(batch, tpl))
    return 0


def cmd_deliver(args: argparse.Namespace) -> int:
    batch = core.load_batch(Path(args.output))
    tpl = core.load_template(Path(batch["template"]))
    changed = core.deliver_batch(batch, tpl, args.only)
    if not changed:
        print("没有成图可压。")
        return 0
    print(f"已压 {len(changed)} 张到各品夹 {core.DELIVER_DIR}/（成图原件没动）：")
    for path in changed:
        print(f"  {path}")
    return 0


def cmd_preview(args: argparse.Namespace) -> int:
    batch = core.load_batch(Path(args.output))
    tpl = core.load_template(Path(batch["template"]))
    for product in core.select_products(batch, args.only):
        path = core.preview_product(batch, tpl, product)
        print(f"{product['sku']}: {path or '（还没有成图）'}")
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    batch = core.load_batch(Path(args.output))
    tpl = core.load_template(Path(batch["template"]))
    product = core.find_product(batch, args.sku)
    changed: list[str] = []
    hints: list[str] = []
    if args.kind:
        kinds = tpl.get("product_kinds") if isinstance(tpl.get("product_kinds"), dict) else {}
        if not kinds:
            core.fail("这个模板没有 product_kinds，不分品类，不用 --kind")
        if args.kind not in kinds:
            core.fail(f"品类标签 {args.kind!r} 不在模板 product_kinds 里：{'、'.join(kinds)}")
        product["kind"] = args.kind
        changed.append(f"kind={args.kind}")
    for key in ("front", "back"):
        value = getattr(args, key)
        if not value:
            continue
        path = Path(value)
        if not path.is_file():
            by_name = [p for p in product["images"] if Path(p).name == value]
            if len(by_name) != 1:
                core.fail(f"文件不存在：{value}（可以只写文件名，前提是它在该品的图里）")
            path = Path(by_name[0])
        if path.suffix.lower() not in core.IMAGE_SUFFIXES:
            core.fail(f"不是图片：{path}")
        resolved = str(path.resolve())
        if resolved not in product["images"]:
            hints.append(f"{key} 用的是品夹外的图 {path.name}，确认是这个品")
        product[key] = resolved
        changed.append(f"{key}={path.name}")
    if args.front and args.back and product["front"] == product["back"]:
        core.fail("正面和背面是同一张图")
    if args.back:
        derived = core.derived_back(batch, product, core.template_output(tpl)["format"])
        if derived is not None:
            derived.unlink()
            hints.append("已删掉之前派生的背面图，改用你指定的这张")
    slot_by_id = {str(s["id"]).lower(): s for s in tpl["slots"]}
    for slot, text in args.vary or []:
        spec = slot_by_id.get(slot.lower())
        if spec is None:
            core.fail(f"模板没有槽位 {slot}。有：{'、'.join(core.slot_ids(tpl))}")
        texts = [str(spec.get("prompt") or "")] + [str(t) for t in (spec.get("prompt_by_kind") or {}).values()]
        if not any("{vary}" in t for t in texts):
            core.fail(f"槽位 {spec['id']} 的 prompt 里没有 {{vary}}，--vary 对它没用")
        product.setdefault("vary", {})[str(spec["id"])] = text
        changed.append(f"vary[{spec['id']}]")
    if not changed:
        print("没有改动。可改：--kind / --front / --back / --vary SLOT 文字")
        return 0
    core.save_batch(batch)
    core.copy_product_refs(Path(batch["output"]), product)
    print(f"{args.sku} 已更新：{'，'.join(changed)}")
    for hint in hints:
        print(f"  注意：{hint}")
    done = [s for s in core.slot_ids(tpl)
            if gen_image._existing_output(Path(batch["output"]) / args.sku, s.lower(),
                                          core.template_output(tpl)["format"]) is not None]
    if done:
        print(f"  这个品已出 {len(done)} 张，改动要生效请 run --redo --only {args.sku}")
    return 0


# ── setup：配 API ─────────────────────────────────────────

def _env_path(args: argparse.Namespace) -> Path:
    return Path(args.env_file).resolve() if getattr(args, "env_file", None) else SKILL_DIR / ".env"


def _runtime_from_env(env_path: Path) -> tuple[str, str, str, str]:
    """只认这份 .env（覆盖进程环境里的 IMG_*），返回 provider, base_url, model, api_key。"""
    if not env_path.is_file():
        core.fail(f"没有 {env_path}，先 setup env --provider … --key …")
    values = gen_image.read_env_file(env_path)
    for key in ENV_KEYS:
        if key in values:
            os.environ[key] = values[key]
        else:
            os.environ.pop(key, None)
    return gen_image.resolve_runtime()


def _print_models(provider: str, base_url: str, api_key: str, current: str) -> None:
    spec = gen_image.OFFICIAL_PROVIDERS.get(provider, {})
    try:
        image, others = gen_image.list_models(provider, base_url, api_key)
    except gen_image.GenError as exc:
        print(f"拉模型列表失败：{exc}")
        if spec:
            print("用内置名单：")
            image, others = list(spec["models"]), []
        else:
            print("网关不给列表，让用户直接报模型名，然后 setup model <名>。")
            return
    if not image:
        print("列表里没认出图片模型；全部模型如下，让用户挑：")
        image, others = others, []
    print(f"可用图片模型（{provider}）：")
    for idx, name in enumerate(image, 1):
        tag = "  ← 当前" if name == current else ""
        tag += "  推荐" if spec and name == spec.get("default_model") else ""
        print(f"  {idx}. {name}{tag}")
    if others:
        print(f"  （另有 {len(others)} 个非图片模型未列）")


def _template_refs() -> list[str]:
    """拿一份内置模板的两张示例图当参考，试的就是换货用的多图路径。"""
    for item in core.list_templates():
        folder = item["path"]
        found = [str(folder / f"h{i}.png") for i in (1, 2) if (folder / f"h{i}.png").is_file()]
        if found:
            return found
    return []


def _print_template_list() -> None:
    items = core.list_templates()
    print(f"库里 {len(items)} 个模板：" if items else "库里没有模板。")
    for item in items:
        print(f"  {(item.get('key') or item['name']):<24} {item['mode']:<8} {item['slots']} 槽  {item['category']}")


def _setup_test(env_path: Path) -> int:
    provider, base_url, model, api_key = _runtime_from_env(env_path)
    mode = gen_image.detect_mode(provider, base_url, None, model)
    out_dir = SKILL_DIR / "_check"
    refs = _template_refs()
    ns = gen_image._probe_args("")
    ns.image = refs
    if len(refs) >= 2:
        prompt = ("Show the exact product from the first image on a pure white seamless background, centered, "
                  "soft studio light, no text. The second image is the same product; keep shape, color and hardware "
                  "consistent with both.")
    elif refs:
        prompt = "Place the exact product from the first image on a pure white seamless background, centered, soft studio light, no text."
    else:
        prompt = "a single red apple on pure white background, studio lighting"
    print(f"试出一张：{provider} / {model}  mode={mode}" + (f"（带 {len(refs)} 张参考图）" if refs else ""))
    started = time.time()
    paths = gen_image.generate_with_retry(base_url, api_key, model, mode, ns, prompt, out_dir, "setup", "test", retries=2)
    print(f"成功，{time.time() - started:.0f}s：")
    for p in paths:
        print(f"  {p}")
    print("打开看一眼是不是白底上的那个包；是就配好了（多图参考也通了）。")
    print()
    _print_template_list()
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    env_path = _env_path(args)
    if args.action == "env":
        provider = gen_image._normalize_provider(args.provider)
        if provider not in (*gen_image.OFFICIAL_PROVIDERS, "custom"):
            core.fail(f"--provider 应为 openai / grok / gemini / custom，实际 {args.provider!r}")
        key = (args.key or "").strip()
        if not key:
            core.fail("--key 不能为空")
        base_url = (args.base_url or "").strip().rstrip("/")
        if provider == "custom" and not base_url:
            core.fail("兼容网关要 --base-url（例如 https://gateway.example/v1）")
        if provider != "custom" and base_url:
            by_host = gen_image._provider_from_host(base_url)
            if by_host != provider:
                core.fail(f"{provider} 的地址写死在脚本里，不用 --base-url；第三方网关请 --provider custom")
            base_url = ""
        spec = gen_image.OFFICIAL_PROVIDERS.get(provider)
        model = (args.model or "").strip() or (spec["default_model"] if spec else "")
        updates: dict[str, str | None] = {
            "IMG_PROVIDER": provider,
            "IMG_API_KEY": key,
            "IMG_BASE_URL": base_url or None,
            "IMG_MODEL": model or None,
        }
        gen_image.write_env_file(env_path, updates)
        print(f"已写 {env_path}")
        print(f"  provider={provider}" + (f"  base_url={base_url}" if base_url else "") + f"  key={gen_image.mask_key(key)}")
        print(f"  model={model}" if model else "  model=（未定）")
        print()
        _print_models(provider, base_url or gen_image.resolve_base_url(provider, ""), key, model)
        print()
        if model:
            print(f"下一步：用 {model} 就 `setup test`；换别的 `setup model <名>`（会顺手试出一张）。")
        else:
            print("下一步：`setup model <名>` 定模型（会顺手试出一张）。")
        return 0
    if args.action == "models":
        provider, base_url, model, api_key = _runtime_from_env(env_path)
        _print_models(provider, base_url, api_key, model)
        return 0
    if args.action == "model":
        name = args.name.strip()
        if not name:
            core.fail("模型名不能为空")
        if not env_path.is_file():
            core.fail(f"没有 {env_path}，先 setup env")
        gen_image.write_env_file(env_path, {"IMG_MODEL": name})
        print(f"已写 IMG_MODEL={name}")
        if args.no_test:
            return 0
        return _setup_test(env_path)
    if args.action == "test":
        return _setup_test(env_path)
    raise AssertionError(args.action)


# ── update：自更新 ────────────────────────────────────────

def _skill_root_in(folder: Path) -> Path | None:
    for candidate in (folder, folder / "skills" / "dsimage"):
        if (candidate / "SKILL.md").is_file() and (candidate / "scripts" / "dsimage.py").is_file():
            return candidate
    for child in folder.iterdir() if folder.is_dir() else []:
        if child.is_dir():
            found = _skill_root_in(child) if child.name.startswith("dsimage") else None
            if found:
                return found
    return None


def _fetch_source(source: str | None, tmp: Path) -> Path:
    if source:
        p = Path(source).expanduser().resolve()
        if p.is_dir():
            found = _skill_root_in(p)
            if not found:
                core.fail(f"{p} 里找不到 skills/dsimage（要有 SKILL.md 和 scripts/dsimage.py）")
            return found
        if p.is_file() and p.suffix.lower() == ".zip":
            data = p.read_bytes()
        else:
            core.fail(f"--from 应为仓库文件夹或 zip：{p}")
    else:
        print(f"下载 {REPO_ZIP} …")
        try:
            with urllib.request.urlopen(urllib.request.Request(REPO_ZIP, headers={"User-Agent": gen_image.UA}), timeout=120) as resp:
                data = resp.read()
        except OSError as exc:
            core.fail(f"下载失败：{exc}。可以手动下载 zip 后 update --from <zip>，或 git clone 后 update --from <仓库夹>")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(tmp)
    except zipfile.BadZipFile:
        core.fail("不是有效的 zip")
    found = _skill_root_in(tmp)
    if not found:
        core.fail("zip 里找不到 skills/dsimage")
    return found


def _iter_files(folder: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    if not folder.is_dir():
        return files
    for p in folder.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            files[p.relative_to(folder).as_posix()] = p
    return files


def _sync_dir(src: Path, dest: Path, report: dict[str, list[str]], *, dry_run: bool, label: str) -> None:
    src_files = _iter_files(src)
    dest_files = _iter_files(dest)
    for rel, sp in src_files.items():
        dp = dest / rel
        if not dp.exists():
            report["added"].append(f"{label}/{rel}")
        elif dp.read_bytes() != sp.read_bytes():
            report["updated"].append(f"{label}/{rel}")
        else:
            continue
        if not dry_run:
            dp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sp, dp)
    for rel, dp in dest_files.items():
        if rel not in src_files:
            report["removed"].append(f"{label}/{rel}")
            if not dry_run:
                dp.unlink()


def _sync_file(src: Path, dest: Path, report: dict[str, list[str]], *, dry_run: bool, label: str) -> None:
    if not src.is_file():
        return
    if not dest.exists():
        report["added"].append(label)
    elif dest.read_bytes() != src.read_bytes():
        report["updated"].append(label)
    else:
        return
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def sync_skill(src: Path, dest: Path, *, dry_run: bool) -> dict[str, list[str]]:
    """把新版技能文件同步到已装目录：只动受管文件，.env 和自建模板不碰。"""
    report: dict[str, list[str]] = {"added": [], "updated": [], "removed": [], "kept": []}
    for name in MANAGED_FILES:
        sp, dp = src / name, dest / name
        if not sp.is_file():
            continue
        if not dp.exists():
            report["added"].append(name)
        elif dp.read_bytes() != sp.read_bytes():
            report["updated"].append(name)
        else:
            continue
        if not dry_run:
            shutil.copy2(sp, dp)
    for name in MANAGED_DIRS:
        _sync_dir(src / name, dest / name, report, dry_run=dry_run, label=name)
    src_tpl, dest_tpl = src / "templates", dest / "templates"
    src_dirs = {p.name: p for p in src_tpl.iterdir() if p.is_dir()} if src_tpl.is_dir() else {}
    for name, sp in sorted(src_dirs.items()):
        dp = dest_tpl / name
        if core.is_client_dir(sp):
            _sync_file(sp / core.REQUIRE_FILE, dp / core.REQUIRE_FILE, report,
                       dry_run=dry_run, label=f"templates/{name}/{core.REQUIRE_FILE}")
            src_children = {c.name: c for c in sp.iterdir() if c.is_dir() and core.is_template_dir(c)}
            for child_name, child_src in sorted(src_children.items()):
                _sync_dir(child_src, dp / child_name, report, dry_run=dry_run,
                          label=f"templates/{name}/{child_name}")
            if dp.is_dir():
                report["kept"] += [
                    f"templates/{name}/{child.name}"
                    for child in sorted(dp.iterdir())
                    if child.is_dir() and core.is_template_dir(child) and child.name not in src_children
                ]
        else:
            _sync_dir(sp, dp, report, dry_run=dry_run, label=f"templates/{name}")
    if dest_tpl.is_dir():
        report["kept"] += [
            f"templates/{p.name}"
            for p in sorted(dest_tpl.iterdir())
            if p.is_dir() and p.name not in src_dirs
        ]
    if (dest / ".env").is_file():
        report["kept"].append(".env")
    return report


def cmd_update(args: argparse.Namespace) -> int:
    dest = Path(args.dest).resolve() if args.dest else SKILL_DIR
    repo_root = dest.parent.parent
    if not args.source and (repo_root / ".git").exists() and (repo_root / "skills" / "dsimage").resolve() == dest:
        print(f"{dest} 就是 dsimage 仓库本体，直接 git pull：")
        if args.dry_run:
            return 0
        result = subprocess.run(["git", "-C", str(repo_root), "pull", "--ff-only"], capture_output=True, text=True)
        print((result.stdout + result.stderr).strip())
        if result.returncode == 0:
            print()
            _print_template_list()
        return result.returncode
    with tempfile.TemporaryDirectory() as tmp:
        src = _fetch_source(args.source, Path(tmp))
        report = sync_skill(src, dest, dry_run=args.dry_run)
    head = "将要" if args.dry_run else "已"
    print(f"{head}更新 {dest}：新增 {len(report['added'])}，更新 {len(report['updated'])}，删除 {len(report['removed'])}")
    for key, title in (("added", "新增"), ("updated", "更新"), ("removed", "删除")):
        for item in report[key]:
            print(f"  [{title}] {item}")
    if report["kept"]:
        print("原样保留：" + "、".join(report["kept"]))
    if not report["added"] and not report["updated"] and not report["removed"]:
        print("已经是最新。")
    if not args.dry_run:
        print()
        _print_template_list()
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="dsimage：模板 → 试出两个 → 一批品。")
    sub = parser.add_subparsers(dest="command", required=True)

    t = sub.add_parser("template", help="模板管理")
    ts = t.add_subparsers(dest="action", required=True)
    ts.add_parser("list")
    ti = ts.add_parser("init")
    ti.add_argument("name")
    ti.add_argument("--from", dest="source", help="甲方示例套图文件夹（按文件名自然顺序排成 H1…）")
    ti.add_argument("--blank", action="store_true", help="不拷图，只建骨架（配 --slots）")
    ti.add_argument("--slots", type=int, default=0)
    ti.add_argument("--mode", choices=core.MODES, default="replace")
    ti.add_argument("--category")
    ti.add_argument("--language")
    ti.add_argument("--client", help="放进这个甲方夹，并写入 要求.json")
    tc = ts.add_parser("check")
    tc.add_argument("name")
    tf = ts.add_parser("freeze")
    tf.add_argument("output")
    tf.add_argument("sku")
    tf.add_argument("name")
    tf.add_argument("--client", help="冻进这个甲方夹，并写入 要求.json")
    tcl = ts.add_parser("client", help="建甲方夹和空的 要求.json")
    tcl.add_argument("name")

    so = sub.add_parser("sort", help="按大类把品拷到源夹同级分类根（不改甲方源）")
    so.add_argument("plan", nargs="?", help="分类.json，含 source 和 groups")
    so.add_argument("--source", help="甲方大文件夹")
    so.add_argument("--out", help="分类根；默认源夹同级「XX分类」")
    so.add_argument("--group", action="append", help="大类=SKU,SKU，可重复")

    i = sub.add_parser("init", help="扫源、建成图根、写批次")
    i.add_argument("--template", required=True)
    i.add_argument("--source", required=True)
    i.add_argument("--out")

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("output", help="成图根（含 _dsimage/batch.json）")
        p.add_argument("--only", nargs="+", metavar="SKU")

    def add_gen(p: argparse.ArgumentParser) -> None:
        p.add_argument("--slot", nargs="+", metavar="H1")
        p.add_argument("--redo", action="store_true", help="已存在的也重出")
        p.add_argument("--dry-run", action="store_true", help="只组 jobs，不打接口")
        p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
        p.add_argument("--env-file")
        p.add_argument("--mode", choices=gen_image.API_MODES, help="覆盖 API 模式")

    r = sub.add_parser("run", help="出图（replace 直接出；smart 先给 brief）")
    add_common(r)
    add_gen(r)

    d = sub.add_parser("derive", help="只派生背面参考图，先看对不对再 run")
    add_common(d)
    add_gen(d)

    g = sub.add_parser("gen", help="不走模板，直接出一张或几张图")
    g.add_argument("prompt", help="英文 prompt；@文件路径 则从文件读")
    g.add_argument("--ref", action="append", metavar="IMG", help="参考图，可重复；顺序 = prompt 里说的第一张、第二张")
    g.add_argument("--ratio", default="1:1")
    g.add_argument("--resolution", default="1k", choices=gen_image.VALID_RESOLUTIONS)
    g.add_argument("--format", default="png", choices=gen_image.VALID_FORMATS)
    g.add_argument("--quality", default="high", choices=("low", "medium", "high"))
    g.add_argument("--out", default="generated-images", help="输出目录，默认 ./generated-images")
    g.add_argument("--name", help="输出文件名（不带后缀）；默认 image-时间")
    g.add_argument("--n", type=int, default=1, help="同一 prompt 出几张：name-1 … name-N")
    g.add_argument("--model", help="临时指定模型，不写用 .env")
    g.add_argument("--redo", action="store_true", help="同名文件已存在也重出")
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    g.add_argument("--env-file")
    g.add_argument("--mode", choices=gen_image.API_MODES, help="覆盖 API 模式")

    add_common(sub.add_parser("status", help="看进度"))
    add_common(sub.add_parser("deliver", help="按模板 deliver 压交付尺寸"))
    add_common(sub.add_parser("preview", help="每个品拼一张预览图"))

    s = sub.add_parser("set", help="改某个品的标签 / 白图 / 背面 / 每槽变化文字")
    s.add_argument("output")
    s.add_argument("sku")
    s.add_argument("--kind")
    s.add_argument("--front")
    s.add_argument("--back")
    s.add_argument("--vary", nargs=2, action="append", metavar=("SLOT", "TEXT"))

    su = sub.add_parser("setup", help="配生图 API：写 .env、列模型、试出一张")
    sus = su.add_subparsers(dest="action", required=True)
    se = sus.add_parser("env", help="写 .env 并拉模型列表")
    se.add_argument("--provider", required=True, help="openai | grok | gemini | custom")
    se.add_argument("--base-url", help="仅 custom 网关")
    se.add_argument("--key", required=True, help="API key（只写进 .env，不回显）")
    se.add_argument("--model", help="已知模型名就直接写；不写用服务商默认，custom 留空待选")
    se.add_argument("--env-file", help=argparse.SUPPRESS)
    sm = sus.add_parser("models", help="拉服务商模型列表")
    sm.add_argument("--env-file", help=argparse.SUPPRESS)
    sn = sus.add_parser("model", help="定模型，然后试出一张")
    sn.add_argument("name")
    sn.add_argument("--no-test", action="store_true")
    sn.add_argument("--env-file", help=argparse.SUPPRESS)
    st = sus.add_parser("test", help="试出一张带参考图的图，再列模板")
    st.add_argument("--env-file", help=argparse.SUPPRESS)

    u = sub.add_parser("update", help="自更新：拉新版覆盖技能文件，保留 .env 和自建模板")
    u.add_argument("--from", dest="source", help="本地仓库夹或 zip；不写就从 GitHub 下载 main")
    u.add_argument("--dry-run", action="store_true", help="只列会改什么")
    u.add_argument("--dest", help=argparse.SUPPRESS)

    args = parser.parse_args(argv)
    if args.command == "template" and args.action == "init" and not args.source and not args.blank:
        parser.error("template init 要 --from <示例夹> 或 --blank --slots N")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    handlers = {
        "template": cmd_template, "sort": cmd_sort, "init": cmd_init, "run": cmd_run,
        "derive": cmd_derive, "gen": cmd_gen,
        "status": cmd_status,
        "deliver": cmd_deliver, "preview": cmd_preview, "set": cmd_set,
        "setup": cmd_setup, "update": cmd_update,
    }
    try:
        return handlers[args.command](args)
    except core.DsError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except gen_image.GenError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
