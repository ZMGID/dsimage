#!/usr/bin/env python3
"""把新版 dsimage 原地覆盖到已安装目录，不重装、不碰密钥。

- 不读、不写、不删、不复制 .env / .env.*（.env.example 除外）
- 不删除已装目录里多出来的文件（自建模板/情景原位保留）
- 内置情景/模板 JSON：新版打底，把已装里的沉淀（pitfalls / text_rules / 槽位 overrides）合并回去
- 不把已装目录改名备份，不整目录替换
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SKILL_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIR_NAMES = {".git", "__pycache__", ".DS_Store"}


def fail(message: str) -> None:
    print(f"错误：{message}", file=sys.stderr)
    raise SystemExit(1)


def is_secret(path: Path) -> bool:
    name = path.name
    if name == ".env.example":
        return False
    return name == ".env" or name.startswith(".env.")


def rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for item in root.rglob("*"):
        if any(part in SKIP_DIR_NAMES for part in item.relative_to(root).parts):
            continue
        if item.is_file():
            files.append(item)
    return files


def is_library_json(rel: Path) -> bool:
    if rel.suffix != ".json":
        return False
    if rel.parts[:2] == ("references", "scenes") and len(rel.parts) == 3:
        return True
    if rel.parts[:2] != ("references", "templates"):
        return False
    if len(rel.parts) == 3:
        return rel.name not in {"要求.json"}
    if len(rel.parts) == 4 and rel.name == "要求.json":
        return True
    return (
        len(rel.parts) == 5
        and rel.parts[3] in {"风格", "替换"}
    )


def _move_json_and_sidecar(src: Path, dest_dir: Path, report: list[str]) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / src.name
    if dest_path.exists():
        report.append(f"{src.name} 目标已有同名，未覆盖：{dest_dir.as_posix()}")
        return
    shutil.move(str(src), str(dest_path))
    sidecar = src.parent / src.stem
    if sidecar.is_dir():
        dest_side = dest_dir / src.stem
        if dest_side.exists():
            report.append(f"{src.stem}/ 母版目录目标已有，未覆盖")
        else:
            shutil.move(str(sidecar), str(dest_side))
            report.append(f"迁移母版 {src.stem}/ → {dest_dir.as_posix()}")
    report.append(f"迁移 {src.name} → {dest_dir.as_posix()}")


def migrate_flat_templates(dest: Path, report: list[str]) -> None:
    """旧版 风格模板/替换模板/内置/{风格|替换} → templates 根目录（零散）。"""
    root = dest / "references" / "templates"
    if not root.is_dir():
        return
    for old_name in ("风格模板", "替换模板"):
        old_dir = root / old_name
        if not old_dir.is_dir():
            continue
        for path in sorted(old_dir.glob("*.json")):
            _move_json_and_sidecar(path, root, report)
        leftovers = [p.name for p in old_dir.iterdir() if p.name not in {".gitkeep", ".DS_Store"}]
        if leftovers:
            report.append(f"{old_name}/ 仍有未迁移文件：{', '.join(leftovers)}")
        else:
            for extra in old_dir.glob(".gitkeep"):
                extra.unlink()
            try:
                old_dir.rmdir()
                report.append(f"已删除空目录 {old_name}/")
            except OSError:
                report.append(f"{old_name}/ 未清空，未删除")
    builtin = root / "内置"
    if builtin.is_dir():
        for kind in ("风格", "替换"):
            kind_dir = builtin / kind
            if not kind_dir.is_dir():
                continue
            for path in sorted(kind_dir.glob("*.json")):
                _move_json_and_sidecar(path, root, report)
        leftover_json = [p for p in builtin.rglob("*.json") if p.name != "要求.json"]
        if leftover_json:
            report.append("内置/ 仍有未迁到根目录的模板，未删除")
        else:
            shutil.rmtree(builtin)
            report.append("已把 内置/ 里的零散模板挪到 templates/ 根目录")
    for client_dir in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("_")):
        if (root / f"{client_dir.name}.json").is_file():
            continue
        old_meta = client_dir / "_甲方.json"
        new_meta = client_dir / "要求.json"
        if old_meta.is_file() and not new_meta.exists():
            shutil.move(str(old_meta), str(new_meta))
            report.append(f"迁移 {client_dir.name}/_甲方.json → 要求.json")


def dump_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def merge_list(new: list[Any], old: list[Any]) -> tuple[list[Any], int]:
    out = list(new)
    added = 0
    for item in old:
        if item not in out:
            out.append(item)
            added += 1
    return out, added


def merge_text_rules(
    new: dict[str, Any], old: dict[str, Any], notes: list[str], prefix: str
) -> dict[str, Any]:
    out = dict(new)
    for key, value in old.items():
        if key not in out:
            out[key] = value
            notes.append(f"{prefix}text_rules.{key} 保留用户键")
        elif out[key] != value:
            out[key] = value
            notes.append(f"{prefix}text_rules.{key} 保留用户值")
    return out


def merge_overrides(
    new: dict[str, Any], old: dict[str, Any], notes: list[str], prefix: str
) -> dict[str, Any]:
    out = dict(new)
    for key, value in old.items():
        if key not in out:
            out[key] = value
            notes.append(f"{prefix}overrides.{key} 保留用户键")
        elif out[key] != value:
            out[key] = value
            notes.append(f"{prefix}overrides.{key} 保留用户值")
    return out


def merge_pack(
    new_pack: dict[str, Any], old_pack: dict[str, Any], notes: list[str], prefix: str
) -> dict[str, Any]:
    out = dict(new_pack)
    new_images = out.get("images")
    old_images = old_pack.get("images")
    if not isinstance(new_images, list) or not isinstance(old_images, list):
        return out
    old_by_slot = {
        img.get("slot"): img
        for img in old_images
        if isinstance(img, dict) and img.get("slot")
    }
    merged: list[Any] = []
    seen: set[str] = set()
    for img in new_images:
        if not isinstance(img, dict):
            merged.append(img)
            continue
        slot = img.get("slot")
        copied = dict(img)
        if isinstance(slot, str):
            seen.add(slot)
            old_img = old_by_slot.get(slot)
            if isinstance(old_img, dict) and isinstance(old_img.get("overrides"), dict):
                new_ov = copied.get("overrides") if isinstance(copied.get("overrides"), dict) else {}
                copied["overrides"] = merge_overrides(
                    new_ov, old_img["overrides"], notes, f"{prefix}{slot}."
                )
        merged.append(copied)
    for slot, old_img in old_by_slot.items():
        if slot not in seen:
            merged.append(old_img)
            notes.append(f"{prefix}槽位 {slot} 保留用户槽")
    out["images"] = merged
    return out


def merge_client_meta(
    new: dict[str, Any], old: dict[str, Any], label: str
) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    out = dict(new)
    for key, value in old.items():
        if key not in out:
            out[key] = value
            notes.append(f"{label} 保留用户键 {key}")
        elif key == "notes" and isinstance(value, list) and isinstance(out.get("notes"), list):
            out["notes"], added = merge_list(out["notes"], value)
            if added:
                notes.append(f"{label} notes +{added}")
        elif key in {"language", "generation", "style", "brand", "name"} and out.get(key) != value:
            out[key] = value
            notes.append(f"{label} {key} 保留用户值")
    return out, notes


def merge_library_json(
    new: dict[str, Any], old: dict[str, Any], label: str
) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    out = dict(new)
    if isinstance(new.get("pitfalls"), list) and isinstance(old.get("pitfalls"), list):
        out["pitfalls"], added = merge_list(new["pitfalls"], old["pitfalls"])
        if added:
            notes.append(f"{label} pitfalls +{added}")
    if isinstance(new.get("text_rules"), dict) and isinstance(old.get("text_rules"), dict):
        out["text_rules"] = merge_text_rules(new["text_rules"], old["text_rules"], notes, f"{label} ")
    if isinstance(new.get("pack"), dict) and isinstance(old.get("pack"), dict):
        out["pack"] = merge_pack(new["pack"], old["pack"], notes, f"{label} ")
    return out, notes


def insert_table_row(text: str, heading: str, row: str) -> str:
    idx = text.find(heading)
    if idx < 0:
        return text
    tail = text[idx:]
    lines = tail.splitlines(keepends=True)
    last_table = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            last_table = i
        elif last_table and stripped and not stripped.startswith("|"):
            break
    if last_table == 0:
        return text
    row_line = row if row.endswith("\n") else row + "\n"
    lines.insert(last_table + 1, row_line)
    return text[:idx] + "".join(lines)


def register_user_files(dest: Path, user_rels: list[Path], report: list[str]) -> None:
    skill_path = dest / "SKILL.md"
    if not skill_path.is_file() or not user_rels:
        return
    text = skill_path.read_text(encoding="utf-8")
    changed = False
    for rel in user_rels:
        fname = rel.name
        if fname in text:
            continue
        data = load_json(dest / rel)
        triggers = data.get("trigger_phrases", []) if data else []
        trigger = ", ".join(str(t) for t in triggers[:4]) or fname
        if rel.parts[:2] == ("references", "templates"):
            if rel.name == "要求.json":
                continue
            ttype = (data or {}).get("template_type") or "style"
            heading = "### 替换模板匹配表" if ttype == "replace" else "### 风格模板匹配表"
            if len(rel.parts) == 3:
                cell = f"`templates/{fname}`"
            elif len(rel.parts) == 5 and rel.parts[3] in {"风格", "替换"}:
                client, kind = rel.parts[2], rel.parts[3]
                cell = f"`templates/{client}/{kind}/{fname}`"
                heading = "### 替换模板匹配表" if kind == "替换" else "### 风格模板匹配表"
            else:
                continue
        else:
            cell = f"`{fname}`"
            heading = "### 情景匹配表"
        text = insert_table_row(text, heading, f"| {trigger} | {cell} |")
        changed = True
        report.append(f"登记 {fname}")
    if changed:
        skill_path.write_text(text, encoding="utf-8")


def update(source: Path, dest: Path) -> int:
    source = source.resolve()
    dest = dest.resolve()
    if not (source / "SKILL.md").is_file():
        fail(f"新版目录不像 dsimage Skill：{source}")
    if not dest.exists():
        fail(f"已装目录不存在：{dest}。这是安装，不是更新。")
    if not (dest / "SKILL.md").is_file():
        fail(f"已装目录不像 dsimage Skill：{dest}")

    report: list[str] = []
    env_path = dest / ".env"
    if env_path.is_file():
        report.append("保留 .env（未读取、未改动、未复制）")
    else:
        report.append("已装目录没有 .env（不是被这次更新删掉的）")

    migrate_flat_templates(dest, report)

    if source == dest:
        print("已装目录就是新版目录（例如仓库里的 skills/dsimage）。")
        print("git pull 已经是更新；密钥和用户文件原位不动。")
        for line in report:
            print(f"  {line}")
        return 0

    source_files = {Path(rel_posix(p, source)): p for p in iter_files(source) if not is_secret(p)}
    dest_json = {
        Path(rel_posix(p, dest)): p
        for p in iter_files(dest)
        if is_library_json(Path(rel_posix(p, dest)))
    }
    user_json = sorted(rel for rel in dest_json if rel not in source_files)

    copied = 0
    merged = 0
    for rel, src_path in sorted(source_files.items(), key=lambda item: item[0].as_posix()):
        dest_path = dest / rel
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if is_library_json(rel) and dest_path.is_file():
            new_data = load_json(src_path)
            old_data = load_json(dest_path)
            if new_data is None:
                fail(f"新版 JSON 无法解析：{rel.as_posix()}")
            if old_data is None:
                shutil.copy2(src_path, dest_path)
                copied += 1
                report.append(f"覆盖 {rel.as_posix()}（已装文件无法解析，已用新版替换）")
                continue
            old_id = old_data.get("id")
            new_id = new_data.get("id")
            if old_id and new_id and old_id != new_id:
                report.append(
                    f"跳过 {rel.as_posix()}：已装是用户模板「{old_id}」，"
                    f"与新版「{new_id}」文件名冲突，用户文件未改"
                )
                continue
            if rel.name == "要求.json":
                merged_data, notes = merge_client_meta(new_data, old_data, rel.as_posix())
            else:
                merged_data, notes = merge_library_json(new_data, old_data, rel.as_posix())
            dest_path.write_text(dump_json(merged_data), encoding="utf-8")
            merged += 1
            if notes:
                report.extend(notes)
            else:
                report.append(f"更新 {rel.as_posix()}")
            continue
        shutil.copy2(src_path, dest_path)
        copied += 1

    for rel in user_json:
        report.append(f"保留用户文件 {rel.as_posix()}")

    leftover_secrets = [
        rel_posix(p, dest)
        for p in iter_files(dest)
        if is_secret(p)
    ]
    if leftover_secrets:
        report.append("密钥文件仍在：" + "、".join(leftover_secrets))

    register_user_files(dest, user_json, report)

    print(f"原地更新完成：{dest}")
    print(f"覆盖/新增 {copied} 个文件，合并 {merged} 个内置情景/模板，保留 {len(user_json)} 个用户文件")
    for line in report:
        print(f"  {line}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把新版 dsimage 原地覆盖到已安装目录。不碰 .env，不删用户文件，不整目录重装。"
    )
    parser.add_argument(
        "--source",
        default=str(SKILL_ROOT),
        help="新版 skills/dsimage 路径，默认本脚本所在 Skill 目录。",
    )
    parser.add_argument(
        "--dest",
        required=True,
        help="已安装的 dsimage 目录，例如 ~/.codex/skills/dsimage。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raise SystemExit(update(Path(args.source), Path(args.dest)))


if __name__ == "__main__":
    main()
