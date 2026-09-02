---
name: dsimage
description: E-commerce visual creation skill. Turns product photos plus a one-line request into complete, conversion-optimized image sets using 26 shooting scenes, with Campaign Style Lock for visual consistency. Generates via Codex built-in imagegen or a configured OpenAI-compatible image API. Also builds reusable client templates from brand materials. A template has one lock: rules (generate from brand rules) or master (swap the product onto a locked page set). Use when the user says 使用 dsimage / 使用dsimage / dsimage, or asks for 电商主图 / 详情页 / 产品图 / 商品图 / 白底图 / listing images / product photos / PDP / A+ content / social or ad creatives, or 制作模板 / 创建模板 / 使用 dsimage 模板 / 替换模板 / 换品 / 换货 / 快速换货 / 同类快换 / 快速替换.
---

# dsimage

对人只谈三件事：**出一套** → **铺很多套** → **收成模板**。开口带「使用 dsimage」。

**出图时这些已经定好。** 命令在本技能目录跑（Windows：`python`）。Skill 目录有 `.env` = 生图 API 已配好，脚本自己读、自己带 User-Agent，加 `--run` 就会出。Grok：一张参考走 `image`，两张走 `images` 并标 `<IMAGE_0>` / `<IMAGE_1>`。你做的是看图选编号和白图。翻车把报错原文给人，同一条命令重跑。不要暴露或回显 API key。

分流看命中模板的 `lock`，不要让用户挑两种模板：

| 材料和措辞 | 怎么干 |
|---|---|
| 替换模板 / 只换货 / 版式别动 / 样板套图 + 产品图 / `lock=master` | **替换模板**：看图选白图，`--pilot` 出一套，点头再 `--blast`。不要派品工人写 Prompt。 |
| 调性 / PDF / 色板 / 情景 / `lock=rules` | **按规则画**。2 个及以上品才派工人写 Prompt。 |
| 制作模板 / 创建模板 | 读 `CREATE_TEMPLATE.md` |
| 安装 / 配 API | 读 `SETUP.md` |

含糊才问：成品主图页 + 产品图 → 按替换模板做，字默认冻。只有色板/情绪板、没有成品页 → 按规则画。用户已经给了模板名、源夹、成图夹、先出哪几个 → 按他说的开做。

出图前跑一次匹配，把 stdout 原样给用户：

```bash
python scripts/match_pack.py --query "<用户原话，不要改写>"
```

回 `1` / `2` / `3` 换方案。没有就按第 1 个做。点名不在库里时按脚本给出的第 1 名走，不要改成白底主图充数。要换货但库里没有 `lock=master` → 脚本会说明；有样板文件夹就加 `--masters`，不要假装在换。

---

## 替换模板（lock=master）

锁的是已画好的母版套图。每个编号对着同一套图换货。字、图标、版式、背景默认不动。单品和大文件夹都走这一套。

共用提示词就是这一句。各槽差别在图，不给每槽另写一版：

```text
Replace only the product in the first image with the product from the second image. Keep layout, text, icons, and background unchanged.
```

- 一品一张白图，每槽都用这一张。夹里混着白底和场景图时，看画面只选白底商品图。
- 不要因文件名没有「背面」就跳槽。不要派品工人。不要问货号/改价（字全冻）。要改字：`--set-prompt` 或 `--set-slot-prompt`。
- `--size` 传比例；`--resolution` 只有 `1k` / `2k` / `4k`。交付走 `--deliver`。
- `lock=master` 的模板或 `--masters` 时，`--init` 自动走换货，不必再加别的旗。

用户说先看哪几个编号，就先出那几个的**整套**。没点头再铺其余。

1. 打开要先出的编号，选定那张白图。对不上就问。
2. 建批次并出第一套：

```bash
python scripts/queue_pack.py --init --source "<甲方大文件夹>" --template "<匹配到的模板 JSON>" --output "<成图根，用户给了就用>" --pilot "<第一个编号>"
python scripts/queue_pack.py --queue "<成图根>/_prompts/批次.json" --pilot "<第一个编号>" --run
```

库里没有母版模板、用户给了样板夹时才加 `--masters "<样板文件夹>"`。先看两个：出完第一个再 `--pilot "<第二个编号>" --run`。

3. 把成图路径给用户。要改：`--set-prompt "新的一句"` 或 `--set-slot-prompt H5 "该槽的一句"` 或换白图，再 `--pilot --run`（不要 `--skip-existing`）。
4. 点头之后，其余编号同样看图选白图，再铺：

```bash
python scripts/queue_pack.py --queue "<成图根>/_prompts/批次.json" --blast --run --skip-existing
```

5. 批次里写了交付尺寸再 `--deliver`。没有就结束。

用户没说的旗不要加。可选：`--resolution 1k|2k|4k`，`--output-size 宽x高` 或 `--max-px` / `--max-bytes`，`--inspect-every N`，`--category "<品类>"`。

出完对照母版查：版式、图标、未点名的字、产品是不是换成新货。翻车沉淀到该槽母版或 `editable_fields` / pitfalls，不要写进情景。

---

## 甲方文件夹（默认读存）

甲方给一个大文件夹。只读，不要改里面的文件。替换模板和按规则画都走这一套。用户另起成图根名才覆盖。

**读**

1. 下面是编号夹：可能一个编号一个夹（`V26025`），也可能几个编号一个夹（`V26007-V26010`）。
2. 打开夹看图（文件名通常不带颜色，也基本没有正面/背面）：
   - **一品一张图**：常态。那张就是该品白图。
   - **一夹多品**：文件名带着不同商品编号。按文件名编号拆开，一品一套、一品仍是一张图。不要把整个号段夹当成一个品。
   - **白图和场景图混在一起**：看画面，只选白底/抠图商品图。场景图、已合成的主图不当白图。
3. 夹名是号段、文件名却拆不开时停下问。不要靠文件名猜颜色。
4. 品的名字 = **商品编号**（`V26007`），不是号段夹名，也不要改成英文 slug。

**存**

5. 在甲方大文件夹**同级**新建成图根：夹名以「系列」结尾则把「系列」换成「生成」（`VE男包系列` → `VE男包生成`）；否则在原名后加「生成」。不要建在甲方夹里面，不要用 `generated-images/` 顶替这批。
6. 成图根里 **一个商品编号一个文件夹**。禁止输出一个 `V26007-V26010/`。
7. 每个编号夹：模板套图（`h1.png`…）+ **一张白图**（从甲方迁来的那张产品图，不是再生成一张）。
8. Prompt / `jobs.json` 只放成图根 `_prompts/{商品编号}/`，不要和成图混放，也不要写进甲方源夹。

```text
VE男包系列/                 ← 甲方源（只读）
  V26007-V26010/
  V26026/
VE男包生成/                 ← 同级默认
  V26007/h1.png … + 白图
  _prompts/批次.json
```

`--init --source` 直接指向甲方大文件夹。脚本按编号拆品。不要先手拆再 `--init`。

**完成：每个商品编号有自己的成图夹（套图 + 一张白图）；甲方源夹未被改写。**

单品、未声明批量：成图 `generated-images/<slug>-pdp/`，Prompt `generated-images/_prompts/<slug>/`。`jobs.json` 的 `output_dir` 写成 `../../<slug>-pdp`。

---

## 按规则画（lock=rules / 情景）

模板大于情景。模板写了的一律用模板，不要跟情景折中。只命中情景、没有模板时，才以情景为准。

| 高 → 低 | 听谁 |
|---|---|
| 1 | 用户本轮 |
| 2 | 模板 JSON（pack / text_rules / style_lock / brand / generation） |
| 3 | 本文件夹 `要求.json`（该模板文件夹名须在 `templates` 里） |
| 4 | 所引情景 |
| 5 | SKILL / 脚本 |

`--size` 用该槽比例。`--resolution` 用户点了用用户的，否则甲方或模板，都没有才 `1k`，不要从情景抄 `2k`。接口返回多大就保存多大，禁止本地升采样。

每张 Prompt 开头必须是同一段 Style Lock。模板已有 `style_lock` 则原样用；没有才用：

```text
Campaign Style Lock: consistent premium ecommerce visual system across the entire image set; fixed palette of clean off-white background, deep charcoal text, one product-matched accent color, and one soft secondary accent; neutral-cool studio lighting; modern geometric sans-serif headline placeholders only; consistent rounded rectangular info labels; consistent thin-line icon style; clean high-end product photography mixed with minimal infographic elements; stable product scale and placement; generous whitespace; no color palette changes, no mixed fonts, no random backgrounds, no inconsistent lighting, no mismatched icon styles.
```

颜色用 hex。产品占比和留白写出数字。否定清单写具体禁止项。图内文字短；中文用「」包裹。

一品多色：锁一个主色出套图；其他颜色只出现在一张配色合集。用户明确要求「每个颜色出一套」才按色分套。

**2 个及以上品**：主会话只调度，不要在本对话按品串行。口头要求只问一次，写入 `_prompts/批次.json` 的 `only` / `skip` / `notes`。

```bash
python scripts/queue_pack.py --init --source "<甲方大文件夹>" --template "<命中的模板 JSON>"
python scripts/queue_pack.py --queue "<成图根>/_prompts/批次.json" --next
python scripts/queue_pack.py --queue "<成图根>/_prompts/批次.json" --run --skip-existing
```

`--next` 一次派最多 3 个品工人（一品一工人，只写 Prompt）。有 API：工人不要自己 `--batch`，调度一次 `--run`（默认并发 32）。宿主生图：工人写完 Prompt 后自己派槽位，同时最多 2 路。

单品多图：Prompt 写入该品 `_prompts/` 后一次 `python scripts/gen_image.py --batch <该品 _prompts>/jobs.json`。没有 API、走宿主生图：2 张及以上立刻派平级子代理，单品同时最多 4 路。

缺价格/尺寸/卖点先问；不补则按假设出图并列出假设，不要跳槽。认证/评分/销量用示意占位。

**一套品出完收口**（多品整批出完再问一次）：定制 `lock=rules` 问要不要对照改模板；只用了情景或默认电商模板问要不要建模板（说要 → `CREATE_TEMPLATE.md`，先建夹、先拷图、再写 JSON）。`lock=master` 问母版要不要对照刚出的图换一张。

---

## 匹配

「使用 dsimage 模板：某某」查模板匹配表。命中后再读 JSON 的 `lock`。「替换模板：某某」仍当点名，并按换货意图匹配。只读取第 1 名方案用到的情景/模板。

脚本固定输出 3 名，第 1 个最优。用户回 2 或 3 则改用该名次，不要混用两套 pack。

新建或修改情景 / 模板：规范在 `references/scenes/_SCENE_SPEC.md` 与 `references/templates/_TEMPLATE_SPEC.md`。写完跑 `python scripts/check_scenes.py`，并在下方匹配表登记。

### 情景匹配表

| 触发词 | 情景文件 |
|---|---|
| 白底图, 主图, hero image, packshot | `01-hero-image.json` |
| 场景图, 生活图, lifestyle | `02-lifestyle-scene.json` |
| 平铺图, flat lay, 俯拍 | `03-flat-lay.json` |
| 细节图, 微距, macro, 特写 | `04-detail-macro.json` |
| 海报, poster, banner, 促销 | `05-poster-banner.json` |
| 社交媒体, 小红书, Instagram, TikTok | `06-social-media.json` |
| UGC, 买家秀, GRWM | `07-ugc-style.json` |
| 模特, model, 人物展示 | `08-model-showcase.json` |
| 对比, before after, 前后 | `09-before-after.json` |
| 包装, packaging, 礼盒 | `10-packaging.json` |
| 信息图, A+, 详情页, PDP | `11-infographic.json` |
| 创意, 概念, creative | `12-creative-concept.json` |
| 尺寸, 规格, 使用步骤 | `13-size-spec.json` |
| 套装, 组合, bundle | `14-multi-product.json` |
| 直播, livestream | `15-livestream.json` |
| 试穿, 融入, try on | `16-try-on-virtual.json` |
| 拆解图, 爆炸图, exploded view | `17-exploded-view.json` |
| 隐形模特, ghost mannequin, 3D服装 | `18-ghost-mannequin.json` |
| 多角度, 网格, grid, 多色展示 | `19-multi-angle-grid.json` |
| 杂志, 封面, editorial, magazine | `20-magazine-editorial.json` |
| 季节, 四季, campaign, 春夏秋冬 | `21-seasonal-campaign.json` |
| 奢华, 氛围, 烟雾, luxury, atmospheric | `22-luxury-atmospherics.json` |
| 设备模型, 界面, mockup, SaaS, APP | `23-device-mockup.json` |
| 店铺, 门面, 空间, storefront, 实体店 | `24-storefront.json` |
| 运动, 健身, sports, fitness | `25-sports-campaign.json` |
| 箱包功能图, 背包结构, 拉杆带, 防盗袋, bag feature proof | `26-bag-feature-proof.json` |

### 模板匹配表

| 触发词 | 模板文件 |
|---|---|
| 使用 dsimage 模板：默认电商模板, 默认模板, default template, 通用电商主图, 起步套图 | `templates/01-默认电商模板/01-默认电商模板.json` |
| 使用 dsimage 模板：箱包单品报价模板, 箱包单品报价, 箱包报价表, BEAUTY&U风格, bag quote sheet, 风格四 | `templates/BeautyU/01-箱包单品报价模板/01-箱包单品报价模板.json` |

---

## 常见翻车点

| 翻车 | 防护 |
|---|---|
| 替换模板却派品工人写长 Prompt | `--pilot` 出一套，点头再 `--blast` |
| 因缺「背面」文件名跳槽 | 一品一张白图，每槽都用这一张 |
| 有母版却按情景重画 | 只换品；`jobs.image` = [母版, 产品图] |
| 未点名却改了母版上的字 | 只有本轮点名的字段才改 |
| 多品在同一对话里一个一个做 | 替换模板 `--blast`；按规则画 `--next` 一品一工人 |
| 点名的模板不在库里却出一张白底主图 | 跑 match_pack.py，按第 1 名做 |
| 出套图现测 API | 有 `.env` 加 `--run`；Grok 一张 `image`、两张 `images` |
| 出完再用 PIL 手压成固定像素 | `--deliver`，尺寸按本轮填 |
| Prompt 写进品文件夹或项目根 | 只写入 `_prompts/` |
| 中文字笔画错 / 品牌色漂移 | 放大核对；颜色用 hex |
