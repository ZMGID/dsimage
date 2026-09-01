# Dsimage

**给 AI 装一个电商美工。**

Dsimage 是一个电商视觉创作 Skill，装进 Claude Code / Codex / OpenClaw 后，开口带上「使用 dsimage」：

```text
使用 dsimage 来制作，基于 data/shirt.jpg 生成 Amazon 详情页全套图片
使用 dsimage 模板：箱包单品报价模板，基于这张图出全套
使用 dsimage 模板：某某，按这套样图换货，把这个型号换进去
```

它就会按模板出一套图。模板只有一种：JSON 里的 `lock` 决定按品牌规则生成（`rules`），还是对着已有母版套图只换产品（`master`）。换货时未点名的字和版式不动，适合同一系列很多型号。

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

选了 2 之后选服务商（OpenAI / Grok / Gemini 地址已写死，不用填 URL）→ 只填 API key → 从内置名单选模型 → 写入 `.env`，并可生成测试图验证。

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

装好之后就三件事。开口最好带上「使用 dsimage」，套模板写成「使用 dsimage 模板：某某模板」。

**1. 出图**  
把产品图丢过来，能给的信息一起给（品名、价格、尺寸、卖点、颜色），再说一句要什么，就可以开始。开口之后会先展示准备用的**模板和场景**（自动匹配，最优排第一，一共三个）。回 1 / 2 / 3 换方案，或者说没有要求就按第 1 个开做。原图文件名会参与生图：一般就是型号，正面/背面等也会用来选参考图。缺的会先问一轮，你说先出也行。

如果你同时丢来「一套已经做好的商品图」和「新产品图」，又没说是换货还是按感觉重画，Agent 会先用白话问清（建议换品、字默认不动），避免做成另一套不像的图。一套出完：已经套了定制模板会问要不要对照刚出的图改模板；否则会问要不要给这类货新建模板。

一个大文件夹、下面每个子文件夹一个品时，成图写到大文件夹**同级**的 `{大文件夹名}-成图/`，里面的子文件夹名和原来的品文件夹一样。Prompt 和 `jobs.json` 放在成图根下的 `_prompts/{品名}/`，不写进源品文件夹，也不和 `h1.png` 混放。单品则是 `generated-images/<slug>-pdp/` 放成图、`generated-images/_prompts/<slug>/` 放提示词。

```text
使用 dsimage 来制作，基于这张衣服图做 Amazon 详情页
使用 dsimage 模板：箱包单品报价模板，基于这张图出全套
使用 dsimage 模板：某某，按这套样图换货，把这个型号换进去
使用 dsimage，用这张产品图出 3 张小红书图，要真实拍照感
使用 dsimage 模板：箱包单品报价模板，把这个文件夹里每个子文件夹出一套
```

**2. 同类品做模板**  
同一类货、同一套版式要反复出，就说「使用 dsimage，按这些参考图 / PDF 做一个模板」。还没有定稿套图 → 按规则画（`lock=rules`，文件夹里至少放一张示例图）；已经有一套成品图、后面只换型号 → 把那套图拷进模板文件夹当母版（`lock=master`）。**一份模板一个文件夹**，JSON 和图放一起，整夹才能分享。同一甲方多个品才再套一层甲方文件夹：`要求.json` 的 `templates` 列出这些模板目录名，语言、分辨率、格式、风格写在 `要求.json`，不要再抄进各模板。下次直接套。

**3. 模板会越用越好**  
哪里不对直接说，比如「H5 不该是生活图」「字糊了」「少了拉杆带」。也可以把甲方成品图丢过来，让它对照着改模板。改的是这个品牌模板，下次同类品会跟着变好。

也可以不经过对话，直接调生图脚本（Windows 用 `python`，macOS/Linux 用 `python3`）：

```bash
python skills/dsimage/scripts/gen_image.py \
  --prompt "clean product hero image, white background, studio lighting" \
  --size 1:1 --image data/product.jpg
```

多图套图用**批量模式**一次并发生成（比逐张串行快得多）：

```bash
python skills/dsimage/scripts/gen_image.py --batch generated-images/_prompts/backpack/jobs.json
```

`jobs.json` 必须放在该品 `_prompts/` 目录（相对路径相对清单文件所在目录）：

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

输出按槽位命名（`h1.png`、`h2.png`…），进 `generated-images/backpack-pdp/`。Prompt 留在 `_prompts/backpack/`，不要放进品文件夹。母版换货把 `image` 写成数组：先母版路径，后产品图。个别槽位失败不影响其余槽位；修正后加 `--skip-existing` 重跑同一命令，只会补生成缺的图。

脚本参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--prompt` / `--prompt-file` / `--batch` | Prompt 来源或批量清单，三选一必填 | — |
| `--concurrency` | 批量起始并发；429/超时自动 8→4→2→1 回退 | `8` |
| `--skip-existing` | 批量模式跳过输出已存在的槽位（失败重跑用） | 关 |
| `--size` | 画幅比例：`1:1`、`2:3`、`16:9` 等 14 种 | `1:1` |
| `--resolution` | 分辨率档位 `1k` / `2k` / `4k`（4K 仅 6 种宽幅） | `1k` |
| `--image` | 参考图路径，可重复。母版换货：先母版后产品图 | 无 |
| `--output-dir` | 图片输出目录 | `generated-images` |
| `--env-file` | 指定 `.env` 路径（默认向上查找含 `IMG_` 配置的 `.env`，兜底 Skill 目录） | 自动 |
| `--mode` | `sync` / `async` / `grok` / `gemini`，按服务商自动检测 | 自动 |
| `--format` | `png` / `jpeg` / `webp` | `png` |

异步模式另有 `--poll-interval`（默认 5 秒）、`--timeout`（1k/2k 默认 180 秒，4k 默认 480 秒）；同步模式支持 `--quality`（low/medium/high）和 `--n`（生成数量）。

## 项目结构

```
dsimage/
├── skills/dsimage/          # Skill 本体
│   ├── SKILL.md             # 技能定义与通用流程
│   ├── SETUP.md             # 安装配置指南（Agent 读取）
│   ├── CREATE_TEMPLATE.md   # 模板创建流程（Agent 读取）
│   ├── scripts/             # gen_image.py 生图 + match_pack.py 匹配前三 + check_scenes.py 校验 + update_skill.py 原地升级
│   └── references/
│       ├── scenes/         # 26 个内置情景 + _SCENE_SPEC.md 情景规范
│       └── templates/
│           ├── _TEMPLATE_SPEC.md
│           ├── 01-默认电商模板/          # 整夹复制即可分享/移动；至少一张示例图
│           │   └── 01-默认电商模板.json
│           └── BeautyU/                 # 同一甲方多个品才建；整夹带走 要求.json + 各模板
│               ├── 要求.json            # templates 列出下面的文件夹名
│               └── 01-箱包单品报价模板/
│                   └── 01-箱包单品报价模板.json  # 图和 JSON 放一起；rules 至少一张示例
├── data/                    # 产品原图目录（自建，放入你的产品图）
├── generated-images/        # 生图输出（运行时自动创建，不入库）
│   ├── <slug>-pdp/          # 该品成图（h1.png…）
│   └── _prompts/<slug>/     # 该品 Prompt + jobs.json，不进成图文件夹
└── .env.example             # API 配置模板
```

## 说明

- 本项目不内置任何 API 密钥；`.env` 已被 gitignore，请勿把 key 提交进仓库或在对话中回显
- 缺价格、尺寸、卖点时先问用户；不补则按假设出图并列出假设。认证/评分/销量用示意占位，不要写成已核实
- 直接生图可以走 Codex 账号登录的原生生图，也可以走 OpenAI / Grok / Gemini 官方接口或其他兼容网关；两者可同时开。已配 API 时套图优先走脚本批量。官方三家不用填 URL。不同服务商对尺寸/分辨率/参考图的支持范围不同

## 许可

MIT
