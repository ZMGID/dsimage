# 模板规范（模板层）

> 模板 = 某个甲方/品牌**可复用的完整出图方案**：品牌风格 + 图内语言 + 图片包结构 + 执行流程。
> 情景（`references/scenes/`）只管"一类图怎么拍"；模板决定"这个品牌出哪些图、按什么流程出"。
> 创建模板走 `CREATE_TEMPLATE.md` 的 4 检查点；字段必须符合本规范；写完跑 `python3 scripts/check_scenes.py`（会同时校验情景库和模板库）。

## 与情景的关系

- 模板通过 `pack` **引用**情景文件（如 `01-hero-image.json`），每张图的拍摄方法来自被引用的情景
- 模板**不重复**情景内容，只写：品牌风格、语言、出哪些图（pack）、执行流程（workflow）
- 执行流程（workflow）属于模板层，情景里没有流程
- 优先级：用户指定 > 模板 > 情景默认 > 脚本默认

## 文件约定

- 位置：`references/templates/`，命名 `NN-中文名.json`（中文名与 `name`/`id` 字段一致），编号**独立于情景**，从 01 起
- `id` 与文件名中文名一致（`01-默认电商模板.json` → `"id": "默认电商模板"`），校验器自动核对
- UTF-8，标准 JSON，中文不转义

## 字段清单（★必填 ○可选）

| 字段 | 要求 | 说明 |
|---|---|---|
| ★ `id` / `name` | 必填 | 文件名一致；中文场景名 |
| ★ `template_meta` | 必填 | 品牌与语言，见下方细则 |
| ★ `keywords` | ≥5 个 | 中英混合，跨情景+模板库查重 |
| ★ `trigger_phrases` | ≥3 个 | 用户最可能说的话 |
| ★ `text_rules` | 必填 | 本品牌的图内文字规则（语言、价格、标题、字号、hex、位置） |
| ★ `pack` | 必填 | 图片包结构，见下方细则 |
| ★ `workflow` | 5-8 步 | **执行流程**：读 pack → 建 Style Lock → 逐张引用情景拼 Prompt → 生成 → 检查 |
| ★ `generation` | 必填 | `{"resolution": "2k", "format": "png"}`，pack 可按槽位覆盖 ratio |
| ★ `examples` | ≥1 条 | 示例 Prompt 或执行记录 |
| ★ `supports_image_reference` | 必填 | bool |
| ○ `style_lock` | 可选 | 固定的 Style Lock 文本；不写则按 SKILL.md 规则从 template_meta.brand 现场生成 |
| ○ `pitfalls` | 可选 | 品牌/行业特有翻车点；出图后连同所引情景的 pitfalls 一起检查。拍法坑回情景，模型通用坑回 SKILL.md |

## 结构化字段细则

### template_meta

```json
{
  "language": "图内文字默认中文，可按用户要求切换",
  "brand": {
    "background": "#F5F5F0",
    "text": "#2D2D2D",
    "accent": "#C8452C",
    "font": "现代无衬线体（SF Pro Display 类），全套只用这一族",
    "tone": "专业、高级、简洁、有销售力"
  },
  "style_source": "风格来源：甲方参考 PDF / 内置默认"
}
```

- `brand` 全部颜色必须 hex；`tone` 是甲方的原话诉求翻译后的短语
- `language` 决定图内文字语言；Prompt 骨架仍用英文书写

### pack（图片包结构）

```json
{
  "default_count": "3 张（用户指定数量时以用户为准）",
  "images": [
    {
      "slot": "H1",
      "purpose": "主图：产品突出 + 价格信息",
      "scene": "01-hero-image.json",
      "ratio": "1:1",
      "overrides": {
        "layout": "标题左上、产品居中偏上、价格左下，元素位置每张一致",
        "price_block": "44pt 强调色 hex，左下角，仅确认报价后渲染"
      }
    }
  ]
}
```

- `images[].scene` 必须是 `references/scenes/` 里真实存在的文件名，校验器会检查
- 每个槽位：slot 编号、purpose（一句话意图）、scene（拍法来源）、ratio（画幅）、`overrides`（品牌对这张图的特化）
- **`overrides` 是槽位的沉淀容器**：key 为要覆盖的方面（layout / product_ratio / background / callouts / price_block / condition / forbidden…自由命名），value 写具体要求；只写与情景默认的**差异**，不要把情景内容抄一遍
- 后续优化落点：品牌对某张图不满意 → 改该槽位 `overrides`；某类图通用的坑 → 改所引情景的 `pitfalls`/`composition_rules`
- 用户指定数量/比例时**永远以用户为准**，pack 只是缺省方案

### workflow（执行流程——流程归模板）

- 5-8 步，标准结构：读 pack 规划 → 建 Campaign Style Lock（用 template_meta.brand 的 hex）→ 逐张"读引用情景 → 情景骨架 + 品牌 hex + text_rules 拼 Prompt" → 调 gen_image.py（--image 带参考图）→ 按情景 pitfalls + 本模板 pitfalls 检查 → 汇报
- 这是"原来 Skill 里的流程"的落点：每个模板可以有自己的流程特化（如报价表模板规定价格必须人工确认）

## 最小骨架（复制即用）

```json
{
  "id": "客户模板中文名",
  "name": "客户模板中文名",
  "template_meta": {
    "language": "图内文字语言",
    "brand": {"background": "#xxxxxx", "text": "#xxxxxx", "accent": "#xxxxxx", "font": "字体族", "tone": "调性短语"},
    "style_source": "甲方参考材料说明"
  },
  "keywords": ["中文词", "english"],
  "trigger_phrases": ["用户会说的话"],
  "text_rules": {"headline": "≤10 字 28-36pt #2D2D2D", "price": "44pt #C8452C 左下角"},
  "pack": {
    "images": [
      {"slot": "H1", "purpose": "主图", "scene": "01-hero-image.json", "ratio": "1:1"}
    ]
  },
  "workflow": ["读 pack 规划", "建 Style Lock", "逐张引用情景拼 Prompt", "生成", "按 pitfalls 检查", "汇报"],
  "generation": {"resolution": "2k", "format": "png"},
  "examples": ["示例 Prompt"],
  "supports_image_reference": true
}
```

## 完整性校验清单

- [ ] `python3 scripts/check_scenes.py` 全部通过（含 pack 引用的情景文件存在性检查）
- [ ] brand 颜色全部 hex，语言明确
- [ ] pack 每个槽位都有真实存在的情景引用
- [ ] workflow 是完整执行流程（5-8 步）
- [ ] 已在 SKILL.md 匹配表登记
