---
name: dsimage
description: E-commerce visual creation skill. Turns product photos plus a one-line request into complete, conversion-optimized image sets using 26 shooting scenes, with Campaign Style Lock for visual consistency. Generates via Codex built-in imagegen or a configured OpenAI-compatible image API. Also builds reusable client templates from brand materials. A template has one lock: rules (generate from brand rules) or master (swap the product onto a locked page set). Use when the user says 使用 dsimage / 使用dsimage / dsimage, or asks for 电商主图 / 详情页 / 产品图 / 商品图 / 白底图 / listing images / product photos / PDP / A+ content / social or ad creatives, or 制作模板 / 创建模板 / 使用 dsimage 模板 / 替换模板 / 换品 / 换货.
---

# dsimage Skill

当用户需要视觉策略、图片 Prompt、商品主图、营销图、社媒图、广告图、电商 PDP 视觉，或要求直接 AI 生图时，使用这个 Skill。

这个 Skill 有两种模式：

1. **Brief / Prompt 模式**：只输出视觉简报和可执行图片 Prompt。
2. **Generate 模式**：当用户明确要求"生图、生成图片、出图、render image"时，先输出最终 Prompt，再调用生图。

不要暴露、索要、写入、提交或回显真实 API key。生图 API 不是必须的：Codex 账号登录即可用原生生图；需要更高额度/并发时可再配 API，两者可同时开，不是二选一。

---

## 意图引导（出图前先对齐，避免用错路）

用户心里通常已经有成品长什么样，只是没把做法说全。职责不是让用户学两套模板名，而是**从材料和措辞里确定怎么干，用白话跟他确认，再做成他要的那种。** 已经够清楚就直接干；会走错路才问，问的时候先说出你判断他想要的结果。

内部看命中模板的 `lock`：`master` = 对着母版换货；`rules` = 按品牌规则画（或只用情景）。对用户只谈结果（换货 vs 按感觉新画），不要让用户挑两种模板。

| 用户要的结果 | 怎么干 |
|---|---|
| 和这套样板同一版式，只是货换成新的 | 换品：母版不动，只换商品 |
| 参考这种感觉，但每款可以重新构图 | 按感觉新画 |

### 什么时候不必问

已经够清楚就直接做，不要为问而问：

- 已点名「替换模板：某某 / 只换产品 / 版式别动 / 一模一样 / 各型号统一」→ 换货（找 `lock=master` 的模板；库里没有则说明，不要假装在换）
- 已点名「用某某模板 / 按这个调性、感觉、规范来 / 参考这个配色」且材料是 PDF、色板、情绪板，不是成套成品主图 → 按规则画
- 只有产品图，没有「标准套图 / 成品主图 / 样板页」→ 按规则画（默认电商模板或情景）。可提一句：以后要铺很多型号、要长得一样，可以把定稿套图做成带母版的模板
- 已命中已登记的模板，且 JSON 里 `lock=master` → 换货
- 已命中已登记的模板，且 `lock=rules`（或不写），没有另给一套成品主图 → 按该模板规则画

### 什么时候必须问（除非用户已经说死）

材料或措辞对得上下面任一条，先停下来问一轮。**推荐项写在前面**，并说明为什么。

**1. 一套「标准商品图 / 模板图 / 样板套图」+ 若干产品图，说整一下 / 按模板做 / 套一下**  
最容易走错。成品页上已经有标题、图标、报价块 → 多半是换品；只有氛围图/色板 → 多半是新画。

问法（可按材料改字，结构不要散）：

```text
你给了两样：一套已经做好的版式图，加上要上的产品图。我按「版式不动、只换商品」来做——做成和样板同一套版，货换成你的。图上的货号、价格除非你说要改，否则一个字都不动。要是你其实想参考感觉重新画、不锁这套版式，说一声。
```

**2. 一个大文件夹、每个子文件夹一个型号，同时给了一套样板图**  
这不是「每个型号各自按规则新画一套」（那样每款版式会对不齐）。正确做法是：**同一套样板当母版，每个型号单独换一次货**——H1 还是那张版式，只是袋子换成该型号。源文件夹有几个型号子文件夹，就出几套成图，版式同一套。用户只点了其中几个子文件夹就只做那几个。问一句：是不是每个型号都套这套样板、只换货。

**3. 「做成和这个一样 / 不要走样 / 统一版式」**  
就是换品。再确认字要不要换成新货号/价格；没说则整页冻住。

**4. 「这种感觉 / 这种调性 / 参考配色和字体」**，图不是完整主图页  
按感觉新画。不要问换品，以免把情绪板当成母版去贴产品。

**5. 品牌 PDF + 一套已画好的 9 页主图 + 产品图**  
成品主图优先当换品母版；PDF 只作核对。问一句是否锁这套成品换货（推荐），还是按 PDF 规则重画。

**6. 用户说的「模板」其实是平台坑位**（Amazon 主图、5 张+详情、小红书三图）  
这是出几张、什么比例，不是换品/新画。先澄清坑位；若同时又给了成品套图，再走第 1 条。

**7. 只给成品套图，没有新产品图**  
这是建模板，不是出图。问：登记成以后换货用的母版（推荐，若还要铺型号）→ `lock=master`，还是提炼成规则以后重画 → `lock=rules`。然后读 `CREATE_TEMPLATE.md`：先建文件夹，把这些成品页拷进去，再写 JSON。缺页不要写成 `lock=master`。

**8. 刚按规则出完一套，又丢来新型号说「也出一套」**  
问：用刚出的图当母版换货（各型号更像），还是继续按规则再画（会有差别）。用户说要统一 → 把本轮成图建成 `lock=master` 的模板再换货。

**9. 换品路上用户又说「字大一点 / 改版式 / H5 别那样」**  
那是改母版或改风格，不是这一次换货能顺手做的。先问：只改这一款，还是改母版让以后都变。

### 问的时候遵守

- 一次只问会做歪的那一点（是不是锁这套版只换货；字改不改）。不要让用户从菜单里挑模板种类。
- 用户含糊（「你看着办」「整好看就行」）→ 按你判断的那种结果做，汇报里写明：我按版式不动只换货做的（或按感觉新画）。
- 用户两种都要（先定一版再铺型号）→ 先画出他要的那一版，再拿成图当母版铺其余型号；说明顺序，不要两套做法叠在同一张图上。

### 开做前问一句要求（路已经对齐之后）

做法定了、还没写 Prompt / 还没调生图时，**先把匹配前 3 名给用户看**，再问还有没有要求。用户心里常有没说出口的细节（改货号、只要某几页、某个型号先不做、文字语言、不要改价）。

已经在本轮说清了全部要求、并且点名的模板已命中第 1 名 → 仍要展示排名（让他看见将用的模板和场景），问法可以更短，不要再让他从菜单里挑类型。

把 `match_pack.py` 的 stdout 放在前面，末尾保留下面这句（脚本已带）：

```text
回 1 / 2 / 3 换方案。还有没有要求（货号、只要某几页、某个型号先不出）？没有就按第 1 个开做。
```

用户说「没有 / 先出 / 你看着办 / 1」→ 立即按第 1 名开做。说 2 或 3 → 改用该名次的模板和场景。默认：换货则字和版式全冻；按规则画则缺的参数按假设，汇报里列出。不要因为这一问空等。

**2 个及以上品文件夹**：这一问只问一次。答案写入成图根 `_prompts/批次.json` 的 `only` / `skip` / `notes`，然后按「批量品目录」并发派工人。不要每个品再问一遍。

---

## 核心流程

**本 Skill 只规定通用流程。动手前先走「意图引导」：材料或措辞含糊时，用白话问清是换货还是按规则画。** 命中 `lock=master` 时走「换货」，不要按情景重画。

**模板大于情景。** 命中 `lock=rules` 的模板时，情景只提供拍法骨架和缺省数值。模板里写了的，一律用模板，不要跟情景折中，也不要为迁就这一套图去改情景。只命中情景、没有模板时，才以情景为准。

| 高 → 低 | 听谁 | 管什么 |
|---|---|---|
| 1 | 用户本轮 | 数量、比例、删槽、文案、货号、点名要改的字 |
| 2 | 模板 JSON | `pack`（含槽位 `ratio` / `purpose` / `overrides`）、`text_rules`、`style_lock`、`template_meta.brand`、`generation`、语言、该模板 `pitfalls` |
| 3 | 本文件夹 `要求.json` | 仅当该模板文件夹名在它的 `templates` 里：语言、分辨率、格式、风格、brand |
| 4 | 所引情景 | `prompt_template` 骨架；模板没覆盖的 `composition_rules` / `text_rules` / `default_ratio` / `generation`；`pitfalls` / `anti_ai_tips` |
| 5 | SKILL / 脚本 | 上面都没有时 |

同名字段直接覆盖，不要平均、不要各用一半。槽位 `overrides` 只作用于该槽。

1. 先走「意图引导」，再跑匹配。开口带「替换模板 / 按样图换货 / 只换产品」→ 按换货意图匹配；「使用 dsimage 模板：某某」按模板名匹配，再看该 JSON 的 `lock`。**每次出图前**执行 `python scripts/match_pack.py --query "<用户原话>"`（见「匹配与展示」），把前 3 名原样给用户看，第 1 个最优。采用第 1 名的模板和它列出的场景。点名不在库里时脚本会说明，**按它给出的前 3 名走，不要改成白底主图充数。** 展示排名时一并问还有没有要求（本轮已说清则只展示排名、按第 1 个做）。
2. **`lock=rules`**：模板在甲方文件夹里时，先读 `要求.json`，确认该模板文件夹名在 `templates` 里，再读模板 JSON；不在列表里就停下，不要拿这份要求套别的文件。零散模板只读它自己。打开该文件夹里的示例图，对照版式和调性再写 Prompt。然后读该槽引用的情景。Prompt = 情景 `prompt_template` 骨架 → 模板 `style_lock` / brand / `text_rules`（brand / 语言 / generation 模板没写则用 `要求.json`）→ 该槽 `overrides` 覆盖情景默认。情景与模板同名字段用模板的；情景 `pitfalls` / `anti_ai_tips` 仍要查，和模板冲突时听模板。只命中情景、没有模板时，才整份按情景执行。生图参考图用用户产品图，不要把示例图塞进 `--image` 当母版。**`lock=master`**：读取该模板 JSON + 同文件夹里的母版套图，走「换货」节；有甲方则同样先核对 `要求.json` 的 `templates`。缺母版就停下。不要加载情景、不要建 Style Lock 去重画。
3. 价格、尺寸、卖点、文案等缺了先问一轮；用户不补或说先出图，则按合理假设继续，槽位不跳过。**换货例外**：未点名的字不改、不问卖点文案；只问 `editable_fields` 里本轮要换的值，以及缺的产品角度。产品外形以参考图为准。**源图文件名要参与生图**（见「源图文件名」）：型号、哪张当正面/背面参考，都从文件名读。认证/评分/销量不要写成已核实事实，可用示意占位。
4. 多图任务（`lock=rules` / 情景）：先建立 **Campaign Style Lock**（见下文），原样放进每张 Prompt 开头。`lock=master` 不要建 Style Lock。一品多色先锁主色（见「一品多色」），其他颜色不要在套图里反复出现。
5. `lock=rules` 的商品/营销任务：先做**转化驱动力诊断**（见下文）。换货跳过。
6. 逐张写 Prompt：`lock=rules` = 模板 Style Lock → 情景 `prompt_template` 骨架 → 该槽 `overrides` 覆盖情景默认 → 按需 `variants` / `category_tips` → 通用规则收尾。换货 = 「换货」里的指令，不要套情景骨架。**2 个及以上品由各品工人写，主会话不写。**
7. Generate 模式：按下方**出图通道**选路；用户提供了产品图必须带上参考图。`lock=master` 每槽必须带**母版 + 产品图**两张参考（`jobs.json` 的 `image` 为数组，先母版后产品）。走脚本时单品多图用 `--batch`；**2 个及以上品**按「批量品目录」并发调度（工人写 Prompt，有 API 则 `queue_pack.py --run`）。走 Codex/宿主原生生图时多图**积极派子代理并行**（见「多图执行规则」）。用户丢来「大文件夹 + 每子文件夹一个品」时，按「批量品目录」落盘，不要写进源文件夹。Prompt / `jobs.json` 按「落盘」进 `_prompts/`，禁止写进源品文件夹或成图文件夹。**命令参数与 Prompt 字段同一套优先级**（见上方「模板大于情景」）。`--size` 用比例（`1:1`），不要写死 `1024x1024` 或 `2048x2048`。未特别要求 2k 时用甲方或模板默认 `1k`，不要从情景抄 `2k`。接口返回多大就保存多大，禁止本地升采样。
8. 出图后按对应 pitfalls + 下方 QA 清单检查，返回文件路径和关键假设。换货对照母版查：未点名的字/图标/版式是否被改。
9. **一套品出完必须收口**（本轮已经在建/改模板则跳过；**2 个及以上品整批出完再问一次**）：
   - 本轮套的是 **`lock=master`** → 问：「母版要不要对照刚出的图换一张？」说要 → 只换该槽母版图或 `product_ref` / `editable_fields`，不要改成 `lock=rules`、不要走 CREATE_TEMPLATE 新建。
   - 本轮套的是**定制模板且 `lock=rules`**（不是「默认电商模板」）→ 问：「这套要不要对照刚出的图改一下这个模板？」说要 → 按「坑跟谁走」改该模板的槽位 `overrides` / `pitfalls`，**不要再走 CREATE_TEMPLATE 新建**。若用户说「以后别的型号要长得一模一样」→ 转 CREATE_TEMPLATE：建新文件夹，**把本轮成图整套拷进去当母版**，写成 `lock=master`。
   - 本轮只用了情景或默认电商模板 → 问：「这类货以后还要反复出的话，要不要用这次的图和版式建一个模板？」说要 / 好 / 建 → **立刻读 `CREATE_TEMPLATE.md`**，先定 `lock`（铺型号、要像素级一致 → `master`，本轮成图拷进模板夹当母版；还没有定稿套图 → `rules`，至少把本轮 H1 拷进去当示例）。本轮成图、Prompt、产品图和已给信息当作检查点 1 的素材。不要只写 JSON 不拷图。
   - 用户说不用则结束。

---

## 生图配置

官方 OpenAI / Grok / Gemini 的接口地址写死在 `scripts/gen_image.py`，配置时只选服务商、填 key、选模型，**不要问用户要 URL**。`.env` 放在 Skill 目录内（与 SKILL.md 同级）即全局生效；脚本查找顺序：`--env-file` > 从当前目录向上查找 > Skill 自身目录。不要把真实 API key 写进仓库：

```dotenv
IMG_PROVIDER=openai
IMG_MODEL=gpt-image-2
IMG_API_KEY=your-api-key
```

`IMG_PROVIDER` 取值：`openai`（`https://api.openai.com/v1`）/ `grok`（`https://api.x.ai/v1`）/ `gemini`（`https://generativelanguage.googleapis.com/v1beta`）。其他兼容网关才设 `IMG_PROVIDER=custom` 并填 `IMG_BASE_URL`。

脚本兼容别名：`OPENAI_BASE_URL`、`OPENAI_API_BASE`、`OPENAI_IMAGE_MODEL`、`OPENAI_MODEL`、`OPENAI_API_KEY`、`XAI_API_KEY`、`GEMINI_API_KEY`、`GOOGLE_API_KEY`。默认模型：OpenAI `gpt-image-2`，Grok `grok-imagine-image-2.0`，Gemini `gemini-3.1-flash-image`。

**出图通道**（Codex 账号登录和生图 API 可同时存在，不是二选一）：

1. **已配置生图 API**（Skill 目录或项目有 `IMG_*` / 兼容别名）→ 走 `scripts/gen_image.py`。一品多图必须 `--batch`。**2 个及以上品**不要每品各开一套 `--batch`（并发会叠乘）；工人只写 `_prompts/`，调度跑 `queue_pack.py --run`（见「批量品目录」）。API 额度/并发通常更高，有 API 时套图优先走脚本。
2. **未配 API，但当前是 Codex 账号登录**（或宿主有原生生图，如 Codex imagegen）→ 用宿主生图，**不要再追问 API**。单品：单张由主会话出；**2 张及以上立刻派平级子代理并行**（见「Codex 原生生图：子代理并行」）。**2 个及以上品**：主会话不写 Prompt，按「批量品目录」并发派品工人。
3. **API 和宿主生图都没有** → 只输出 Prompt 包；若用户坚持要出图，读取 `SETUP.md` 第 2 步，列出三个选项让用户选（1 和 2 可同时选），不要只问「是否配置 API」。

走脚本时（Windows 用 `python`，macOS/Linux 用 `python3`，下同）：

```bash
# 单张
python scripts/gen_image.py --prompt "..." --size 1:1 --image data/product.jpg
python scripts/gen_image.py --prompt-file prompt.txt --output-dir generated-images

# 多图套图：批量清单一次并发生成（单品多图必须用这个，不要逐张串行调用）
python scripts/gen_image.py --batch generated-images/_prompts/<slug>/jobs.json

# 2 个及以上品：看队列 → 派品工人 → API 全局出图
python scripts/queue_pack.py --init --source "<大文件夹>" --template templates/<甲方>/<模板>/<模板>.json --notes "<口头要求>"
python scripts/queue_pack.py --queue "<成图根>/_prompts/批次.json" --next
python scripts/queue_pack.py --queue "<成图根>/_prompts/批次.json" --run --skip-existing
```

批量清单必须放在该品 `_prompts/` 目录（见「落盘」），相对路径相对清单文件所在目录：

```json
{
  "output_dir": "../../<slug>-pdp",
  "defaults": {"size": "1:1", "resolution": "1k", "quality": "high", "image": "<源图绝对路径>"},
  "jobs": [
    {"slot": "H1", "prompt_file": "prompt-H1.txt"},
    {"slot": "H2", "prompt_file": "prompt-H2.txt", "size": "4:5"}
  ]
}
```

脚本要点：

- 按 `IMG_PROVIDER` / 模型名走对应协议：OpenAI 同步（像素尺寸）；Grok 官方 JSON（`aspect_ratio` + `resolution`，参考图走 `/images/edits` JSON 而非 multipart）；Gemini 官方 `generateContent`（`x-goog-api-key`）；URL 含 `apimart` → 异步轮询
- **带参考图时**：OpenAI 走 multipart `/images/edits`；Grok 走 JSON `/images/edits`；Gemini 把原图作为 `inline_data` 一并提交。原图真实交给模型，不要只把路径写进 Prompt
- `--image`：参考图路径，可重复传入。`lock=rules` 通常一张产品图；**`lock=master` 必须先母版后产品图**（`jobs.json` 里 `image` 用数组）
- **批量模式**：默认并发 9，碰到 429/超时自动降到 4→2→1 只重跑失败槽位；输出按槽位命名（`h1.png`、`h2.png`…）；部分槽位最终失败时其余照常产出、退出码 1；加 `--skip-existing` 重跑同一命令即可只补失败的槽位
- **多品**：`queue_pack.py` 看队列、`--next` 派品工人写 Prompt、`--run` 单独生图。生图默认并发 32（最大 64），429 自动减半。不要每品各开一套 `--batch`
- 其他参数：`--output-dir`、`--poll-interval`、`--timeout`（同步图生图 300s；异步 1k/2k 默认 180，4k 默认 480）、`--format`、`--quality`、`--n`、`--concurrency`

安装或首次配置时，读取本 Skill 目录下的 `SETUP.md`，按第 2 步列出三个选项让用户选，不要自行默认。

---

## 情景系统

`references/scenes/` 下 26 个内置情景（01-26，通用拍法）。

**存放：一个模板一个文件夹。** JSON 和图都在这个文件夹里，整夹复制就能分享或挪位置。匹配看 JSON 里的名字和触发词，不看路径有几层。不要把产品图或成图塞进模板库。

```text
references/templates/
  01-默认电商模板/
    01-默认电商模板.json
    h1.png                          # lock=rules 至少一张示例
  NN-中文名/
    NN-中文名.json
    h1.png                          # 有图就和 JSON 放一起
  BeautyU/                          # 同一甲方多个品才建
    要求.json                       # templates 列出下面的文件夹名
    01-箱包单品报价模板/
      01-箱包单品报价模板.json
      h1.png
```

分享 / 移动时整夹走，不要只拷 JSON：

| 要带走 | 复制哪一夹 |
|---|---|
| 一份零散模板 | `NN-中文名/` |
| 某个甲方的全部模板 + 共用要求 | `{甲方}/`（含 `要求.json` 和下面每个模板夹） |
| 甲方里的一份 | `{甲方}/NN-中文名/`。丢进另一个甲方则把文件夹名写入那边的 `templates`；丢到根下当零散，先把 `要求.json` 里的 `generation` / 语言 / brand 写进这份 JSON |

拷进来之后在 SKILL.md 模板匹配表登记一行，再跑 `python scripts/check_scenes.py`。

| 放哪 | 放什么 | 不放什么 |
|---|---|---|
| `NN-中文名/NN-中文名.json` | 这一套怎么出图（lock、pack、字规则） | 图片 |
| `NN-中文名/` 里的图片 | **每个模板都要有。** `lock=master`：每槽母版，文件名 = pack 的 `example`。`lock=rules`：至少 1 张示例（建议 H1 / `h1.png`，该槽写 `example`），只作版式参考 | 用户产品图、成图、`要求.json` |
| `{甲方}/要求.json` | 本文件夹里那些模板的共用语言/色板/分辨率；`templates` 列文件夹名 | 图片、pack |
| 用户产品图 | 用户给的路径 / `data/` | 不要拷进 `templates/` |
| 成图 | `generated-images/` 或 `{名}-成图/` | 不要写回 `templates/` |

`lock=master` 出图读该文件夹里的母版；缺任何一槽母版就不要出、也不要假装是换货。`lock=rules` 出图读 JSON + 用户产品图；先看文件夹里的示例图对照版式和调性，不要把示例图当母版去换货。

不要建 `风格/`、`替换/`。编号接所在目录（根目录或某个甲方文件夹）已有最大号。

字段规范在 `references/templates/_TEMPLATE_SPEC.md`，**只在新建或改模板时再读**，出图不要加载。**情景是一类图的缺省拍法**（仅 `lock=rules` 使用；被模板引用时模板内容大于情景），包含：

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
| 使用 dsimage 模板：默认电商模板, 默认模板, default template, 通用电商主图, 起步套图 | `templates/01-默认电商模板/01-默认电商模板.json` |
| 使用 dsimage 模板：箱包单品报价模板, 箱包单品报价, 箱包报价表, BEAUTY&U风格, bag quote sheet, 风格四 | `templates/BeautyU/01-箱包单品报价模板/01-箱包单品报价模板.json` |

「使用 dsimage 模板：某某」查这一张表。命中后再读 JSON 的 `lock` 决定按规则画还是换货。用户说「替换模板：某某」仍当点名，并按换货意图匹配。**只读取第 1 名方案用到的情景/模板**；模板在甲方文件夹里才再读该文件夹的 `要求.json`（先核对该模板文件夹名在 `templates` 里）。不要一次性加载全部模板。

### 匹配与展示

出图前必须跑（Windows 用 `python`，macOS/Linux 用 `python3`）：

```bash
python scripts/match_pack.py --query "<用户原话，不要改写>"
```

脚本按触发词和 keywords 打分，**固定输出 3 名，第 1 个最优**。每一名都带将用的模板（或仅情景）以及 pack 场景清单。把 stdout **原样**给用户看，不要自己重排、不要藏备选。

- 用户点名且命中 → 该模板是第 1 名；仍展示 2、3 名备选。
- 用户没点名 → 第 1 名是自动匹配结果（全套/详情页偏向默认电商模板；小红书等单情景会排到仅情景）。
- 用户点名但库里没有 → 脚本第一行会说明，下面仍是最接近的三个。**采用这名单的第 1 名**，不要改走 `01-hero-image.json` 充数。
- 用户要换货但库里没有 `lock=master` 的模板 → 脚本会说明；不要假装已经在换货。

多图任务通常一次命中多个情景（如详情页 = 信息图 + 细节 + 场景的组合），每张图按其对应情景执行。`lock=master` 按 pack 槽位执行，一张母版换一张品。用户回 2 或 3 则改用该名次，不要混用两套 pack。

**区分任务**（先过「意图引导」，再对号）：

- **用情景或 `lock=rules` 的模板出图** → 按规则画。
- **换货 / 命中 `lock=master`** → 「换货」。
- **制作一个模板** → 读 `CREATE_TEMPLATE.md`，按那份的顺序做：定 lock → 建空文件夹 → **先拷图** → 再写 JSON → 校验登记。对用户说换货母版 vs 按规则画，不要甩两种模板名。`lock=rules` 至少一张示例（没有则先试跑 H1 再拷）；`lock=master` 齐套母版，没有就不要用这个 lock。`lock=rules` 缺情景可新建情景；`lock=master` 不要新建情景。

**新建或修改情景的规范**：字段规范看 `references/scenes/_SCENE_SPEC.md`；写完跑 `python scripts/check_scenes.py` 校验，并在上方匹配表登记（校验器会检查登记，漏登记会报错）。

---

## 换货（lock=master）

锁的是已画好的母版套图，不是规则。每个型号对着同一套图换货，未点名的文字、图标、版式、背景保持原样。

**资产**

一份模板一个文件夹；JSON 和图放在一起，整夹复制即可带走母版。产品图不进这里。

```text
# 零散
references/templates/NN-中文名/
  NN-中文名.json
  h1.png
  h2.png

# 有甲方
references/templates/{甲方}/要求.json
references/templates/{甲方}/NN-中文名/
  NN-中文名.json
  h1.png
  h2.png
```

**出图前**

1. 若在甲方文件夹里，先读 `要求.json`，确认该模板文件夹名在 `templates` 里（语言、分辨率、格式、风格）；不在列表里就停下。零散模板跳过。
2. 读 JSON 的 `pack`：每槽 `example` + `product_ref`（`front` / `back` / `side` / `detail` / `colorway`）。对应文件不在该文件夹里就停下，不要出图、不要改走按规则重画。
3. 按 SKILL「源图文件名」选该品产品图。`product_ref` 对不上（要背面没有背面图）→ 问用户或跳过该槽，禁止用正面硬贴背面页。
4. `template_meta.category` 有值且新品外形差太远（双肩包母版 vs 登机箱）→ 先问，不要硬换。
5. 一品多色：非 `colorway` 槽只用主色产品图；其他颜色只出现在 `colorway` 槽。
6. 文字政策 C：`editable_fields` 里且用户本轮给了新值的才改（货号/价格/色名等）；没点名的字一句不动。不要把母版上的卖点句重写一遍。

**Prompt（每张独立写入 `_prompts/`）**

不要 Style Lock，不要情景 `prompt_template`。结构固定：

```text
The first reference image is a locked layout master. The second reference image is the product to insert.
Replace only the product in the master with the product from the second image. Keep background, typography, icons, callout lines, labels, grid, lighting, camera angle, and composition identical to the master.
Do not restyle. Do not redraw the page. Do not add or remove labels/icons.
Allowed text replacements (only these, and only if a new value is given): {本轮点名的字段=新值}。If none, keep all master text exactly.
The new product must match the second reference exactly (shape, color, material, hardware, logo).
Negative: do not change layout, do not invent product features, do not use a different background.
```

**生成**

- `jobs.json` 的每个 job：`"image": ["<母版绝对路径>", "<产品图绝对路径>"]`，`size` 用该槽 `ratio`。
- 走脚本：`--batch` 该品 `_prompts/jobs.json`。走宿主生图：子代理必须附上该槽母版 + 产品图两张参考。
- 成图仍按「落盘」进该品成图文件夹（`h1.png`…），Prompt 只在 `_prompts/`。

**出图后**

对照母版检查：版式、图标数量、未点名字段、产品是否换成新货且外形跟产品参考一致。翻车沉淀到该模板的母版图或 `editable_fields` / pitfalls，不要写进情景。

---

## 通用 Prompt 规则

以下铁律适用于 **`lock=rules` 的模板和情景**。具体数值：模板 / 槽位 `overrides` 优先，没写才用情景 `composition_rules` / `text_rules`。**`lock=master` 不要套用本节去重画**，只走「换货」指令。

1. **颜色用 hex 码**，不用形容词："白底"是淡灰，`#FFFFFF` 才是白。
2. **产品占比和留白必须显式写出数字**，不写模型一定把画面填满。
3. **否定清单不能省**，写具体禁止项：`不要添加：道具、手、水印、假 logo、额外文字、装饰元素、渐变背景`。
4. **图内文字量严格控制**：主标题短、标签化，禁止大段小字；颜色和字号给明确指令。
5. 中文文字用「」包裹渲染更准；复杂笔画中文字换简单同义字；拉丁语言（英/葡/西等）直接写。
6. Prompt 结构顺序：Style Lock → 主体场景 → 目的与情绪 → 构图镜头 → 光线材质 → 风格真实感 → 画幅比例 → 图内文字 → 负面约束。
7. Prompt 保持简洁具体，自然语言优于关键词堆砌；写清楚材质（磨砂玻璃、拉丝金属、哑光饰面）。
8. **一品多色锁主色**：同一产品多张图、每张一种颜色时，整套主图/场景/细节只用一个主色；其他颜色只集中出现在**一张**配色合集里，不要一张一个色轮着出。细则见「一品多色」。

---

## 一品多色

不限于批量文件夹。用户一次丢来多张产品图、每张一种颜色，或一个品文件夹里每张图一种颜色，都按这条执行。

1. **选定一个主色**，整套功能图、主图、场景、细节都只用这张主色参考。用户指定优先；否则用文件名/文件夹带「主、主色」或无颜色词的那张；再不行用正面主图。汇报里写明主色是哪张。
2. **其他颜色不要在套图里反复出现**。不要一张一个色轮着出，不要把配色散到每张生活图/细节图里。
3. **可以有一张「各色在一起」**：模板已有配色槽（`lock=rules` 如 H9，`lock=master` 的 `product_ref` 为 `colorway`）就用那一张；pack 没有配色槽时按规则画可加一张合集。换货不要额外发明一页。
4. 用户明确要求「每个颜色出一套」时才按色分套，不要混进主色套图里。

---

## Campaign Style Lock（多图一致性）

多张图必须先建 Style Lock：这是整套图的视觉合同，原样复制进每张 Prompt 开头，不能改写或缩短。**`lock=master` 除外**：母版套图就是锁，不要另写 Style Lock。模板已有 `style_lock` 则原样用，不要用情景的光线/色板改写；没给才用下面的默认锁：

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

命中 `lock=master` 时改走「换货」，下面的 Style Lock / 情景骨架不适用。

1. 先建 Campaign Style Lock 并写入图片包计划。
2. 每张图独立编号、独立用途、独立 Prompt，写入单独文件（`prompt-H1.txt`），禁止一张 Prompt 生成多屏拼图。文件按下方「落盘」放置，禁止写进源品文件夹、成图文件夹、项目根或 Skill 目录。
3. 数量、比例、用途：**用户指定优先**；未指定时先用命中模板的 `pack`，再用命中情景实际存在的 `pack_structure`，两者都没有时按转化驱动力现场规划。
4. 每张 Prompt 开头必须是同一段 Style Lock。
5. 成图和提示词按「落盘」分开放：成图进品输出文件夹；Prompt 和 `jobs.json` 进同级 `_prompts/`。
6. **出图必须并行，按通道选工具**：
   - **2 个及以上品**：主会话按「批量品目录」并发调度，不要在本对话按品串行。
   - 走脚本、单品：把 Prompt 和 `jobs.json` 写进该品 `_prompts/`（每槽位 slot / prompt_file / size / image），`output_dir` 指向该品成图文件夹，一次 `python scripts/gen_image.py --batch <该品 _prompts>/jobs.json`；失败槽位修正 Prompt 后加 `--skip-existing` 重跑，只补缺的图。
   - 走脚本、多品：工人只写各品 `_prompts/`；调度一次 `python scripts/queue_pack.py --queue <成图根>/_prompts/批次.json --run --skip-existing`（生图单独走，默认并发 32）。
   - 走 Codex/宿主原生生图、单品：Prompt 写入 `_prompts/` 后**立刻按下方「子代理并行」派发**；失败只重派失败槽位。多品则每个品工人自己派槽位，同时最多 2 路。
7. API 或模型不支持某尺寸时，改用最接近的支持尺寸并说明。
8. 未配 API 且宿主也不能原生生图时，只输出完整 Prompt 包，不调用脚本；Prompt 仍按「落盘」写入 `_prompts/`，不要摊在项目根。有 Codex 原生生图就用它，不要因为没有 `.env` 就改成只出 Prompt。
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
7. 一品多色见上方「一品多色」：先定主色，配色合集只出一张。
8. 没有角度词的图当主参考；该槽位没有对得上的源图时，用主参考，不要因为缺背面图就跳槽。
9. 批量品目录里：子文件夹名是品名（或颜色档），图片名才是型号；两者都保留，不要用英文 slug 替换型号。

### 落盘（成图 vs 提示词）

成图和提示词必须分开放。`prompt-H*.txt` 与 `jobs.json` **禁止**写入：源品文件夹、该品成图文件夹（不要和 `h1.png` 混放）、项目根、Skill 目录、`data/`。参考图只引用原路径，不要拷进 `_prompts/`。

**单品**（或未声明批量）：

```text
generated-images/
  <slug>-pdp/                 ← 只放成图
    h1.png
    h2.png
  _prompts/
    <slug>/                   ← 该品提示词工作区（slug 与成图文件夹去掉 -pdp 后一致）
      jobs.json
      prompt-H1.txt
      prompt-H2.txt
```

`jobs.json` 的 `output_dir` 写成 `../../<slug>-pdp`；`prompt_file` 用同目录文件名；`image` 用源图绝对路径。

**批量品目录**：成图仍按下方镜像规则；每个品的 Prompt / `jobs.json` 放在成图根下的 `_prompts/{品文件夹名}/`，文件夹名与源品文件夹逐字相同。`output_dir` 写成 `../../{品文件夹名}`。

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
  双肩包-黑/               ← 只放成图；子文件夹名与源品文件夹逐字相同
    h1.png
    h2.png
  双肩包-米/
    h1.png
  _prompts/                ← 提示词工作区，不要写进上面的品文件夹
    批次.json              ← 整批合同（模板、skip、notes）；进度看磁盘不是看聊天
    双肩包-黑/
      jobs.json
      prompt-H1.txt
    双肩包-米/
      jobs.json
      prompt-H1.txt
```

1. 判定：用户给的路径下面有多个子文件夹、且子文件夹里是图 → 按本规则。用户指定了输出文件夹名则用用户的，否则用 `{大文件夹名}-成图`，建在大文件夹**同级**，不要建在大文件夹里面，不要改源目录里的任何文件。
2. 每个品文件夹单独出一套图，参考图只用该品文件夹里的图。输出写到成图根目录下**同名**子文件夹，名字与源子文件夹完全一致（含中文、空格、连字符），不要改成英文 slug，不要加 `-pdp`。
3. 成图按槽位命名（`h1.png`、`h2.png`…）放进该品输出子文件夹。Prompt / `jobs.json` 放进成图根下 `_prompts/{同名品文件夹}/`，不要放进源品文件夹，也不要和 `h1.png` 放一起。已有同名成图文件夹就接着用，只写当前品，不要清空别人的子文件夹。
4. **多品并发，不要在本对话按品排队。** 主会话只调度，每个品一个新子代理（独立上下文）。口头要求只问一次，写入 `_prompts/批次.json`。用户只点了其中几个子文件夹 → `only`；某个先不做 → `skip`。
   - 先跑 `python scripts/queue_pack.py --init --source "<源>"`（有命中模板就加 `--template`，有口头要求加 `--notes` / `--skip` / `--only`）。已有批次文件则 `--queue "<成图根>/_prompts/批次.json"` 看状态。
   - `--next` 给出下一波品名（默认同时 3 路，最多 8）。立刻派平级子代理，**一品一工人**，把脚本打印的工人任务原文放进子代理；把 `{品名}` 换成该工人的文件夹名。工人返回后立刻再 `--next` 补下一波，不要等全部写完才派。
   - **有 API**：工人只写该品 `_prompts/`（Prompt + `jobs.json`），不要自己 `--batch`。Prompt 波次写完后调度跑 `python scripts/queue_pack.py --queue ... --run --skip-existing`。生图单独走、开大并发（默认 32，写在批次.json 的 `gen_concurrency`，上限 64；429 自动减半）。不要让子 agent 自己调生图。
   - **宿主生图**：工人写完 Prompt 后自己给本品派槽位子代理，同时最多 2 路。失败再 `--next --retry`。
   - 压缩丢了记忆：新开对话，只读 `批次.json` 再 `--next` / `--run`，不要靠上一场聊天。
5. 整批出完再收口一次，不要每个品问一遍要不要建模板。`--next` 显示「全部完成」才收口。

单张图、或只有一个品文件夹且用户没说批量：成图仍用 `generated-images/<slug>-pdp/`，提示词用 `generated-images/_prompts/<slug>/`。

### Codex 原生生图：子代理并行

内置 `image_gen` / 宿主原生生图一次只出一张。**2 个及以上品**时主会话不要给每个品写 Prompt，按上方「批量品目录」派品工人；下面只描述**一个品**内部的槽位并行。

1. 主会话先把全部 Prompt 文件和 `jobs.json` 写进该品 `_prompts/`（见「落盘」），并列出槽位清单（slot、prompt 路径、size、参考图、目标文件名）。批量多品里这一步由该品工人做。
2. **2 张及以上：立刻派平级子代理**，每槽位一个。单品同时最多 4 路；批量多品里每个品工人同时最多 2 路。多出来的分波排队。1 张由当前会话自己出。不要等用户说「开子代理」。
3. 每个子代理只出自己那个槽位：从 `_prompts/` 读对应 Prompt、按源文件名选参考图、用宿主原生生图、把成图存到该品**成图目录**的 `<slot>.png`（如 `h1.png`），返回绝对路径。`lock=master` 必须同时附上该槽母版图和产品图。沿用原 Prompt，不要改成 SVG/HTML/占位图，不要把 txt 写进成图目录，不要覆盖其他槽位的文件。
4. 用宿主的平级子代理派发（Codex Desktop 子代理、Cursor / Claude Code 的 Task 等）。已经在 Codex 会话里就派 Desktop 子代理，不要再套一层 `codex exec`。某路结束立刻收下路径并关掉，空出位置给下一波。
5. 部分失败其余照常留下；只重派失败槽位。宿主没有子代理时，当前会话按同一目录和文件名把槽位连续出完。

---

## QA 检查

最终输出前确认：

- [ ] 材料含糊时已用白话对齐做法（见「意图引导」），没有把成品套图误当成规则去重画，也没有把情绪板当成换货母版
- [ ] 开做前已跑 `match_pack.py`，把前 3 名（第 1 个最优，含将用模板和场景）展示给用户；点名不在库里时没有改成白底主图充数；用户说没有则按第 1 名做并写进汇报
- [ ] `lock=rules` 已按「模板大于情景」组装：情景骨架 + 模板 brand/text_rules/generation + 槽位 overrides；同名字段没有跟情景折中
- [ ] 只命中情景、没有模板时，才整份按情景执行
- [ ] 模板在甲方文件夹里则已读 `要求.json`，该模板文件夹名在 `templates` 里，再读模板 JSON；零散模板只读它自己
- [ ] 所用模板文件夹里有图：`lock=master` 每槽母版存在，每槽参考为母版+产品图，未点名字段未改，缺角度未硬贴；`lock=rules` 至少一张示例，写 Prompt 时看过，没有拿它当母版换货
- [ ] `lock=rules` 多图任务已建 Style Lock 且每张开头一致（换货不建 Style Lock）
- [ ] `lock=rules` 商品/营销任务已做转化驱动力诊断（换货跳过）
- [ ] 颜色全部 hex、占比和留白有数字、否定清单具体
- [ ] 图内文字短且必要，符合模板 `text_rules`（没有才用情景）
- [ ] 一品多色已锁主色，其他颜色只出现在一张配色合集上
- [ ] 批量品目录已在大文件夹同级建 `{名}-成图`，子文件夹名与源品文件夹一致，没有写进源目录
- [ ] 2 个及以上品：已写 `_prompts/批次.json`，主会话只调度，已用 `queue_pack.py --next` 一品一工人并发派发；有 API 则工人只写 Prompt、调度 `--run`，没有每品叠乘 `--batch`；没有在本对话按品串行出图
- [ ] Prompt / `jobs.json` 已写入 `_prompts/`（单品：`generated-images/_prompts/<slug>/`；批量：`{名}-成图/_prompts/{品}/`），没有写进源品文件夹、成图文件夹或项目根
- [ ] 走 Codex/宿主原生生图：单品槽位同时最多 4 路；批量多品每个品工人槽位同时最多 2 路。成图按槽位落在输出目录
- [ ] 出图后按对应 pitfalls 检查通过（有模板：先该模板 + 槽位 overrides，再所引情景且不与模板冲突；仅情景：所引情景；换货对照母版 + 该模板 pitfalls）
- [ ] UGC / 社媒 / 直播场景已应用 `anti_ai_tips`
- [ ] 文件和输出中没有 API key 或私密凭据
- [ ] 出图发现问题已按「坑跟谁走」询问用户是否回流沉淀
- [ ] 一套品出完已按第 9 步收口：定制模板问对照改模板，否则问是否新建；用户说要则已转入 `CREATE_TEMPLATE.md`（先建夹、先拷图、再写 JSON，没有空 JSON 登记）

---

## 翻车回流（沉淀机制）

出图发现问题后，按"坑跟谁走"分层沉淀，并**主动询问用户是否回流**：

| 坑的类型 | 判断 | 沉淀到 |
|---|---|---|
| 拍法的坑（换个客户也会踩） | 影响这一类图 | 所引情景的 `pitfalls`。模板已经覆盖过的数值不要写回情景 |
| 品牌的坑（只跟这个甲方有关） | 影响该甲方所有品 | `要求.json` 的 `style` / `brand` / `language` / `generation` |
| 某一品模板的坑 | 只影响这一套图 | 该槽位的 `overrides` 或该模板 `pitfalls` / `text_rules` |
| 母版换货的坑 | 影响这一套换货 | 换该槽母版图，或改 `product_ref` / `editable_fields` / 该模板 `pitfalls`；不要改成规则 overrides，不要回情景 |
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
| 一品多色每张换色 | 锁一个主色出套图，其他颜色只放进一张合集 |
| 图内文字乱码 | 放大检查，乱码整张重出 |
| Prompt 写进品文件夹或项目根 | 只写入 `_prompts/`，源品文件夹和成图文件夹只放图 |
| 多品在同一对话里一个一个做 | 写 `批次.json`，`queue_pack.py --next` 一品一工人并发；有 API 用 `--run` 全局出图 |
| 多品各开一套 `--batch` 叠乘并发 | 工人只写 jobs.json，调度一次 `--run` |
| 有模板却按情景默认出图 | 模板写了的覆盖情景；不要折中，不要改情景迁就这一套 |
| 有母版却按情景重画 | 只换品；母版是锁；jobs.image = [母版, 产品图] |
| 未点名却改了母版上的字 | 政策 C：只有 editable_fields 且本轮给了新值才改 |
| 缺角度用正面硬贴 | 问用户或跳过该槽 |
| 用户说「按模板整」却直接新画或直接换品 | 走「意图引导」：成品套图+产品图先问；推荐换品；字默认不动 |
| 点名的模板不在库里却出一张白底主图 | 跑 match_pack.py，把前 3 名给用户看，按第 1 名做 |

场景特化的翻车点见各情景 `pitfalls` 字段，出图后必须对照检查。
