#!/usr/bin/env python3
"""校验 references/templates/ 下所有模板的完整性（依据 _TEMPLATE_SPEC.md）。"""
import glob
import json
import os
import sys

TPL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "templates")

REQUIRED = ["id", "name", "keywords", "trigger_phrases", "prompt_template",
            "default_ratio", "composition_rules", "text_rules", "workflow",
            "pitfalls", "examples", "supports_image_reference"]


def fail(fname: str, msg: str) -> None:
    print(f"  [x] {fname}: {msg}")
    global errors
    errors += 1


errors = 0
files = sorted(glob.glob(os.path.join(TPL_DIR, "*.json")))
all_keywords: dict[str, str] = {}

for path in files:
    fname = os.path.basename(path)
    try:
        d = json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(fname, f"JSON 解析失败：{exc}")
        continue

    # 必填字段
    for key in REQUIRED:
        if key not in d or d[key] in ("", None, [], {}):
            fail(fname, f"缺少必填字段或为空：{key}")

    # id 与文件名一致
    stem = os.path.splitext(fname)[0]
    expected_id = stem.split("-", 1)[1] if "-" in stem else stem
    if d.get("id") != expected_id:
        fail(fname, f"id 应为 {expected_id!r}，实际 {d.get('id')!r}")

    # 类型检查
    for key in ("keywords", "trigger_phrases", "workflow", "pitfalls", "examples"):
        if key in d and (not isinstance(d[key], list) or not d[key]):
            fail(fname, f"{key} 应为非空列表")

    # composition_rules 细则
    cr = d.get("composition_rules", {})
    if isinstance(cr, dict):
        for key in ("product_ratio", "whitespace", "angles"):
            if key not in cr:
                fail(fname, f"composition_rules 缺 {key}")
        angles = cr.get("angles", [])
        if isinstance(angles, list):
            for a in angles:
                if not (isinstance(a, dict) and a.get("angle") and a.get("prompt")):
                    fail(fname, f"angles 项缺少 angle 或 prompt: {a}")

    # workflow 空话检查
    for step in d.get("workflow", []):
        if isinstance(step, str) and any(w in step for w in ("按需调整", "注意效果", "合理搭配")):
            fail(fname, f"workflow 含空话：{step}")

    # keywords 跨模板查重
    for kw in d.get("keywords", []):
        k = kw.lower()
        if k in all_keywords and all_keywords[k] != fname:
            fail(fname, f"keywords 与 {all_keywords[k]} 重复：{kw}")
        all_keywords[k] = fname

    # generation 参数预设（可选字段）
    gen = d.get("generation")
    if gen is not None:
        if not isinstance(gen, dict):
            fail(fname, "generation 应为对象")
        else:
            for key, allowed in (("resolution", {"1k", "2k", "4k"}),
                                 ("format", {"png", "jpeg", "webp"}),
                                 ("quality", {"low", "medium", "high"})):
                value = gen.get(key)
                if value is not None and value not in allowed:
                    fail(fname, f"generation.{key} 非法值：{value}（允许 {'/'.join(sorted(allowed))}）")
            unknown = set(gen) - {"resolution", "format", "quality"}
            if unknown:
                fail(fname, f"generation 含未知键：{sorted(unknown)}（--image/--output-dir/--mode 禁止写入模板）")

    # 非法 variables 命名检查（snake_case；见 SPEC 第四章）
    import re
    raw = json.dumps(d, ensure_ascii=False)
    for var in set(re.findall(r"\{[a-zA-Z-]+\}", raw)):
        if not re.fullmatch(r"\{[a-z_]+\}", var):
            fail(fname, f"占位符 {var} 不符合 snake_case 命名")

print(f"\n共校验 {len(files)} 个模板")
if errors:
    print(f"发现 {errors} 个问题，请修复后重跑")
    sys.exit(1)
print("全部通过 ✓")
