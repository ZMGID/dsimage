# dsimage 安装与配置指南

> 本文件供 AI Agent 读取并执行（自动安装 / 首次配置）。用户只需把本文件的 URL 或路径交给 Agent，例如：
> `Install and configure dsimage by following the instructions at: https://raw.githubusercontent.com/ZMGID/dsimage/main/skills/dsimage/SETUP.md`

你（Agent）正在为用户安装和配置 dsimage 电商图片生成 Skill。严格按以下流程执行，根据每一步的结果决定下一步。

用户要求的是**更新**已安装的 dsimage（说「更新 dsimage / 升级 dsimage / 按 SETUP.md 更新」）时，跳过第 1-6 步，直接执行第 7 节「更新已安装的 dsimage」。

## 1. 安装 Skill

1. 获取仓库：已克隆到本地则直接用本地路径；否则执行 `git clone https://github.com/ZMGID/dsimage.git`。
2. 根据用户使用的 Agent，把 `skills/dsimage/` 复制到对应技能目录：

| Agent | 项目级（仅当前项目） | 全局（所有项目） |
|---|---|---|
| Claude Code | `<项目>/.claude/skills/` | `~/.claude/skills/` |
| Codex CLI | `<项目>/.codex/skills/` | `~/.codex/skills/` |
| Cursor | `<项目>/.cursor/skills/` | `~/.cursor/skills/` |
| OpenClaw | `<工作区>/skills/` | `~/.openclaw/skills/` |

3. 目标位置已有 `SKILL.md`（或 `.env`）时，这是已安装目录：**转入第 7 节原地更新**。禁止改名备份后整目录覆盖，禁止重新收集 API。
4. 生图脚本只需 Python 3.10+ 标准库，无第三方依赖，无需 pip install。交付压图（`queue_pack.py --deliver`）可选：`pip install pillow`。

## 2. 让用户选择出图方式

安装完成后**必须停下来**，把下面三个选项原样列给用户，等用户明确回答后再继续。不要自行默认、不要只问「是否配置 API」。

**选项 1 和选项 2 不是二选一，可以同时选。** Codex 账号登录已经能直接生图；图片 API 通常额度更高、并发也更高，适合整套批量出图。账号登录的同事如果要跑套图，建议 1 和 2 一起开。

请用户回复编号，例如 `1`、`2`、`1 和 2`、`3`：

```text
请选择出图方式（1 和 2 可同时选）：

1. Codex 账号登录使用 — 用 Codex 原生生图，不配 API 也能出图
2. 配置生图 API — 走脚本出图，额度/并发通常更高；可与选项 1 一起选
3. 什么都不配置 — 只输出 Prompt，不出图
```

分支：

| 用户选择 | 下一步 |
|---|---|
| 只选 1 | 跳到第 6 步。不要再索要 API。告知：之后出图走 Codex 原生生图，多图会主动开子代理并行；铺很多型号、要高并发生图时建议加上选项 2。若以后要补 API，随时可以说「按 SETUP.md 补配生图 API」 |
| 只选 2，或 1 和 2 都选 | 继续第 3 步配置 API |
| 只选 3 | 跳到第 6 步。告知：当前只出 Prompt；之后仍可补选 1 或 2 |

若当前对话看起来就是 Codex，可在选项下面加一句「你现在很像选项 1 的环境，需要批量高并发时建议加上选项 2」，但**仍必须等用户选**，不要替他决定。

## 3. 选服务商，只收 API key（官方 URL 已写死）

**禁止向用户索要官方服务商的 URL。** OpenAI / Grok / Gemini 的地址写死在下表和 `scripts/gen_image.py` 里；官方三家**不要**把 URL 写入 `.env`（写了脚本也会忽略）。

先把下面四个选项原样列给用户，等编号：

```text
请选生图服务商（官方地址已写死，不用填 URL）：

1. OpenAI
2. Grok（xAI）
3. Gemini（Google）
4. 其他兼容网关（才需要填地址，如 apimart）
```

| 用户选择 | 写入 `.env` 的 `IMG_PROVIDER` | 地址 |
|---|---|---|
| 1 | `openai` | 脚本内 `https://api.openai.com/v1`，不要写入 `.env` |
| 2 | `grok` | 脚本内 `https://api.x.ai/v1`，不要写入 `.env` |
| 3 | `gemini` | 脚本内 `https://generativelanguage.googleapis.com/v1beta`，不要写入 `.env` |
| 4 | `custom` | 这时才问用户要根地址，写入 `IMG_BASE_URL` |

然后**只问 API key**。官方三家不要问 URL、不要问「接口地址填哪个」。

安全规则（必须遵守）：

- API key 只允许写入 `.env`，不得回显到对话、写入日志、README、脚本或任何其他文件。
- 需要向用户确认 key 时，只显示前 6 位和总长度。
- 用户在对话中直接粘贴 key 属于正常输入，不要中断流程，收下后立即进入选模型。

## 4. 让用户选 IMG_MODEL

官方三家用下面的内置名单，以编号列出，标出推荐项。**不要**再请求 `/models` 来凑名单。用户说名单里没有的，才让他直接打模型名。

**OpenAI**

1. `gpt-image-2`（推荐）
2. `gpt-image-1.5`
3. `gpt-image-1`
4. `dall-e-3`

**Grok**

1. `grok-imagine-image-2.0`（推荐）
2. `grok-imagine-image`

**Gemini**

1. `gemini-3.1-flash-image`（推荐）
2. `gemini-2.5-flash-image`
3. `gemini-3-pro-image-preview`

只有选了「4. 其他兼容网关」才拉模型列表：

```
GET {IMG_BASE_URL}/models
Authorization: Bearer {IMG_API_KEY}
```

从 `data[].id` 筛图像模型（ID 通常含 `image`、`dall-e`、`flux`、`seedream`、`grok-imagine`、`gemini`、`stable-diffusion`、`sd3`、`imagen`）；看不出用途的可列出但标注「用途未知」。失败时：

- `404`：可能不提供 `/models`，或根地址缺 `/v1` —— 末尾补 `/v1` 后重试一次；
- `401`：key 无效，请用户检查后重试；
- 仍然失败：请用户直接输入模型名。

## 5. 写入配置并验证

1. 把 `.env` 写入 **Skill 自己的目录**（刚安装的 `.../skills/dsimage/.env`，与 SKILL.md 同级）。这样配置随 Skill 全局生效——换会话、换项目、换工作目录都可用。**不要**写进某个会话的临时工作目录或"当前项目"，否则其他对话找不到配置。若用户日后想按项目覆盖，可在该项目根目录另放一份 `.env`（优先级更高）。

官方三家按第 3 步的表写入（**不要写 IMG_BASE_URL**，地址由脚本写死；填了也会被忽略）：

```dotenv
IMG_PROVIDER=<openai 或 grok 或 gemini>
IMG_MODEL=<第 4 步用户选择的模型>
IMG_API_KEY=<第 3 步收集的 key>
```

其他兼容网关：

```dotenv
IMG_PROVIDER=custom
IMG_BASE_URL=<用户提供的地址>
IMG_MODEL=<第 4 步用户选择的模型>
IMG_API_KEY=<第 3 步收集的 key>
```

2. 询问用户是否生成一张测试图验证配置（会真实调用 API，产生少量费用，须先征得同意）：

```bash
# Windows 用 python，macOS/Linux 用 python3
python <技能目录>/dsimage/scripts/gen_image.py \
  --prompt "a single red apple on pure white background, studio lighting" \
  --size 1:1
```

3. 成功 → 向用户报告生成文件路径；失败 → 按报错排查（`401` = key 有误、`404` = 地址或模型名有误、超时 = 网络），修正后最多重试一次。

## 6. 收尾汇报

先确认安装结果（短）：

- Skill 装在哪（具体路径）
- 出图方式按用户刚才的选择说：1 Codex 原生生图 / 2 已配生图 API（不回显 key）/ 两者都开 / 3 只出 Prompt
- 以后要补配 API：说「按 SETUP.md 配置生图 API」，或改 Skill 目录里的 `.env`

然后**必须用下面这段人话告诉用户怎么用**，不要展开成长教程，不要改写成长篇：

```text
怎么用，就三件事。开口最好带上「使用 dsimage」，这样才会走这套技能。

套模板时写成：使用 dsimage 模板：箱包单品报价模板

1. 出一套（单品）
把产品图丢过来，能给的信息一起给，再说一句要什么。例如：「使用 dsimage 模板：箱包单品报价模板，基于这张图出全套」。会先给你 3 个方案，回 1 或说没有要求就开始。单品多图走脚本 --batch（默认 9 路并发）。一套出完会问要不要改模板或新建模板。

2. 铺很多套（大文件夹）
甲方一个大文件夹（一编号一夹，或几个编号一夹、文件名带商品号）。例如：「使用 dsimage 模板：箱包单品报价模板，把这个文件夹出一套」。成图默认同级「生成」根，一编号一夹（套图 + 白图）。要求只问一次，写进成图根 _prompts/批次.json。主会话只调度：每个品一个子代理写 Prompt；生图单独 queue_pack --run（默认 32 路）。不要在一条聊天里一个品做完再接下一个。

3. 同类品做模板
同一类货要反复出，就说「使用 dsimage，按这些参考图/PDF 做一个模板」。还没有定稿套图 → 按规则画（文件夹里至少一张示例图）；已经有成品套图、后面只换型号 → 拷进模板夹当母版。哪里不对直接说，改的是这个品牌模板。
```

## 7. 更新已安装的 dsimage（非首次安装）

用户要求更新时执行本节，**跳过第 1-6 步**。更新不是重装：

- 禁止把已装目录改名备份再整份拷入
- 禁止重新列出出图方式、禁止重新索要或改写 API key
- 禁止读取、回显、复制、删除 `.env`
- 禁止删除已装目录里多出来的文件（自建模板/情景原位保留）

密钥、自建模板/情景、以及写进内置文件的沉淀（`pitfalls` / 槽位 `overrides` / `text_rules`）必须留在原地。

1. 定位已安装目录（按第 1 步的目录表逐个找；找不到就问用户装在哪）。下面称 `<已装>`。多处都有就每一处都更新。
2. 获取最新代码：本地已有克隆仓库则进入该目录 `git pull`；没有则 `git clone https://github.com/ZMGID/dsimage.git`。下面称 `<新版>` = 仓库里的 `skills/dsimage/`。
3. 若 `<已装>` 就是 `<新版>`（用户直接在仓库技能目录里用），`git pull` 已经完成更新。确认 `.env` 仍在（如果本来就有），跑第 5 步校验，不要再拷贝一遍。
4. 否则在已装目录上**原地覆盖**（Windows 用 `python`，macOS/Linux 用 `python3`）：

```bash
python <新版>/scripts/update_skill.py --source <新版> --dest <已装>
```

脚本会：覆盖 SKILL.md / 脚本 / 规范 / 内置情景与模板；**跳过 `.env`**；**不删用户自建模板/情景**（新版仓库里没有的文件原位保留，并补登记到 SKILL.md 匹配表）；把已装里写进内置文件的沉淀合并进新版 JSON。看输出确认出现「保留 .env」或「已装目录没有 .env」，以及「保留用户文件 …」。若出现「跳过 … 文件名冲突」，用户那份模板没被改。
5. 运行 `python <已装>/scripts/check_scenes.py`，必须全部通过；不通过就修（常见问题：自建模板漏登记、其 pack 引用的自建情景还在）。
6. 收尾汇报（短）：更新了哪几个已装目录、脚本报告里保留了什么（`.env` 只说「在/不在」，不回显内容）、合并了哪些沉淀、校验结果。不要让用户再选一次出图方式。
