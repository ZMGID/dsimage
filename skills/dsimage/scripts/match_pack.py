#!/usr/bin/env python3
"""按用户原话给模板/情景打分，输出前 3 名方案（最优在第 1）。

Agent 出图前执行，把 stdout 原样给用户看。点名的模板不在库里时会说明，
不会悄悄改成白底主图。
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

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCENES_DIR = SKILL_ROOT / "references" / "scenes"
TEMPLATES_DIR = SKILL_ROOT / "references" / "templates"
CLIENT_META = "要求.json"
KIND_FOLDER = {"风格": "style", "替换": "replace"}
LEGACY_TOP = {"风格模板", "替换模板"}
STARTER_ID = "默认电商模板"
STARTER_HINTS = (
    "全套", "详情页", "pdp", "amazon", "listing", "主图套",
    "电商", "起步", "出一套", "做一套", "listing images",
)
MASTER_HINTS = (
    "替换模板", "只换产品", "只换货", "换品", "版式别动",
    "按样图换货", "一模一样", "各型号统一", "母版换货",
    "快速换货", "同类快换", "快速替换",
)
FAST_HINTS = ("快速换货", "同类快换", "快速替换")
LOCK_ALIASES = {"rules": "rules", "master": "master", "style": "rules", "replace": "master"}
NAMED_MASTER = re.compile(r"替换模板\s*[：:]\s*([^\s，,。；;]+)")
NAMED_TEMPLATE = re.compile(r"(?<!替换)模板\s*[：:]\s*([^\s，,。；;]+)")


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _rel_template(path: Path) -> str:
    return "templates/" + path.relative_to(TEMPLATES_DIR).as_posix()


def _hit_score(query: str, phrases: list[str], weight: int) -> int:
    q = query.casefold()
    score = 0
    seen: set[str] = set()
    for raw in phrases:
        phrase = str(raw).strip()
        if not phrase:
            continue
        key = phrase.casefold()
        if key in seen:
            continue
        seen.add(key)
        if key in q:
            score += weight
        elif len(key) >= 6 and q in key:
            score += max(1, weight // 2)
    return score


def resolve_lock(data: dict[str, Any]) -> str:
    raw_lock = data.get("lock")
    raw_legacy = data.get("template_type")
    if isinstance(raw_lock, str) and raw_lock in LOCK_ALIASES:
        return LOCK_ALIASES[raw_lock]
    if isinstance(raw_legacy, str) and raw_legacy in LOCK_ALIASES:
        return LOCK_ALIASES[raw_legacy]
    return "rules"


def _named_from_query(query: str) -> tuple[str | None, str | None]:
    master = NAMED_MASTER.search(query)
    if master:
        return "master", master.group(1).strip()
    named = NAMED_TEMPLATE.search(query)
    if named:
        return "template", named.group(1).strip()
    return None, None


def _intent_master(query: str) -> bool:
    return any(hint in query for hint in MASTER_HINTS)


def _name_matches(named: str, data: dict[str, Any], path: Path) -> bool:
    named_cf = named.casefold()
    stem = path.stem
    chinese = stem.split("-", 1)[1] if "-" in stem else stem
    candidates = [
        str(data.get("id") or ""),
        str(data.get("name") or ""),
        chinese,
        stem,
    ]
    return any(named_cf == c.casefold() or named_cf in c.casefold() for c in candidates if c)


def _slots_from_template(data: dict[str, Any]) -> list[dict[str, str]]:
    pack = data.get("pack") if isinstance(data.get("pack"), dict) else {}
    images = pack.get("images") if isinstance(pack, dict) else []
    slots: list[dict[str, str]] = []
    if not isinstance(images, list):
        return slots
    for img in images:
        if not isinstance(img, dict):
            continue
        slot = str(img.get("slot") or "")
        purpose = str(img.get("purpose") or "")
        scene = str(img.get("scene") or img.get("example") or "")
        if slot and (scene or purpose):
            slots.append({"slot": slot, "purpose": purpose, "scene": scene})
    return slots


def load_library() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    templates: list[dict[str, Any]] = []
    scenes: list[dict[str, Any]] = []
    if SCENES_DIR.is_dir():
        for path in sorted(SCENES_DIR.glob("*.json")):
            data = load_json(path)
            if not data:
                continue
            scenes.append({
                "kind": "scene",
                "id": str(data.get("id") or path.stem),
                "name": str(data.get("name") or path.stem),
                "path": f"scenes/{path.name}",
                "file": path.name,
                "triggers": [str(x) for x in (data.get("trigger_phrases") or [])],
                "keywords": [str(x) for x in (data.get("keywords") or [])],
                "ratio": str(data.get("default_ratio") or "1:1"),
            })
    if not TEMPLATES_DIR.is_dir():
        return templates, scenes
    json_paths: list[Path] = []
    json_paths.extend(p for p in TEMPLATES_DIR.glob("*.json") if p.name != CLIENT_META)
    for entry in sorted(TEMPLATES_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_") or entry.name in LEGACY_TOP:
            continue
        if (entry / CLIENT_META).is_file():
            json_paths.extend(p for p in sorted(entry.glob("*.json")) if p.name != CLIENT_META)
            for child in sorted(entry.iterdir()):
                if not child.is_dir():
                    continue
                nested = child / f"{child.name}.json"
                if nested.is_file():
                    json_paths.append(nested)
                if child.name in KIND_FOLDER:
                    json_paths.extend(sorted(child.glob("*.json")))
        else:
            nested = entry / f"{entry.name}.json"
            if nested.is_file():
                json_paths.append(nested)
    seen: set[Path] = set()
    for path in json_paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        data = load_json(path)
        if not data:
            continue
        lock = resolve_lock(data)
        templates.append({
            "kind": lock,
            "id": str(data.get("id") or path.stem),
            "name": str(data.get("name") or data.get("id") or path.stem),
            "path": _rel_template(path),
            "file": path,
            "triggers": [str(x) for x in (data.get("trigger_phrases") or [])],
            "keywords": [str(x) for x in (data.get("keywords") or [])],
            "slots": _slots_from_template(data),
        })
    return templates, scenes


def _item_path(item: dict[str, Any]) -> Path:
    file = item.get("file")
    if isinstance(file, Path):
        return file
    return Path(str(item.get("path") or item.get("id") or "item"))


def score_item(query: str, item: dict[str, Any], named_kind: str | None, named: str | None) -> int:
    score = _hit_score(query, item.get("triggers") or [], 12)
    score += _hit_score(query, item.get("keywords") or [], 4)
    if named and _name_matches(named, item, _item_path(item)):
        if named_kind == "master" and item["kind"] != "master":
            return score
        score += 1000
    return score


def rank_plans(query: str, *, top_n: int = 3) -> dict[str, Any]:
    query = (query or "").strip()
    templates, scenes = load_library()
    named_kind, named = _named_from_query(query)
    want_master = named_kind == "master" or _intent_master(query)
    named_hit = False
    if named:
        pool = templates
        if named_kind == "master":
            pool = [t for t in templates if t["kind"] == "master"]
        named_hit = any(_name_matches(named, t, _item_path(t)) for t in pool)

    starter_bonus = 0
    if not named_hit:
        q = query.casefold()
        starter_bonus = min(24, 8 * sum(1 for hint in STARTER_HINTS if hint in q))

    plans: list[dict[str, Any]] = []
    for tmpl in templates:
        score = score_item(query, tmpl, named_kind, named)
        if tmpl["id"] == STARTER_ID and tmpl["kind"] == "rules":
            if starter_bonus:
                score += starter_bonus
            elif named and not named_hit:
                score += 5
        if want_master and tmpl["kind"] != "master":
            score = max(0, score - 20)
        if want_master and tmpl["kind"] == "master" and not named_hit:
            score += 15
        suffix = "（母版换货）" if tmpl["kind"] == "master" else ""
        plans.append({
            "kind": tmpl["kind"],
            "title": tmpl["name"],
            "path": tmpl["path"],
            "score": score,
            "slots": tmpl["slots"],
            "label": f"模板「{tmpl['name']}」{suffix}",
        })

    best_scene = None
    best_scene_score = -1
    for scene in scenes:
        score = score_item(query, scene, None, None)
        if named_kind == "master":
            score = max(0, score - 8)
        if score > best_scene_score:
            best_scene_score = score
            best_scene = scene
    if best_scene is not None:
        plans.append({
            "kind": "scene",
            "title": best_scene["name"],
            "path": best_scene["path"],
            "score": best_scene_score,
            "slots": [{
                "slot": "H1",
                "purpose": best_scene["name"],
                "scene": best_scene["file"],
            }],
            "label": f"仅情景「{best_scene['name']}」",
        })

    plans.sort(key=lambda p: (
        -p["score"],
        0 if p.get("title") == STARTER_ID else 1,
        p["kind"] != "rules",
        p["title"],
    ))
    # 同路径去重后取前 N
    seen: set[str] = set()
    ranked: list[dict[str, Any]] = []
    for plan in plans:
        if plan["path"] in seen:
            continue
        seen.add(plan["path"])
        ranked.append(plan)
        if len(ranked) >= top_n:
            break

    notes: list[str] = []
    if named and not named_hit:
        notes.append(f"你点的模板「{named}」不在库里。下面是最接近的三个，不会改成白底主图充数。")
    if want_master and not any(p["kind"] == "master" for p in ranked):
        notes.append("库里没有带母版的模板。下面是按规则画的备选；要换货需要先有母版套图。")
    if any(hint in query for hint in FAST_HINTS):
        notes.append("快速换货：有样板文件夹就用 --masters，不要改走默认电商模板。读 FAST_SWAP.md，试跑一套后由脚本铺开。")

    return {"query": query, "named": named, "named_hit": named_hit, "notes": notes, "plans": ranked}


def format_slots(slots: list[dict[str, str]]) -> str:
    if not slots:
        return "（无槽位）"
    parts: list[str] = []
    extra = 0
    for item in slots:
        if len(parts) >= 8:
            extra += 1
            continue
        bit = item["slot"]
        if item.get("purpose"):
            bit += " " + item["purpose"]
        if item.get("scene"):
            bit += " ← " + item["scene"]
        parts.append(bit)
    text = " · ".join(parts)
    if extra:
        text += f" 等 {extra} 槽"
    return text


def format_report(result: dict[str, Any]) -> str:
    lines: list[str] = []
    for note in result.get("notes") or []:
        lines.append(note)
        lines.append("")
    lines.append("准备这样出（第 1 个最优）：")
    lines.append("")
    plans = result.get("plans") or []
    if not plans:
        lines.append("库里没有可匹配的模板或情景。停下问用户要哪种结果，不要假装已匹配。")
        return "\n".join(lines)
    for index, plan in enumerate(plans, start=1):
        mark = "【采用】" if index == 1 else ""
        lines.append(f"{index}. {mark}{plan['label']}")
        lines.append(f"   {plan['path']}")
        lines.append(f"   场景：{format_slots(plan.get('slots') or [])}")
    lines.append("")
    lines.append("回 1 / 2 / 3 换方案。还有没有要求（货号、只要某几页、某个型号先不出）？没有就按第 1 个开做。")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="给用户原话匹配前 3 名出图方案，最优在第 1。")
    parser.add_argument("--query", required=True, help="用户原话，不要改写。")
    parser.add_argument("--json", action="store_true", help="输出 JSON 而不是给人看的排名。")
    parser.add_argument("--top", type=int, default=3, help="返回几名，默认 3。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = rank_plans(args.query, top_n=max(1, args.top))
    if args.json:
        payload = {
            **result,
            "plans": [
                {k: v for k, v in plan.items() if k != "file"}
                for plan in result["plans"]
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(format_report(result))


if __name__ == "__main__":
    main()
