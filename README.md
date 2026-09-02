# Dsimage

**给 AI 装一个电商美工。**

Dsimage 是一个电商视觉创作 Skill，装进 Claude Code / Codex / OpenClaw 后，开口带上「使用 dsimage」：

```text
使用 dsimage 来制作，基于 data/shirt.jpg 生成 Amazon 详情页全套图片
使用 dsimage 模板：箱包单品报价模板，基于这张图出全套
使用 dsimage 模板：某某，按这套样图换货，把这个型号换进去
```

它就会按模板出一套图。模板只有一种：JSON 里的 `lock` 决定按品牌规则生成（`rules`），还是对着已有母版套图只换产品（`master`）。换货时未点名的字和版式不动，适合同一系列很多型号。多个型号用「大文件夹 + 每子文件夹一个品」：子代理并发写 Prompt，生图单独跑，不要在一条聊天里一个一个做。

它和"再要一个 Prompt"的生图玩法有三个区别：

1. **做整套，不做单张** — 内置 26 种情景（主图、生活方式、平铺、模特、直播间、爆炸图、杂志大片……）。`lock=rules` 用 Campaign Style Lock 锁色板和光线；`lock=master` 直接锁母版套图，换型号时只换货。
2. **为转化出图，不为好看出图** — 动手前先诊断产品靠什么打动买家：视觉驱动、痛点驱动还是情感价值驱动，再按对应的转化逻辑规划图片顺序，而不是堆一堆好看但不出单的图。
3. **从 Prompt 到成图一条龙** — Codex 账号登录即可直接出图，不必先配 API；也可以再配 OpenAI / Grok / Gemini 官方接口或其他兼容网关（额度/并发通常更高，适合整套批量）。两者可同时开。未配置时只输出可执行 Prompt。生图脚本纯 Python 标准库，零第三方依赖。

## 安装

dsimage 遵循 Agent Skills 开放标准（一个含 `SKILL.md` 的文件夹），Claude Code / Codex / OpenClaw 都直接支持。

### 方式一：手动安装

```bash
# 1. 克隆仓库
git clone https://github.com/ZMGID/dsimage.git
cd dsimage

# 2. 把 skills/dsimage 复制到你所用工具的技能目录（目录见下表）
mkdir -p .claude/skills && cp -r skills/dsimage .claude/skills/

# 3. 可选：配置 API（Codex 账号登录不配也能生图；要更高额度/并发可再配）
```

各工具的技能目录（`<项目>` 指你的项目根目录 / OpenClaw 工作区）：

| 工具 | 项目级（仅当前项目可用） | 全局（所有项目可用） |
|------|--------------------------|----------------------|
| Claude Code | `<项目>/.claude/skills/` | `~/.claude/skills/` |
| Codex CLI | `<项目>/.codex/skills/` | `~/.codex/skills/` |
| Cursor | `<项目>/.cursor/skills/` | `~/.cursor/skills/` |
| OpenClaw | `<工作区>/skills/` | `~/.openclaw/skills/` |

OpenClaw 也可以在克隆出的仓库目录内用命令安装：`openclaw skills install ./skills/dsimage --as dsimage`。

### 方式二：让 AI 自动安装

把下面这段发给项目里的 AI（Claude Code / Codex 等），它会读取指南，自动完成安装，并让你选择出图方式：

```text
请安装并配置 dsimage，严格按照以下指南执行：
https://raw.githubusercontent.com/ZMGID/dsimage/main/skills/dsimage/SETUP.md
```

已克隆仓库的，直接让 AI 读本地文件 `skills/dsimage/SETUP.md` 即可。

Agent 会按指南执行：安装 Skill → **列出三个选项让你选（1 和 2 可同时选，不是二选一）**：

1. Codex 账号登录使用（用 Codex 原生生图，不配 API 也能出图）
2. 配置生图 API（额度/并发通常更高，适合整套批量；可与 1 一起选）
3. 什么都不配置（只输出 Prompt）

选了 2 之后选服务商（OpenAI / Grok / Gemini 地址已写死，不用填 URL）→ 只填 API key → 从内置名单选模型 → 写入 `.env` → `gen_image.py --check` 把通道收明白（`--image`、参考图上送、`--size`；Grok 一张 `image`、两张 `images`）。可选 `--check --live` 打一张带参考图的试图。之后出套图按技能里的命令加 `--run`。

也可以让 AI 交互式引导配置：让它读 `skills/dsimage/SETUP.md` 执行即可。

### 更新

已安装的用户把下面这句发给 AI 即可。更新是**原地覆盖技能文件**，不是重装：`.env` 密钥原位不动，自建模板/情景不会删，写进内置文件的翻车点会合并进新版。不要整目录备份替换。

```text
请更新 dsimage，严格按照以下指南的「更新」一节执行：
https://raw.githubusercontent.com/ZMGID/dsimage/main/skills/dsimage/SETUP.md
```

已克隆仓库的，先 `git pull`，再让 AI 读本地 `skills/dsimage/SETUP.md` 按「更新」一节执行。

### API 配置（可选）

Codex 账号登录不配也能生图。图片 API 额度/并发通常更高，适合整套批量，**可以和账号登录同时用**。

在 **Skill 目录内**创建 `.env`（仓库里是 `skills/dsimage/.env`；复制安装后则是 `~/.codex/skills/dsimage/.env` 这类路径）。配置随 Skill 全局生效——换会话、换项目都可用；也可以在某个项目根目录另放 `.env`，仅对该项目覆盖：

```dotenv
IMG_PROVIDER=openai
IMG_MODEL=gpt-image-2
IMG_API_KEY=your-api-key-here
```

| 变量 | 说明 |
|------|------|
| `IMG_PROVIDER` | `openai` / `grok` / `gemini` / `custom`。官方三家地址写死，不必填 URL |
| `IMG_MODEL` | 图片模型名。默认：OpenAI `gpt-image-2`，Grok `grok-imagine-image-2.0`，Gemini `gemini-3.1-flash-image` |
| `IMG_API_KEY` | 你的 API 密钥 |
| `IMG_BASE_URL` | 仅 `custom` 兼容网关需要 |

也兼容 `OPENAI_BASE_URL`、`OPENAI_API_BASE`、`OPENAI_MODEL`、`OPENAI_API_KEY`、`XAI_API_KEY`、`GEMINI_API_KEY` 等别名。

## 使用

装好之后对人就三件事：**出一套、铺很多套、收成模板。** 开口带上「使用 dsimage」才会走这套技能。套模板写成「使用 dsimage 模板：某某」。

你不用记 `lock` 这种字段。Agent 只跟你确认结果：和样板同一套版只换货，还是按这种感觉重新画。同时丢来「一套已做好的主图」+「新产品图」时，它会先问一句（推荐换货，字默认不动）。

```text
使用 dsimage 来制作，基于这张衣服图做 Amazon 详情页
使用 dsimage 模板：箱包单品报价模板，基于这张图出全套
使用 dsimage 模板：某某，按这套样图换货，把这个型号换进去
使用 dsimage 替换模板，母版是这套样板图，把这个文件夹里每个型号只换商品
使用 dsimage，用这张产品图出 3 张小红书图，要真实拍照感
使用 dsimage 模板：箱包单品报价模板，把这个文件夹里每个子文件夹出一套
```

### 1. 出一套（单品）

1. 把产品图丢过来，能给的信息一起给（品名、价格、尺寸、卖点、颜色），再说一句要什么。
2. Agent 先展示准备用的 **3 个方案**（第 1 个最优）。回 `1` / `2` / `3` 换方案，或说「没有 / 先出」按第 1 个做。
3. 缺参数会问一轮；你说先出也行。原图文件名会参与生图：一般就是型号，`正面` / `背面` 用来选参考图。
4. Prompt 写到 `generated-images/_prompts/<品名>/`，成图写到 `generated-images/<品名>-pdp/`（`h1.png`…）。
5. **有生图 API**：一次 `gen_image.py --batch`，默认 **9 路并发**（9 张槽位一次铺开）。**没 API、有宿主生图**：槽位子代理并行，单品最多 4 路。
6. 一套出完：已经套了定制模板会问要不要对照改模板；否则会问要不要给这类货新建模板。

### 2. 铺很多套（大文件夹）

甲方一个大文件夹：可能一编号一夹，也可能几个编号一夹（文件名带商品号）。**一品基本一张图**，文件名不带颜色。源目录只读。成图默认同级「生成」根（`VE男包系列` → `VE男包生成`），里面**一个编号一个夹**：模板套图 + 从甲方迁来的那张白图。一夹多品按文件名拆开。Prompt 在成图根 `_prompts/{编号}/`，整批规矩在 `_prompts/批次.json`。

```text
VE男包系列/                 ← 甲方源（只读）
  V26007-V26010/
  V26026/
VE男包生成/                 ← 同级默认
  V26007/h1.png
  V26007/白图
  _prompts/批次.json
```

真实顺序：

1. 匹配方案 + **口头要求只问一次**（只要哪几款、哪个先不做、字动不动），写入 `批次.json`。
2. **替换模板**（和样板同一套版、只换商品）：Agent 看图选出那张商品白图，先出一套；你改到满意后再铺开其余型号，不再一个品写一遍 Prompt。
3. **按规则画**：主会话只调度。`--next` 一次派最多 3 个子代理，**每个子代理只做一个品、只写 Prompt**。不要在一条对话里一个品做完再接下一个。Prompt 写齐后，生图单独走 `queue_pack.py --run`（默认并发 **32**，上限 64；429 自动减半）。
4. 对话被压缩了就新开一条，读 `批次.json` 再接着做。
5. 整批出完再收口一次，不要每个品问一遍要不要建模板。

还没定版不要直接铺 100 个。先按「出一套」做出你签字的那一款，建成带母版的模板，再对文件夹换货。内置「箱包单品报价模板」目前是按规则画（`lock=rules`）；像素级同一套版需要你先有齐套母版图，建成 `lock=master`。

**只换商品、字不动、型号很多**：说「使用 dsimage 替换模板」，给一套样板图 + 大文件夹。Agent 看图选出那张商品白图，按模板出一套；你改到满意后再铺开其余型号。默认一口气出完；要每隔 N 个品停下来检查，说一声。档位、画幅、交付尺寸跟你这轮说的走（没说则跟模板/样板）；比例对不上不会拿宽图压成方。

铺很多型号、要高并发生图：安装时选生图 API（可和 Codex 账号同时开）。只靠宿主一张一张出，并发上不去。

### 3. 同类品做模板

同一类货、同一套版式要反复出，就说「使用 dsimage，按这些参考图 / PDF 做一个模板」。

- 还没有定稿套图 → 按规则画（`lock=rules`，文件夹里**至少一张示例图**，建议 `h1.png`）
- 已经有一套成品图、后面只换型号 → 把那套图拷进模板文件夹当母版（`lock=master`，每槽一张）

**一份模板一个文件夹**，JSON 和图放一起，整夹才能分享。没有真图不要登记。同一甲方多个品才再套一层甲方文件夹：`要求.json` 的 `templates` 列出这些模板目录名。

哪里不对直接说，比如「H5 不该是生活图」「字糊了」「少了拉杆带」。改的是这个品牌模板，下次同类品会跟着变好。

### 直接调脚本

Windows 用 `python`，macOS/Linux 用 `python3`。

单张：

```bash
python skills/dsimage/scripts/gen_image.py \
  --prompt "clean product hero image, white background, studio lighting" \
  --size 1:1 --image data/product.jpg
```

单品多图（默认并发 9）：

```bash
python skills/dsimage/scripts/gen_image.py --batch generated-images/_prompts/backpack/jobs.json
```

`jobs.json` 必须放在该品 `_prompts/`（相对路径相对清单文件所在目录）：

```json
{
  "output_dir": "../../backpack-pdp",
  "defaults": {"size": "1:1", "resolution": "1k", "image": "E:/path/to/data/backpack.jpg"},
  "jobs": [
    {"slot": "H1", "prompt_file": "prompt-H1.txt"},
    {"slot": "H2", "prompt_file": "prompt-H2.txt", "size": "4:5"}
  ]
}
```

输出按槽位命名（`h1.png`、`h2.png`…）。母版换货把 `image` 写成数组：先母版路径，后产品图。失败加 `--skip-existing` 重跑，只补缺的图。

多品：按规则画先建批次、子代理写 Prompt，再一次全局出图（默认并发 32）。替换模板看图选白图，`--pilot` 出一套再 `--blast`：

```bash
python skills/dsimage/scripts/queue_pack.py --init --source "VE男包系列" --notes "字不要改"
python skills/dsimage/scripts/queue_pack.py --queue "VE男包生成/_prompts/批次.json" --next
python skills/dsimage/scripts/queue_pack.py --queue "VE男包生成/_prompts/批次.json" --run --skip-existing

# 替换模板（lock=master 或 --masters）
python skills/dsimage/scripts/queue_pack.py --init --source VE男包系列 --template "<母版模板 JSON>" --masters 样板套图 --category 双肩包
python skills/dsimage/scripts/queue_pack.py --queue "VE男包生成/_prompts/批次.json" --pilot V26026 --run
python skills/dsimage/scripts/queue_pack.py --queue "VE男包生成/_prompts/批次.json" --blast --run --skip-existing
python skills/dsimage/scripts/queue_pack.py --queue "VE男包生成/_prompts/批次.json" --deliver
```

`--next` 打印下一波品名和工人任务原文（主会话拿去派子代理）。`--run` 把各品待出图槽位丢进同一线程池。`--concurrency` 可加大，上限 64。

`gen_image.py` 参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--prompt` / `--prompt-file` / `--batch` | Prompt 来源或批量清单，三选一必填 | — |
| `--concurrency` | 单品批量起始并发；429/超时自动 9→4→2→1 | `9` |
| `--skip-existing` | 跳过输出已存在的槽位（失败重跑用） | 关 |
| `--size` | 画幅比例：`1:1`、`2:3`、`16:9` 等 14 种 | `1:1` |
| `--resolution` | 分辨率档位 `1k` / `2k` / `4k`（4K 仅 6 种宽幅） | `1k` |
| `--image` | 参考图路径，可重复。母版换货：先母版后产品图 | 无 |
| `--output-dir` | 图片输出目录 | `generated-images` |
| `--env-file` | 指定 `.env` 路径（默认向上查找含 `IMG_` 配置的 `.env`，兜底 Skill 目录） | 自动 |
| `--mode` | `sync` / `async` / `grok` / `gemini`，按服务商自动检测 | 自动 |
| `--format` | `png` / `jpeg` / `webp` | `png` |

异步模式另有 `--poll-interval`（默认 5 秒）、`--timeout`（1k/2k 默认 180 秒，4k 默认 480 秒）；同步模式支持 `--quality`（low/medium/high）和 `--n`（生成数量）。

`queue_pack.py` 常用参数：`--init --source` 建 `批次.json`；`--queue` 看状态；`--next` 派品工人（按规则画）；`--run` 生图；`--skip` / `--only` / `--notes` 写入批次；`--workers` 品工人路数（默认 3）；`--concurrency` 覆盖生图并发。替换模板用 `--template`（`lock=master`）或 `--masters`，再 `--pilot` / `--blast` / `--deliver`；`--resolution`、`--output-size` / `--max-px` / `--max-bytes`、`--inspect-every` 按当轮填，不要当固定默认值抄。

---

## 项目结构

```
dsimage/
├── skills/dsimage/          # Skill 本体
│   ├── SKILL.md             # 技能定义与通用流程（Agent 读）
│   ├── SETUP.md             # 安装配置指南（Agent 读取）
│   ├── CREATE_TEMPLATE.md   # 模板创建流程（Agent 读取）
│   ├── scripts/             # gen_image.py 生图 + queue_pack.py 多品队列 + swap_fast.py 换货填 jobs + match_pack.py 匹配前三 + check_scenes.py 校验 + update_skill.py 原地升级
│   └── references/
│       ├── scenes/         # 26 个内置情景 + _SCENE_SPEC.md 情景规范
│       └── templates/
│           ├── _TEMPLATE_SPEC.md
│           ├── 01-默认电商模板/          # 整夹复制即可分享；lock=rules 至少一张示例图
│           │   └── 01-默认电商模板.json
│           └── BeautyU/                 # 同一甲方多个品才建；整夹带走 要求.json + 各模板
│               ├── 要求.json            # templates 列出下面的文件夹名
│               └── 01-箱包单品报价模板/
│                   └── 01-箱包单品报价模板.json
├── data/                    # 产品原图目录（自建，放入你的产品图）
├── generated-images/        # 单品输出（运行时自动创建，不入库）
│   ├── <slug>-pdp/          # 该品成图（h1.png…）
│   └── _prompts/<slug>/     # 该品 Prompt + jobs.json
└── .env.example             # API 配置模板
```

大文件夹批量时，成图在源目录**同级**的「生成」根（`VE男包系列` → `VE男包生成`），一编号一夹（套图 + 白图），不要写进源目录，也不要用 `generated-images/`。

## 说明

- 本项目不内置任何 API 密钥；`.env` 已被 gitignore，请勿把 key 提交进仓库或在对话中回显
- 缺价格、尺寸、卖点时先问用户；不补则按假设出图并列出假设。认证/评分/销量用示意占位，不要写成已核实
- 模板文件夹必须带图：`lock=rules` 至少一张示例；`lock=master` 每槽一张母版。没有真图不要登记
- 直接生图可以走 Codex 账号登录的原生生图，也可以走 OpenAI / Grok / Gemini 官方接口或其他兼容网关；两者可同时开。已配 API 时套图优先走脚本。官方三家不用填 URL。不同服务商对尺寸/分辨率/参考图的支持范围不同
- Agent 流程以 `skills/dsimage/SKILL.md` 为准；安装以 `SETUP.md` 为准；建模板以 `CREATE_TEMPLATE.md` 为准

## 许可

MIT
