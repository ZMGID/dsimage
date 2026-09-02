#!/usr/bin/env python3
"""dsimage 命令行。所有命令在技能目录下跑：python scripts/dsimage.py <子命令>

  template list                          看库里有哪些模板
  template init <名> --from <示例夹>      从甲方示例套图建模板骨架（--mode replace|smart）
  template init <名> --blank --slots 9   从零建 smart 模板骨架
  template check <名>                    校验模板夹
  template freeze <成图根> <SKU> <新名>   smart 批次的一品成图 + prompt 冻成 replace 模板

  init --template <名> --source <甲方夹或单品夹或图片> [--out <成图根>]
  run <成图根> [--only SKU ...] [--slot H1 ...] [--redo] [--dry-run] [--concurrency N]
  derive <成图根> [--only SKU ...] [--redo]   只派生背面参考图（品没背面图、模板要背面时），先看再 run
  status <成图根>
  deliver <成图根> [--only SKU ...]
  preview <成图根> [--only SKU ...]
  set <成图根> <SKU> [--kind K] [--front 路径] [--back 路径] [--vary H8 "文字"]

  gen "<prompt>" [--ref 图 ...] [--ratio 4:5] [--out 目录] [--name 名] [--n 3]   不走模板，直接出图
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import core  # noqa: E402
import gen_image  # noqa: E402

DEFAULT_CONCURRENCY = 9


def cmd_template(args: argparse.Namespace) -> int:
    if args.action == "list":
        items = core.list_templates()
        if not items:
            print("库里没有模板。用 template init 建一个。")
            return 0
        for item in items:
            print(f"{item['name']:<24} {item['mode']:<8} {item['slots']} 槽  {item['category']}")
        return 0
    if args.action == "init":
        from_dir = Path(args.source).resolve() if args.source else None
        folder = core.init_template(
            args.name, mode=args.mode, from_dir=from_dir, slot_count=args.slots,
            category=args.category or "", language=args.language or "",
        )
        print(f"已建模板夹：{folder}")
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
        folder = core.freeze_template(batch, args.sku, args.name)
        print(f"已冻成 replace 模板：{folder}")
        print("请通读 template.json 每槽 prompt，把生成口吻改成保留口吻，再 template check。")
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
    if undecided:
        print(f"  1) {len(undecided)} 个品有多张图。逐张打开看，选白底/抠图的商品图（不是场景图、不是合成好的主图）：")
        print("     set <成图根> <SKU> --front <路径>   有背面图再加 --back <路径>。没选的品 run 时不出。")
    if kinds:
        print(f"  2) 品类不是「{core.default_kind(tpl)}」的先标：set <成图根> <SKU> --kind <标签>")
    if need_back:
        print(f"  3) {len(need_back)} 个品没有背面图，模板有槽位要背面，出图前会先派生一张。"
              "第一个品建议先 derive <成图根> --only <SKU> 看派生对不对，再 run。")
    if tpl["mode"] == "replace":
        print("  4) 先出一个品：run <成图根> --only <SKU>，preview 看完点头再 run 全部。")
    else:
        print("  4) run <成图根> 会给每个品写 brief.md + prompts.json；按 brief 写好 prompt 再 run。")
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
        print("这些品还没有 prompt，已写好 brief.md + prompts.json，按 brief 填完再 run：")
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
    print(f"已按模板 deliver 处理 {len(changed)} 张：")
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="dsimage：模板 → 一个品 → 一批品。")
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
    tc = ts.add_parser("check")
    tc.add_argument("name")
    tf = ts.add_parser("freeze")
    tf.add_argument("output")
    tf.add_argument("sku")
    tf.add_argument("name")

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

    args = parser.parse_args(argv)
    if args.command == "template" and args.action == "init" and not args.source and not args.blank:
        parser.error("template init 要 --from <示例夹> 或 --blank --slots N")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    handlers = {
        "template": cmd_template, "init": cmd_init, "run": cmd_run, "derive": cmd_derive, "gen": cmd_gen,
        "status": cmd_status,
        "deliver": cmd_deliver, "preview": cmd_preview, "set": cmd_set,
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
