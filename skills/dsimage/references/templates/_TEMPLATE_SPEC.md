# 模板规范（模板层）

> 模板 = 某个甲方/品牌**可复用的完整出图方案**。只有一种模板。
> 情景（`references/scenes/`）只管"一类图怎么拍"。
> 创建模板走 `CREATE_TEMPLATE.md`（先建文件夹、先拷图、再写 JSON）；字段必须符合本规范；写完跑 `python scripts/check_scenes.py`（macOS/Linux 用 `python3`）。

用一个参数决定怎么出图，不要再拆成两套模板、两个文件夹、两张匹配表：

| `lock` | 锁什么 | 适合 |
|---|---|---|
| `rules`（缺省） | 规则：色板、字体、构图、pack 引用情景 | 还没有定稿套图，按品牌规范生成 |
| `master` | 模板文件夹里的母版套图；只换产品，未点名的不动 | 已有成品套图，后面铺不同型号 |

`lock=rules` 的文字是创作简报。`lock=master` 的文字是换货说明书，不要再写构图占比/色板去让模型重画。

旧字段 `template_type: style|replace` 仍能读（style→rules，replace→master）。新文件只写 `lock`。

---

## 与情景的关系

情景是一类图的**缺省拍法**。模板是这一套图的完整方案。**模板里写了的大于情景**，不要折中。

- `lock=rules`：pack **引用**情景，拿 `prompt_template` 当骨架。占比、留白、文字、色板、比例、分辨率：模板 / 槽位 `overrides` 写了就用模板的；没写才用情景
- `lock=master`：**不引用情景**。拍法已经在母版像素里；对不上的角度不要用情景补画
- 执行流程（workflow）属于模板层，情景里没有流程
- 品牌专用规则写进模板（或甲方 `要求.json`），不要改情景去迁就某一个甲方
- 优先级：用户本轮 > 模板 JSON > 甲方 `要求.json` > 情景缺省 > SKILL / 脚本默认
- `generation` 默认写在 `要求.json`（`1k`），单品不一样才在模板里覆盖；不要抄情景里的 `2k`；`--size` 用比例，且必须和母版/目标画布一致，禁止用别的比例生成再变形压；接口返回多大就保存多大，禁止本地升采样。可选 `generation.deliver`：`max_px`（长边上限，保持比例）、`width`/`height`（精确画布，比例必须对得上）、`max_bytes`（体积上限，整数）。快跑出完后 `--deliver` 按这个压；交付像素不是生图档。

## 文件约定

**一个模板一个文件夹。** JSON 文件名 = 文件夹名。图和 JSON 放在一起，整夹复制就能分享或挪位置，不要另建 `风格/`、`图片/`。

```text
references/templates/
  01-默认电商模板/
    01-默认电商模板.json    # 零散；至少一张示例图（建议 h1.png）
    h1.png
  NN-中文名/
    NN-中文名.json
    h1.png
  {甲方id}/                 # 同一甲方多个品才建
    要求.json               # 共用要求；templates 列出下面的文件夹名
    说明.md                 # 可选
    NN-中文名/
      NN-中文名.json
      h1.png
```

| 谁 | 图怎么放 | 何时必有 |
|---|---|---|
| `lock=master` | 每槽母版和 JSON 同文件夹；`pack.images[].example` 是文件名 | **必有，齐套。** 缺任何一槽就不能写成 `lock=master`，也不能出图 |
| `lock=rules` | 至少 1 张示例图（建议 H1 / `h1.png`），对应槽写 `example`。出图用用户产品图，这些图只作版式/调性参考 | **必有。** 没有示例图不准登记。不要拿示例图当母版换货 |
| 用户产品图 | 留在用户给的路径 / `data/` | 出图时引用，禁止拷进 `templates/` |
| 成图 | `generated-images/`（单品）或同级 `{名}生成/`（批量） | 禁止写回 `templates/` |

不要建 `风格/`、`替换/`。编号接**该目录**（`templates/` 根下的零散包，或某个甲方文件夹）已有最大号。

- 零散模板自己写齐 `generation` / 语言 / brand；没有 `要求.json` 可继承
- 甲方 `id` = 文件夹名。不要用 `&`（Windows 会出事）；展示名写在 `要求.json` 的 `name`
- 命名：文件夹 `NN-中文名/`，内含 `NN-中文名.json`（中文名与 `name`/`id` 一致）；禁止覆盖
- 禁止把 `要求.json` 放在 `templates/` 根目录
- UTF-8，标准 JSON，中文不转义
- 母版图 / 示例图只进该模板文件夹，要入库；不要放进 `generated-images/` 或源品文件夹。没有真图不要编一张充数
- 分享或移动：拷整个 `NN-中文名/`（必须含示例图或母版）；拷整个 `{甲方}/` 才带得走 `要求.json`。只把甲方里的一份丢到根下当零散时，先把 `generation` / 语言 / brand 写进该模板 JSON
- `要求.json` **对应本文件夹里的模板包**：`templates` 列出那些文件夹名（不要带 `.json`），必须与磁盘上的模板目录一一对应。共用的语言 / 分辨率 / 色板写在 `要求.json`；单品差异才写进各模板 JSON，不要把共用项再抄一遍

### `要求.json`

本文件是本文件夹里那些模板包的共用要求，不是空挂的甲方名片。

| 字段 | 要求 | 说明 |
|---|---|---|
| ★ `id` | 必填 | 与文件夹名一致 |
| ★ `name` | 必填 | 展示名，可含 `&` |
| ★ `templates` | 必填 | 本文件夹内模板目录名（不要带 `.json`），必须与磁盘上的目录一一对应 |
| ★ `language` | 必填 | 图内文字语言 |
| ★ `generation` | 必填 | `{"resolution": "1k", "format": "png", "quality": "high"}`。可选 `deliver`: `max_px` / `max_bytes`，或精确画布 `width` + `height` + `ratio` |
| ★ `style` | 必填 | 一两句说清调性、字体、叙事 |
| ○ `brand` | 推荐 | hex 色板；`lock=rules` 且模板没写 brand 时从这里补 |
| ○ `notes` | 可选 | 这些模板都要遵守的杂项 |

出图时：先确认命中的模板文件夹名在 `templates` 里，再读 `要求.json`，再读该模板 JSON。模板里的同名字段覆盖本文件。不在列表里的包不要拿这份要求去套。

```json
{
  "id": "BeautyU",
  "name": "BEAUTY&U",
  "templates": ["01-箱包单品报价模板"],
  "language": "图内文字默认葡萄牙语（巴西）",
  "generation": {"resolution": "1k", "format": "png", "quality": "high"},
  "style": "专业商务、产品主导、固定字体和叙事顺序",
  "brand": {
    "background": "#F3F3F3",
    "text": "#111111",
    "accent": "#D6B77A"
  }
}
```

---

## 字段清单

`lock`：`rules` | `master`。不写则视为 `rules`。

### 两种都要

| 字段 | 要求 | 说明 |
|---|---|---|
| ★ `id` / `name` | 必填 | 与文件名中文名一致 |
| ★ `lock` | 推荐 | `rules` 或 `master` |
| ★ `template_meta` | 必填 | 见各 lock 细则 |
| ★ `keywords` | ≥5 个 | 中英混合，跨情景+模板库查重 |
| ★ `trigger_phrases` | ≥3 个 | 至少含「使用 dsimage 模板：{名}」 |
| ★ `text_rules` | 必填 | rules：字号/hex/位置。master：默认冻字 + 允许改的字段 |
| ★ `pack` | 必填 | rules 槽位含 `scene`，至少一槽含 `example` 且文件存在；master 每槽含 `example` + `product_ref` 且文件存在 |
| ★ `workflow` | 5-8 步 | 按 lock 走对应流程 |
| ★ `generation` | 可省 | 不写则用甲方 `要求.json` |
| ★ `examples` | ≥1 条 | rules：示例 Prompt。master：换货执行说明 |
| ★ `supports_image_reference` | 必填 | `lock=master` 必须为 true |
| ○ `pitfalls` | 可选 | 出图后检查 |

### 仅 `lock=rules`

| 字段 | 要求 | 说明 |
|---|---|---|
| ○ `style_lock` | 可选 | 不写则按 SKILL.md 从 `template_meta.brand` 现场生成 |
| ★ 至少一张示例图 | 必填 | 建议 H1 写 `example` 并放入 `h1.png`。出图不拿它换货 |
| ★ `template_meta.brand` | 可省 | 颜色必须 hex；不写则用甲方 `要求.json` 的 brand |

### 仅 `lock=master`

| 字段 | 要求 | 说明 |
|---|---|---|
| ★ 模板文件夹内的母版图 | 必填 | 每个槽位的 `example` 文件必须真实存在。没有齐套母版就不要写成 `lock=master` |
| ★ `text_rules.policy` | 必填 | 固定为未点名不动 |
| ★ `text_rules.editable_fields` | 必填 | 数组；没点名就 `[]` |
| ○ `template_meta.brand` | 可选 | 母版已锁视觉；写了则 hex 仍要合法 |

`editable_fields` 允许：`sku`、`price`、`color_name`、`product_name`、`currency`。用户当场点名的才能写进去；出图时没点名的字段保持母版原文。

---

## 结构化字段细则

### template_meta（rules）

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

### template_meta（master）

```json
{
  "language": "图内文字语言以母版为准，点名改的字段才换",
  "style_source": "甲方确认的母版套图（登记在本模板文件夹）",
  "category": "双肩包"
}
```

- 有甲方时：`language` / `brand` 写在 `要求.json`，模板 `template_meta` 只留本套差异（如 `style_source`），不要再抄一份
- `category` 可选，新品类差太远时停下来问
- 不要为了完整去编一套 brand hex 再写进 Prompt，那会把换货打回按规则重画

### pack（rules）

```json
{
  "default_count": "3 张（用户指定数量时以用户为准）",
  "images": [
    {
      "slot": "H1",
      "purpose": "主图：产品突出 + 价格信息",
      "scene": "01-hero-image.json",
      "example": "h1.png",
      "ratio": "1:1",
      "overrides": {
        "layout": "标题左上、产品居中偏上、价格左下，元素位置每张一致"
      }
    }
  ]
}
```

- `images[].scene` 必须是 `references/scenes/` 里真实存在的文件名
- 至少一槽写 `example` 并放入对应文件（建议 H1 / `h1.png`）。其余槽有现成样张也可以写
- `overrides` 是槽位的沉淀容器，用来覆盖所引情景的默认构图/文字；只作用于该槽
- 模板 `text_rules` / `style_lock` / `generation` / 槽位 `ratio` 同样覆盖情景同名字段
- 出图参考图用用户产品图。示例图给 Agent 看版式，不要当母版去换货

### pack（master）

```json
{
  "default_count": "与母版张数一致",
  "images": [
    {
      "slot": "H1",
      "purpose": "产品总览兼报价主图",
      "example": "h1.png",
      "product_ref": "front",
      "ratio": "1:1"
    }
  ]
}
```

- `example`：本模板文件夹内的母版文件名
- `product_ref`：`front` / `back` / `side` / `detail` / `colorway`
- 不要写 `scene`，不要写构图类 `overrides`
- 非 `colorway` 槽只用主色产品图
- 缺角度：换货长 Prompt 问用户或跳过，禁止拿正面硬贴；快速换货一品一张白图，每槽都用，不要因文件名没有「背面」就跳

### workflow

- **rules**：读 pack → 建 Campaign Style Lock → 逐张引用情景拼 Prompt → `_prompts/` → 生成 → 检查 → 汇报
- **master**：读 pack 与母版 → Agent 看图选定该品白图 → 单品或要改字用换货 Prompt；数量多且冻字走 `FAST_SWAP.md`（看图出原型，点头后再铺）→ `_prompts/`，`image: [母版, 产品图]` → 对照母版检查 → 汇报

---

## 最小骨架

### lock=rules

```json
{
  "id": "客户模板中文名",
  "name": "客户模板中文名",
  "lock": "rules",
  "template_meta": {
    "language": "图内文字语言",
    "brand": {"background": "#xxxxxx", "text": "#xxxxxx", "accent": "#xxxxxx", "font": "字体族", "tone": "调性短语"},
    "style_source": "甲方参考材料说明"
  },
  "keywords": ["中文词", "english"],
  "trigger_phrases": ["使用 dsimage 模板：客户模板中文名"],
  "text_rules": {"headline": "≤10 字 28-36pt #2D2D2D", "price": "44pt #C8452C 左下角"},
  "pack": {
    "images": [
      {"slot": "H1", "purpose": "主图", "scene": "01-hero-image.json", "example": "h1.png", "ratio": "1:1"}
    ]
  },
  "workflow": ["读 pack 规划", "建 Style Lock", "逐张引用情景拼 Prompt", "生成", "按 pitfalls 检查", "汇报"],
  "examples": ["示例 Prompt"],
  "supports_image_reference": true
}
```

### lock=master

```json
{
  "id": "客户模板中文名",
  "name": "客户模板中文名",
  "lock": "master",
  "template_meta": {
    "language": "以母版为准",
    "style_source": "甲方确认母版套图",
    "category": "品类"
  },
  "keywords": ["换品", "母版", "replace", "swap product"],
  "trigger_phrases": ["使用 dsimage 模板：客户模板中文名", "按这套样图换货", "只换产品不改版式"],
  "text_rules": {
    "policy": "未点名的文字、图标、版式、背景一律保持母版原样；只有 editable_fields 且用户本轮给出新值时才改",
    "editable_fields": ["sku", "price"]
  },
  "pack": {
    "images": [
      {"slot": "H1", "purpose": "主图", "example": "h1.png", "product_ref": "front", "ratio": "1:1"}
    ]
  },
  "workflow": [
    "读取 pack 与本文件夹母版套图，禁止改走按规则重画",
    "按 product_ref 选产品图；缺角度或品类差太远先问，不要硬贴",
    "每张 Prompt 只写换品 + 本轮点名的字段；未点名不改字",
    "Prompt/jobs.json 写入 _prompts/；image 为 [母版, 产品图]",
    "对照母版检查版式与未点名字段",
    "汇报成图路径与本轮改动的字段"
  ],
  "examples": ["H1：母版 h1.png 上替换产品，其余不动"],
  "supports_image_reference": true,
  "pitfalls": [
    "有母版却按情景重画",
    "未点名却改了标题/卖点/图标",
    "缺背面参考仍用正面去换背面页",
    "快速换货因文件名没有背面而跳槽"
  ]
}
```

## 完整性校验清单

- [ ] `python scripts/check_scenes.py` 全部通过
- [ ] 零散模板在 `templates/NN-名/NN-名.json`；甲方文件夹有 `要求.json`，其 `templates` 与文件夹内模板目录名一一对应
- [ ] `lock=rules`：brand hex（模板或甲方文件），pack 每个槽位情景文件存在，至少 1 张示例图且有槽位 `example` 指向它
- [ ] `lock=master`：本文件夹里每个 `example` 存在（齐套，缺一槽就不要用 `lock=master`），pack 无 `scene`，`supports_image_reference` 为 true
- [ ] 已在 SKILL.md 模板匹配表登记
