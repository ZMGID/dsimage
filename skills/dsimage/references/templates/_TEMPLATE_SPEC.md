# 模板规范（模板层）

> 模板 = 某个甲方/品牌**可复用的完整出图方案**。
> 情景（`references/scenes/`）只管"一类图怎么拍"。
> 创建模板走 `CREATE_TEMPLATE.md` 的 4 检查点；字段必须符合本规范；写完跑 `python scripts/check_scenes.py`（macOS/Linux 用 `python3`）。

模板分两种，**不要混用执行路径**：

| 类型 | `template_type` | 锁什么 | 适合 |
|---|---|---|---|
| **风格模板** | `style`（缺省也当 style） | 规则：色板、字体、构图、pack 引用情景 | 还没有定稿套图，要按品牌规范生成 |
| **替换模板** | `replace` | **母版套图**：把画面里的品换成新货，未点名的不动 | 已有成品套图，后面只铺不同型号 |

风格模板的文字是创作简报。替换模板的文字是换货说明书，**不要**再写构图占比/色板去让模型重画。

---

## 与情景的关系

- **风格模板**通过 `pack` **引用**情景文件（如 `01-hero-image.json`），每张图的拍摄方法来自被引用的情景；不重复情景内容，只写品牌风格、语言、出哪些图、执行流程
- **替换模板不引用情景**。拍法、构图、字体已经在母版像素里；对不上的角度不要用情景补画
- 执行流程（workflow）属于模板层，情景里没有流程
- 优先级：用户指定 > 模板 JSON > 甲方 `要求.json` > 情景默认 > 脚本默认
- `generation` 默认写在 `要求.json`（`1k`），单品不一样才在模板里覆盖；不要抄情景里的 `2k`；`--size` 用比例；接口返回多大就保存多大，禁止本地升采样

## 文件约定

两种放法，**不要为了一个零散模板特意建文件夹**：

```text
references/templates/
  01-默认电商模板.json      # 零散：JSON 直接放根目录
  NN-替换名.json            # 零散替换
  NN-替换名/                # 零散替换的母版套图
  {甲方id}/                 # 同一甲方多个品才建
    要求.json
    说明.md                 # 可选
    风格/NN-中文名.json
    替换/NN-中文名.json
    替换/NN-中文名/
```

- 零散模板自己写齐 `generation` / 语言 / brand；没有 `要求.json` 可继承
- 甲方 `id` = 文件夹名。不要用 `&`（Windows 会出事）；展示名写在 `要求.json` 的 `name`（如文件夹 `BeautyU`，`name` 为 `BEAUTY&U`）
- 甲方下：风格 → `{甲方}/风格/NN-中文名.json`；替换 → `{甲方}/替换/NN-中文名.json` + 同名母版文件夹
- 命名 `NN-中文名.json`（中文名与 `name`/`id` 一致）；**所在目录独立编号**（根目录、各甲方的 `风格/`、`替换/` 各算各的），接该目录已有最大号；禁止覆盖
- 禁止把 `要求.json` 放在 `templates/` 根目录
- `id` 与文件名中文名一致（`01-默认电商模板.json` → `"id": "默认电商模板"`）
- UTF-8，标准 JSON，中文不转义
- 替换模板的母版图是模板本体，要入库，不要放进 `generated-images/` 或源品文件夹
- 甲方共用写进 `要求.json`；单品差异才写进各模板 JSON

### `要求.json`

| 字段 | 要求 | 说明 |
|---|---|---|
| ★ `id` | 必填 | 与文件夹名一致 |
| ★ `name` | 必填 | 展示名，可含 `&` |
| ★ `language` | 必填 | 图内文字语言 |
| ★ `generation` | 必填 | `{"resolution": "1k", "format": "png", "quality": "high"}` |
| ★ `style` | 必填 | 一两句说清调性、字体、叙事，给 Agent 扫一眼 |
| ○ `brand` | 推荐 | hex 色板；风格模板缺 brand 时从这里补 |
| ○ `notes` | 可选 | 各品都要遵守的杂项 |

模板 JSON 里的同名字段覆盖甲方文件。出图时先读 `要求.json`，再读该品模板。

```json
{
  "id": "BeautyU",
  "name": "BEAUTY&U",
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

`template_type`：`style` | `replace`。不写则视为 `style`。

### 两种都要

| 字段 | 要求 | 说明 |
|---|---|---|
| ★ `id` / `name` | 必填 | 与文件名中文名一致 |
| ★ `template_type` | 推荐 | `style` 或 `replace` |
| ★ `template_meta` | 必填 | 见各类型细则 |
| ★ `keywords` | ≥5 个 | 中英混合，跨情景+模板库查重 |
| ★ `trigger_phrases` | ≥3 个 | 替换模板至少含「使用 dsimage 替换模板：{名}」 |
| ★ `text_rules` | 必填 | 风格：字号/hex/位置。替换：默认冻字 + 允许改的字段 |
| ★ `pack` | 必填 | 风格槽位含 `scene`；替换槽位含 `example` + `product_ref` |
| ★ `workflow` | 5-8 步 | 按类型走对应流程，不要把替换写成「按情景再画」 |
| ★ `generation` | 可省 | 不写则用甲方 `要求.json`；单品不一样才覆盖 |
| ★ `examples` | ≥1 条 | 风格：示例 Prompt。替换：换货执行说明 |
| ★ `supports_image_reference` | 必填 | 替换模板必须为 `true` |
| ○ `pitfalls` | 可选 | 出图后检查 |

### 仅风格模板

| 字段 | 要求 | 说明 |
|---|---|---|
| ○ `style_lock` | 可选 | 不写则按 SKILL.md 从 `template_meta.brand` 现场生成 |
| ★ `template_meta.brand` | 可省 | 颜色必须 hex；不写则用甲方 `要求.json` 的 `brand` |

### 仅替换模板

| 字段 | 要求 | 说明 |
|---|---|---|
| ★ 同名母版文件夹 | 必填 | 每个槽位的 `example` 文件必须真实存在 |
| ★ `text_rules.policy` | 必填 | 固定为未点名不动（C） |
| ★ `text_rules.editable_fields` | 必填 | 数组；没点名就 `[]`。允许值见下 |
| ○ `template_meta.brand` | 可选 | 母版已锁视觉；写了则 hex 仍要合法 |

`editable_fields` 允许：`sku`、`price`、`color_name`、`product_name`、`currency`。用户当场点名的才能写进去；出图时没点名的字段保持母版原文。

---

## 结构化字段细则

### template_meta（风格）

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

### template_meta（替换）

```json
{
  "language": "图内文字语言以母版为准，点名改的字段才换",
  "style_source": "甲方确认的母版套图（登记在同名文件夹）",
  "category": "双肩包"
}
```

- `category` 可选，用于新品类差太远时停下来问，不要硬换
- 不要为了「完整」去编一套 brand hex 再写进 Prompt，那会把替换打回风格生成

### pack（风格）

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

- `images[].scene` 必须是 `references/scenes/` 里真实存在的文件名
- 每个槽位：slot、purpose、scene、ratio、`overrides`（只写与情景默认的差异）
- **`overrides` 是槽位的沉淀容器**；用户指定数量/比例时永远以用户为准

### pack（替换）

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

- `example`：同名文件夹内的母版文件名（`h1.png` / `h1.jpg` / `h1.webp`）
- `product_ref`：这页该用的产品角度，`front` / `back` / `side` / `detail` / `colorway`
- **不要写 `scene`，不要写构图类 `overrides`**。缺某页母版就缺那一槽，禁止用情景补画
- 一品多色：非 `colorway` 槽只用主色产品图；其他颜色只出现在 `product_ref` 为 `colorway` 的槽
- 对不上的角度（母版要背面、这品没有背面图）→ 问用户或跳过该槽，禁止拿正面硬贴

### workflow

- **风格**：读 pack → 建 Campaign Style Lock → 逐张引用情景拼 Prompt → Prompt/jobs.json 写入 `_prompts/` → 生成 → 按情景+模板 pitfalls 检查 → 汇报
- **替换**：读 pack 与母版套图 → 按 `product_ref` 选产品图 → 缺角度/品类差太远先问 → 每张 Prompt 只写「在母版上换品 + 点名才改的字段」→ Prompt/jobs.json 写入 `_prompts/`，jobs 的 `image` 为 `[母版, 产品图]` → 生成 → 对照母版检查未点名元素是否被改 → 汇报
- Prompt 落盘见 SKILL.md「落盘」：禁止写进源品文件夹或成图文件夹

---

## 最小骨架

### 风格模板

```json
{
  "id": "客户模板中文名",
  "name": "客户模板中文名",
  "template_type": "style",
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
      {"slot": "H1", "purpose": "主图", "scene": "01-hero-image.json", "ratio": "1:1"}
    ]
  },
  "workflow": ["读 pack 规划", "建 Style Lock", "逐张引用情景拼 Prompt", "生成", "按 pitfalls 检查", "汇报"],
  "examples": ["示例 Prompt"],
  "supports_image_reference": true
}
```

### 替换模板

```json
{
  "id": "客户替换模板中文名",
  "name": "客户替换模板中文名",
  "template_type": "replace",
  "template_meta": {
    "language": "以母版为准",
    "style_source": "甲方确认母版套图",
    "category": "品类"
  },
  "keywords": ["替换模板", "换品", "replace template"],
  "trigger_phrases": ["使用 dsimage 替换模板：客户替换模板中文名", "按这套样图换货", "只换产品不改版式"],
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
    "读取 pack 与同名文件夹母版套图，禁止改走风格生成",
    "按 product_ref 选产品图；缺角度或品类差太远先问，不要硬贴",
    "每张 Prompt 只写换品 + 本轮点名的字段；未点名不改字",
    "Prompt/jobs.json 写入 _prompts/；image 为 [母版, 产品图]",
    "对照母版检查版式与未点名字段",
    "汇报成图路径与本轮改动的字段"
  ],
  "examples": ["H1：母版 h1.png 上替换产品，其余不动"],
  "supports_image_reference": true,
  "pitfalls": [
    "把替换模板当成风格模板按情景重画",
    "未点名却改了标题/卖点/图标",
    "缺背面参考仍用正面去换背面页"
  ]
}
```

## 完整性校验清单

- [ ] `python scripts/check_scenes.py` 全部通过
- [ ] 零散 JSON 在 `templates/` 根目录；甲方文件夹有 `要求.json`，风格在 `{甲方}/风格/`，替换 JSON+母版在 `{甲方}/替换/`
- [ ] 风格：brand 颜色 hex（模板或甲方文件），pack 每个槽位情景文件存在
- [ ] 替换：`template_type` 为 `replace`，同名文件夹里每个 `example` 存在，pack 无 `scene`，`supports_image_reference` 为 true
- [ ] workflow 是对应类型的完整执行流程（5-8 步）
- [ ] 已在 SKILL.md 匹配表登记
