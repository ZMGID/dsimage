---
name: dsimage
description: E-commerce visual creation skill. Turns product photos plus a one-line request into complete, conversion-optimized image sets using 26 shooting scenes, with Campaign Style Lock for visual consistency. Generates via Codex built-in imagegen or a configured OpenAI-compatible image API. Also builds reusable client templates from brand materials. Use when the user says 使用 dsimage / 使用dsimage / dsimage, or asks for 电商主图 / 详情页 / 产品图 / 商品图 / 白底图 / listing images / product photos / PDP / A+ content / social or ad creatives, or 制作模板 / 创建模板 / 使用 dsimage 模板.
---

# dsimage Skill

当用户需要视觉策略、图片 Prompt、商品主图、营销图、社媒图、广告图、电商 PDP 视觉，或要求直接 AI 生图时，使用这个 Skill。

这个 Skill 有两种模式：

1. **Brief / Prompt 模式**：只输出视觉简报和可执行图片 Prompt。
2. **Generate 模式**：当用户明确要求"生图、生成图片、出图、render image"时，先输出最终 Prompt，再调用生图。

不要暴露、索要、写入、提交或回显真实 API key。生图 API 不是必须的：Codex 账号登录即可用原生生图；需要更高额度/并发时可再配 API，两者可同时开，不是二选一。

---

## 核心流程

**本 Skill 只规定通用流程。每个场景具体怎么拍、占多少、写什么字、注意什么，全部以命中的情景文件为准。**

1. 判断任务类型，按下方**情景匹配表**找到情景文件。
2. **完整读取命中的情景文件**，之后一切按情景内容执行：
      - `composition_rules` — 产品占比、留白、角度（照做）
   - `text_rules` — 图内文字规则（照做）
   - `pitfalls` — 出图后按这个清单检查
   - `anti_ai_tips` — 有则必须应用
3. 价格、尺寸、卖点、文案等缺了先问一轮；用户不补或说先出图，则按合理假设继续，槽位不跳过。产品外形以参考图为准。**源图文件名要参与生图**（见「源图文件名」）：型号、哪张当正面/背面参考，都从文件名读。认证/评分/销量不要写成已核实事实，可用示意占位。
4. 多图任务：先建立 **Campaign Style Lock**（见下文），原样放进每张 Prompt 开头。
5. 商品/营销任务：先做**转化驱动力诊断**（见下文）。
6. 逐张写 Prompt：Style Lock → 情景 `prompt_template` 骨架（替换 `{variables}`）→ 按需套用 `variants` / `category_tips` → 按通用规则收尾。
7. Generate 模式：按下方**出图通道**选路；用户提供了产品图必须带上参考图。走脚本时多图用 `--batch`；走 Codex/宿主原生生图时多图**积极派子代理并行**（见「多图执行规则」）。用户丢来「大文件夹 + 每子文件夹一个品」时，按「批量品目录」落盘，不要写进源文件夹。**命令参数优先级**：用户显式指定 > 命中模板的 `generation` / 槽位 `ratio` > 情景 `generation` / `default_ratio`。`--size` 用比例（`1:1`），不要写死 `1024x1024` 或 `2048x2048`。未特别要求 2k 时用模板默认 `1k`，不要从情景抄 `2k`。接口返回多大就保存多大，禁止本地升采样。
8. 出图后按情景 `pitfalls` + 下方 QA 清单检查，返回文件路径和关键假设。
9. **一套品出完必须收口**（本轮已经在建/改模板则跳过）：
   - 本轮套的是**定制模板**（不是「默认电商模板」）→ 问：「这套要不要对照刚出的图改一下这个模板？」说要 → 按「坑跟谁走」改该模板的槽位 `overrides` / `pitfalls`，**不要再走 CREATE_TEMPLATE 新建**。
   - 本轮只用了情景或默认电商模板 → 问：「这类货以后还要反复出的话，要不要用这次的图和版式建一个模板？」说要 / 好 / 建 → **立刻读 `CREATE_TEMPLATE.md`**，把本轮成图、Prompt、产品图和已给信息当作检查点 1 的素材，不要从头再问一遍已经有的东西。
   - 用户说不用则结束。

---

## 生图配置

图像生成使用任意 OpenAI 兼容 API（示例用官方地址）。`.env` 放在 Skill 目录内（与 SKILL.md 同级）即全局生效，换会话、换项目都可用；脚本查找顺序：`--env-file` > 从当前目录向上查找 > Skill 自身目录。不要把真实 API key 写进仓库：

```dotenv
IMG_BASE_URL=https://api.openai.com/v1
IMG_MODEL=gpt-image-2
IMG_API_KEY=your-api-key
```

脚本兼容别名：`OPENAI_BASE_URL`、`OPENAI_API_BASE`、`OPENAI_IMAGE_MODEL`、`OPENAI_MODEL`、`OPENAI_API_KEY`。

**出图通道**（Codex 账号登录和生图 API 可同时存在，不是二选一）：

1. **已配置生图 API**（Skill 目录或项目有 `IMG_*` / 兼容别名）→ 走 `scripts/gen_image.py`。多图套图必须 `--batch`。API 额度/并发通常更高，有 API 时套图优先走脚本。
2. **未配 API，但当前是 Codex 账号登录**（或宿主有原生生图，如 Codex imagegen）→ 用宿主生图，**不要再追问 API**。单张由主会话出；**2 张及以上立刻派平级子代理并行**（见「Codex 原生生图：子代理并行」）。
3. **API 和宿主生图都没有** → 只输出 Prompt 包；若用户坚持要出图，读取 `SETUP.md` 第 2 步，列出三个选项让用户选（1 和 2 可同时选），不要只问「是否配置 API」。

走脚本时（Windows 用 `python`，macOS/Linux 用 `python3`，下同）：

```bash
# 单张
python scripts/gen_image.py --prompt "..." --size 1:1 --image data/product.jpg
python scripts/gen_image.py --prompt-file prompt.txt --output-dir generated-images

# 多图套图：批量清单一次并发生成（多图任务必须用这个，不要逐张串行调用）
python scripts/gen_image.py --batch jobs.json
```

批量清单 `jobs.json` 格式（相对路径相对清单文件所在目录）：

```json
{
  "output_dir": "generated-images/<slug>-pdp",
  "defaults": {"size": "1:1", "resolution": "1k", "quality": "high", "image": "data/product.jpg"},
  "jobs": [
    {"slot": "H1", "prompt_file": "prompt-H1.txt"},
    {"slot": "H2", "prompt_file": "prompt-H2.txt", "size": "4:5"}
  ]
}
```

脚本要点：

- 自动适配两种 API：URL 含 `apimart` → 异步轮询（比例格式 `1:1` + `--resolution`）；其他 → OpenAI 同步（像素尺寸自动转换）
- **带参考图时同步模式自动走 `/images/edits` 图生图端点**，原图真实上传给模型
- `--image`：参考产品图路径，保证产品一致性，强烈建议总是使用
- **批量模式**：默认并发 8，碰到 429/超时自动降到 4→2→1 只重跑失败槽位；输出按槽位命名（`h1.png`、`h2.png`…）；部分槽位最终失败时其余照常产出、退出码 1；加 `--skip-existing` 重跑同一命令即可只补失败的槽位
- 其他参数：`--output-dir`、`--poll-interval`、`--timeout`（同步图生图 300s；异步 1k/2k 默认 180，4k 默认 480）、`--format`、`--quality`、`--n`、`--concurrency`

安装或首次配置时，读取本 Skill 目录下的 `SETUP.md`，按第 2 步列出三个选项让用户选，不要自行默认。

---

## 情景系统

`references/scenes/` 下 26 个内置情景（01-26，通用拍法）；`references/templates/` 下是**模板层**——带甲方风格/语言/参数的定制实例（目前含默认示例 `templates/01-默认电商模板.json` 和箱包报价模板 `templates/02-箱包单品报价模板.json`）。两者结构不同：情景 = 拍摄方法（骨架/构图/文字渲染规则），保持通用、不带品牌；模板 = 品牌风格 + 语言 + 图片包 + 执行流程，通过 pack 引用情景，并用槽位 `overrides` 写明品牌对每张图的特化（构图占比/背景/布局/标注等），优化优先落在 overrides。模板字段规范见 `references/templates/_TEMPLATE_SPEC.md`。**每个情景是该类画面的完整执行规范**，包含：

| 字段 | 含义 |
|---|---|
| `prompt_template` | Prompt 骨架，替换 `{variables}` 使用 |
| `variants` / `category_tips` | 风格变体、品类加成建议 |
| `default_ratio` | 该场景默认画幅（用户指定优先） |
| `composition_rules` | 产品占比、留白、平台预留区、推荐角度及英文短语 |
| `text_rules` | 图内文字的字号、颜色、长度规则 |
| `pitfalls` | 该场景常见翻车点（出图后检查用） |
| `anti_ai_tips` | 防 AI 味技巧（UGC/社媒/直播类必读） |
| `examples` | 成品 Prompt 示例 |

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
| 使用 dsimage 模板：默认电商模板, 默认模板, default template, 通用电商主图, 起步套图 | `templates/01-默认电商模板.json` |
| 使用 dsimage 模板：箱包单品报价模板, 箱包单品报价, 箱包报价表, BEAUTY&U风格, bag quote sheet, 风格四 | `templates/02-箱包单品报价模板.json` |

无匹配 → 默认 `01-hero-image.json`。**只读取匹配到的情景，不要一次性加载全部。**

多图任务通常一次命中多个情景（如详情页 = 信息图 + 细节 + 场景的组合），每张图按其对应情景执行。

**区分两种任务**：

- **用情景或模板出图**（"使用 dsimage 来制作 / 使用 dsimage 模板：某某"）→ 按上方核心流程走。一套品出完后按第 9 步收口：定制模板问要不要对照改模板，否则问要不要新建。
- **制作一个模板**（用户丢来甲方材料/风格参考，或出图后确认「建模板」，说"制作一个模板 / 创建模板 / 建个模板"，可能带"使用 dsimage"）→ 读 `CREATE_TEMPLATE.md`，按其 4 个固定检查点（素材分析 → 骨架 → 执行规则 → 成稿登记）引导用户完成，每个检查点必须等用户确认才能进下一轮。出图后转来的，本轮成图和 Prompt 算已有素材，检查点 1 直接用，不要装没做过。模板需要而情景库没有的拍法，按该流程**一并新建情景**。模板层现状：默认示例 `templates/01-默认电商模板.json`（内置，可当起点），已登记箱包报价定制模板 `templates/02-箱包单品报价模板.json`。

**新建或修改情景的规范**：字段规范看 `references/scenes/_SCENE_SPEC.md`；写完跑 `python scripts/check_scenes.py` 校验，并在上方匹配表登记（校验器会检查登记，漏登记会报错）。

---

## 通用 Prompt 规则

以下铁律适用于所有场景（具体数值以情景 `composition_rules` / `text_rules` 为准）：

1. **颜色用 hex 码**，不用形容词："白底"是淡灰，`#FFFFFF` 才是白。
2. **产品占比和留白必须显式写出数字**，不写模型一定把画面填满。
3. **否定清单不能省**，写具体禁止项：`不要添加：道具、手、水印、假 logo、额外文字、装饰元素、渐变背景`。
4. **图内文字量严格控制**：主标题短、标签化，禁止大段小字；颜色和字号给明确指令。
5. 中文文字用「」包裹渲染更准；复杂笔画中文字换简单同义字；拉丁语言（英/葡/西等）直接写。
6. Prompt 结构顺序：Style Lock → 主体场景 → 目的与情绪 → 构图镜头 → 光线材质 → 风格真实感 → 画幅比例 → 图内文字 → 负面约束。
7. Prompt 保持简洁具体，自然语言优于关键词堆砌；写清楚材质（磨砂玻璃、拉丝金属、哑光饰面）。

---

## Campaign Style Lock（多图一致性）

多张图必须先建 Style Lock：这是整套图的视觉合同，原样复制进每张 Prompt 开头，不能改写或缩短。用户给了品牌规范就按品牌规范建；没给就用下面的默认锁：

```text
Campaign Style Lock: consistent premium ecommerce visual system across the entire image set; fixed palette of clean off-white background, deep charcoal text, one product-matched accent color, and one soft secondary accent; neutral-cool studio lighting; modern geometric sans-serif headline placeholders only; consistent rounded rectangular info labels; consistent thin-line icon style; clean high-end product photography mixed with minimal infographic elements; stable product scale and placement; generous whitespace; no color palette changes, no mixed fonts, no random backgrounds, no inconsistent lighting, no mismatched icon styles.
```

要点：固定 2-3 主色 + 1 强调色（写 hex）；冷暖调统一；字体系统统一；背景和光线系统统一；产品角度和大小稳定。单张图只能改画面目的、主体动作、局部构图和短文案。重生某张图必须复用原 Lock。

---

## 转化驱动力诊断

商品主图、电商图、广告图和 PDP 视觉，动手前先判断产品靠什么打动买家：

- **A 视觉驱动型**：外观、质感、礼品属性 → 主图序列主打视觉主张、质感特写、场景。
- **B 痛点驱动型**：解决明确摩擦/风险/烦恼 → 严格按"问题 → 解决机制 → 利益证明 → 信任 → CTA"推进。
- **C 情感价值驱动型**：身份、归属、冲动消费 → 情绪钩子、身份表达、社交信号。

**图片包结构优先级**：用户指定 > 命中模板的 `pack` > 命中情景的 `pack_structure`（仅文件实际提供时）> 按转化驱动力现场规划。不要假设 `11-infographic.json` 一定包含 `pack_structure`。

---

## 多图执行规则

1. 先建 Campaign Style Lock 并写入图片包计划。
2. 每张图独立编号、独立用途、独立 Prompt，写入单独文件（如 `prompt-H1.txt`），禁止一张 Prompt 生成多屏拼图。
3. 数量、比例、用途：**用户指定优先**；未指定时先用命中模板的 `pack`，再用命中情景实际存在的 `pack_structure`，两者都没有时按转化驱动力现场规划。
4. 每张 Prompt 开头必须是同一段 Style Lock。
5. 输出目录按「落盘」：批量品目录走同级镜像文件夹；单品才用 `generated-images/<slug>-pdp/`。
6. **出图必须并行，按通道选工具**：
   - 走脚本：写好全部 Prompt 文件后生成 `jobs.json`（每槽位 slot / prompt_file / size / image），`output_dir` 指向该品输出子文件夹，一次 `python scripts/gen_image.py --batch jobs.json`；失败槽位修正 Prompt 后加 `--skip-existing` 重跑，只补缺的图。
   - 走 Codex/宿主原生生图：写好全部 Prompt 文件后**立刻按下方「子代理并行」派发**；失败只重派失败槽位。
7. API 或模型不支持某尺寸时，改用最接近的支持尺寸并说明。
8. 未配 API 且宿主也不能原生生图时，只输出完整 Prompt 包，不调用脚本。有 Codex 原生生图就用它，不要因为没有 `.env` 就改成只出 Prompt。
9. 缺参数先问再出图：用户不补则按假设生成并在结果里列出假设，禁止因缺价格/尺寸/卖点而跳槽。认证、评分、销量、评价用示意占位即可，不要写成已核实。型号已从文件名取得时，不要再问货号。

### 源图文件名

用户给的原图，**文件名是生图输入的一部分**，不要只看画面、不要默认拿文件夹里第一张图套所有槽位。

**型号**

1. 去掉扩展名，得到型号（货号 / SKU / REF）。`BU-8821.jpg` → `BU-8821`。用户另外写了货号，以用户写的为准。
2. 同一品多张图：文件名带「正面 / 背面 / 侧面 / 细节 / front / back / side」等角度后缀时，去掉后缀，公共前缀才是型号（`BU-8821背面.jpg` → `BU-8821`）。
3. 图内要写货号、REF、SKU 的槽位，以及 Prompt 里的型号，**原文照写**，不要翻译、不要改大小写、不要另编一套。
4. 只有文件名明显是相机/聊天默认名（`IMG_`、`DSC_`、`Screenshot`、`微信图片`）时，才当没给型号，按缺参数去问。

**生图时按文件名做事**

5. 写 Prompt、选 `--image` / 宿主参考图之前先读该品所有源文件名。
6. 文件名标明角度或部位的，对上槽位再用：正面/主图/hero → 主图槽；背面/back → 背负、背面结构槽；侧面/side → 侧面槽；细节/macro → 细节槽。jobs.json 里每个 job 的 `image` 按这个选，不要全套共用一张。
7. 文件名或品文件夹名带颜色档的，配色页用对应那张，不要拿主色图去冒充其他色。
8. 没有角度词的图当主参考；该槽位没有对得上的源图时，用主参考，不要因为缺背面图就跳槽。
9. 批量品目录里：子文件夹名是品名（或颜色档），图片名才是型号；两者都保留，不要用英文 slug 替换型号。

### 批量品目录（大文件夹 → 同级成图文件夹）

用户常见用法：一个大文件夹，下面每个子文件夹是一个品，里面几张产品图。

```text
春季新品/                 ← 用户给的大文件夹（源，只读）
  双肩包-黑/
    正面.jpg
    背面.jpg
  双肩包-米/
    1.jpg
春季新品-成图/             ← 在大文件夹同级新建（默认名 = `{大文件夹名}-成图`）
  双肩包-黑/               ← 子文件夹名与源里的品文件夹逐字相同
    h1.png
    h2.png
  双肩包-米/
    h1.png
```

1. 判定：用户给的路径下面有多个子文件夹、且子文件夹里是图 → 按本规则。用户指定了输出文件夹名则用用户的，否则用 `{大文件夹名}-成图`，建在大文件夹**同级**，不要建在大文件夹里面，不要改源目录里的任何文件。
2. 每个品文件夹单独出一套图，参考图只用该品文件夹里的图。输出写到成图根目录下**同名**子文件夹，名字与源子文件夹完全一致（含中文、空格、连字符），不要改成英文 slug，不要加 `-pdp`。
3. 成图按槽位命名（`h1.png`、`h2.png`…）放进该品输出子文件夹。已有同名成图文件夹就接着用，只写当前品，不要清空别人的子文件夹。
4. 多品按品排队（一次一个品）；每个品内部仍按通道并行（`--batch` 或子代理）。用户只点了其中几个子文件夹就只出那几个。
5. 整批出完再收口一次，不要每个品问一遍要不要建模板。

单张图、或只有一个品文件夹且用户没说批量：仍用 `generated-images/<slug>-pdp/`。

### Codex 原生生图：子代理并行

内置 `image_gen` / 宿主原生生图一次只出一张。多图套图把并行交给子代理，主会话负责写 Prompt、派工、收图、检查。

1. 主会话先写完全部 Prompt 文件和槽位清单（slot、prompt 路径、size、参考图、目标文件名）。
2. **2 张及以上：立刻派平级子代理**，每槽位一个，同时最多 4 路；多出来的分波排队。1 张由主会话自己出。不要等用户说「开子代理」。
3. 每个子代理只出自己那个槽位：读对应 Prompt（含同一段 Style Lock 和源图型号）、按源文件名选参考图、用宿主原生生图、把成图存到该品输出目录的 `<slot>.png`（如 `h1.png`），返回绝对路径。沿用原 Prompt，不要改成 SVG/HTML/占位图，不要覆盖其他槽位的文件。
4. 用宿主的平级子代理派发（Codex Desktop 子代理、Cursor / Claude Code 的 Task 等）。已经在 Codex 会话里就派 Desktop 子代理，不要再套一层 `codex exec`。某路结束立刻收下路径并关掉，空出位置给下一波。
5. 部分失败其余照常留下；只重派失败槽位。宿主没有子代理时，主会话按同一目录和文件名把槽位连续出完。

---

## QA 检查

最终输出前确认：

- [ ] 已读取命中的情景，Prompt 基于情景的 `prompt_template` 和 `composition_rules` 组装
- [ ] 多图任务已建 Style Lock 且每张开头一致
- [ ] 商品/营销任务已做转化驱动力诊断
- [ ] 颜色全部 hex、占比和留白有数字、否定清单具体
- [ ] 图内文字短且必要，符合情景 `text_rules`
- [ ] 源图文件名已用于型号和参考图匹配（正面/背面等对上槽位，没有拿第一张图套全套）
- [ ] 批量品目录已在大文件夹同级建 `{名}-成图`，子文件夹名与源品文件夹一致，没有写进源目录
- [ ] 走 Codex/宿主原生生图的多图任务已派子代理并行（同时最多 4 路），成图按槽位落在输出目录
- [ ] 出图后按情景 `pitfalls` 逐条检查通过
- [ ] UGC / 社媒 / 直播场景已应用 `anti_ai_tips`
- [ ] 文件和输出中没有 API key 或私密凭据
- [ ] 出图发现问题已按「坑跟谁走」询问用户是否回流沉淀
- [ ] 一套品出完已按第 9 步收口：定制模板问对照改模板，否则问是否新建；用户说要则已转入对应流程

---

## 翻车回流（沉淀机制）

出图发现问题后，按"坑跟谁走"分层沉淀，并**主动询问用户是否回流**：

| 坑的类型 | 判断 | 沉淀到 |
|---|---|---|
| 拍法的坑（换个客户也会踩） | 影响这一类图 | 所引情景的 `pitfalls` |
| 品牌的坑（只跟这个甲方有关） | 影响这一个模板 | 该槽位的 `overrides`（画面特化）或模板 `pitfalls` / `text_rules` |
| 模型本身的坑（跨情景跨品牌） | 影响所有出图 | SKILL.md「常见翻车点」表 |

回流格式：`"症状（→修法）"`；情景 `pitfalls` 上限 3-5 条，满了合并同类。回流后跑 `python scripts/check_scenes.py` 并提交。

---

## 常见翻车点

| 翻车 | 防护 |
|---|---|
| 中文字笔画错 | 放大 200% 逐字核对；复杂字换简单同义字 |
| 品牌色漂移 | 全部用 hex 码 |
| 画面填满无留白 | 按情景 `composition_rules` 显式声明 |
| 全套图角度雷同 | 按情景 `composition_rules.angles` 分配，不连续 3 张同角度 |
| 图内文字乱码 | 放大检查，乱码整张重出 |

场景特化的翻车点见各情景 `pitfalls` 字段，出图后必须对照检查。
