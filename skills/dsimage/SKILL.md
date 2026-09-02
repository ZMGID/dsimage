---
name: dsimage
description: 电商商品图技能，也能当普通生图工具用。套图走模板（一个文件夹：template.json + 示例图），三种做法：replace（甲方样图换货，脚本直出）、smart（模板给每槽 brief，按品写 prompt）、design（没模板，从零问需求设计一套）；零散一张几张图走 gen。出图走 OpenAI / Grok / Gemini 或兼容网关的图片 API。Use when the user says 使用 dsimage / dsimage, or asks for 电商主图 / 详情页 / 产品图 / 商品图 / 白底图 / 套图 / listing images / product photos / PDP / A+ content, or 生成一张图 / 出张图 / 改图 / 换背景 / 海报 / generate an image / edit this image, or 制作模板 / 创建模板 / 换货 / 换品 / 替换模板 / 按这套样图做.
---

# dsimage

一个模板 = `templates/<名>/` 文件夹：`template.json` + 示例图 `h1.png…` + 可选 `assets/`。
所有命令在本技能目录跑（Windows `python`，macOS/Linux `python3`）：`python scripts/dsimage.py <子命令>`。
Skill 目录有 `.env` 就能出图；没有 → 先读 `SETUP.md`。不要回显 API key。
用户在对话里给了接口地址 / key / 模型名（新的或换的）→ 立刻 `python scripts/dsimage.py setup env --provider … --key …`（换模型 `setup model <名>`）写进 `.env`，以后直接用；不要只在这一次命令里临时用，也不要手改 `.env`。

## 先分流

| 用户给了什么 | 走哪条 | 读 |
|---|---|---|
| 点名了库里的 replace 模板，或「按这套样图把这些品换进去」（样图 + 产品夹） | **replace**：脚本直出，你只选白图、看图、改模板 | `guides/replace.md` |
| 点名了库里的 smart 模板，或「按这个模板/风格，每个品单独写」 | **smart**：脚本给 brief，你按品写 prompts.json，再出 | `guides/smart.md` |
| 只有产品图，没点名模板，要**一套**，没提特殊要求 | **默认模板** `默认电商套图`（smart，9 张 + 白图，pt-BR，有背景，800×800 ≤2MB）：直接 init，走 smart | `guides/smart.md` |
| 品是**童装**（外套 / 卫衣套装 / 夏季套装 / 裤 / 裙 / 睡衣），没点名别的模板 | **`童装套图`**（smart，pt-BR，800×800）：init 后每个品 `set --kind` 标子品类，走 smart | `guides/smart.md` |
| 只有产品图，但提了平台 / 语言 / 风格 / 张数等要求，默认模板对不上 | **design**：先问清需求，建 smart 模板，再走 smart | `guides/design.md` |
| 只要**一张或几张图**：出张图、改这张图、换背景、做张海报 | **gen**：不建模板不建批次，写 prompt 直接出 | `guides/gen.md` |
| 「做个模板」「把这套样图收成模板」 | 建模板 | `guides/make_template.md` |
| 安装 / 配 API / 更新 | | `SETUP.md` |

不确定是 replace 还是 smart：有成品套图 + 只想换货 → replace；只有风格参考或想每个品单独发挥 → smart。问一句，不要自己猜。
一套还是几张：用户说「套图 / 详情页 / 主图全套 / 这些品都做」→ 套；说「一张 / 这张 / 改一下 / 海报」→ gen。5 张以上或以后还会来同类品，建议转 design 建模板。
默认模板还是 design：默认模板是 pt-BR、9 张、有背景、800×800。用户要的语言 / 张数 / 平台跟这个不一样 → design；只是风格微调（换色板、换台面）→ 还用默认模板，写 prompt 时调。
先 `template list` 看库里有什么；用户点名的不在库里就说没有，不要拿别的顶替。

## 开工前跟用户确认（一次问完）

1. 用哪个模板（没点名 → 默认电商套图，童装 → 童装套图；要求对不上 → design）。
2. 源在哪：甲方大文件夹 / 单品夹 / 一张图。成图放哪（不说就默认源夹同级 `XX生成`）。
3. 先出哪个品看效果（不说就第一个）。
4. 这轮有没有要覆盖模板的（语言、画幅、分辩率、交付尺寸、字动不动）。没说 = 按模板。

用户已经把这些说了就直接开做，不要再问。

## 套图三步都一样（gen 不走这里）

```bash
python scripts/dsimage.py init --template <名> --source <甲方夹|单品夹|一张图> [--out <成图根>]
python scripts/dsimage.py run <成图根> --only <SKU>        # 先出一个品
python scripts/dsimage.py run <成图根>                     # 点头后铺全部（已有的跳过；--redo 重出）
python scripts/dsimage.py status <成图根>                  # 进度
python scripts/dsimage.py preview <成图根> --only <SKU>    # 一品拼一张预览图，方便你看
python scripts/dsimage.py deliver <成图根>                 # 模板写了 output.deliver 才有必要
```

`init` 会扫源、拆 SKU、建成图根、写 `_dsimage/batch.json`，最后打印「下一步」清单——照着做。源夹只读。

## 你（Agent）必须亲手做的

1. **选白图**。一个品只有一张图时脚本直接用；多张图时脚本留空并列出候选，你逐张打开看，选那张**白底/抠图的商品图**（不是场景图、不是已合成的主图），`set <成图根> <SKU> --front <路径>`；夹里有背面图再 `--back`。没选的品 `run` 不出。
2. **标品类**。模板有 `product_kinds` 时，不是默认品类的（双肩包模板里混了旅行包）先 `set --kind <键>`，否则会被画成默认品类。
3. **看派生图**。品只有正面图、模板有槽位要背面时，脚本会先用正面图派生一张背面参考再出套图。第一个品先 `derive <成图根> --only <SKU>`，打开 `_dsimage/<SKU>/back.png` 看：是不是同一个产品、颜色/材质/五金对不对。不对 → 改模板 `derive.back` 的 prompt 后 `derive --redo`，或自己找一张 `set --back`。对了再 `run`。铺量时 `run` 会顺手把新派生的列出来，抽查即可。
4. **看成图**。第一个品出完 `preview`，对着模板示例图查：版式/文字/图标是不是原样，产品是不是换成了这个品（形状、颜色、五金、logo）。不对 → 改模板 prompt 或换白图，`run --redo --only <SKU> [--slot H5]`。点头再铺其余。
5. **收口**。整批出完只问一次：这轮改的 prompt 要不要留在模板里；smart 出的效果好要不要 `template freeze` 冻成 replace 模板。

## 跟用户怎么说

- 第一个品出完：给预览图路径 + 你自己看出来的问题（不要只说「出好了」）。让用户点头或指出哪张不对。
- 铺完：给成图根路径、`status` 里完成/失败数、失败的怎么补（同一条 `run`）。
- 报错：把报错原文给用户，说明是哪一步（配置 / 接口 / 模板 / 源），不要自己猜着改 `.env`。
- 用户要改某一页：先说清你改的是模板（会影响以后所有品）还是这个品（`set --vary`），再动手。

## 边界

- 只做**静态图**：套图走模板，零散几张走 `gen`。视频、精修抠图、翻译文案不在这里。
- 一个品的图只认**正面**（必有）和**背面**（可选，没有就派生）。侧面、内部、细节不派生——需要就让模型在槽位 prompt 里自己画，或让用户补图。
- 源夹只读；成图根一个 SKU 一夹（套图 `h1.png…` + 迁进来的白图）；工作文件都在 `_dsimage/`。
- 多个品不要在对话里一个一个做：replace 一条 `run` 全出；smart 每个品的 prompt 可以分给子代理写（一品一个，只写 `prompts.json`），写完主会话一条 `run`。
- 并发、画幅、分辨率、格式、模型都在模板 `output` / `model` 里，用户本轮点名才覆盖，不要自己加旗。
- 分辩率只有 `1k/2k/4k`，接口给多大存多大，不本地放大。交付尺寸用 `deliver`，不要手写 PIL。
- 同一个成图根换模板出：`init` 会提醒，旧图不会自动重出，要 `run --redo`。
- 源根目录下的散图（不在任何品夹里）会被忽略并提醒；要出就挪进品夹。

## 目录

```
skills/dsimage/
  SKILL.md  SETUP.md
  guides/      replace.md  smart.md  design.md  gen.md  make_template.md
  knowledge/   shots.md            26 类电商图的拍法速查（写 prompt 时翻）
  templates/   默认电商套图/  童装套图/（smart）  胜利鹰女款商务背包/  胜利鹰男款商务背包/（replace）
  scripts/     dsimage.py（CLI） core.py  gen_image.py（API）  test_dsimage.py
```
