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
| OpenClaw | `<工作区>/skills/` | `~/.openclaw/skills/` |

3. 目标位置已有同名目录时，先重命名备份再覆盖。
4. 生图脚本只需 Python 3.10+ 标准库，无第三方依赖，无需 pip install。

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
| 只选 1 | 跳到第 6 步。不要再索要 API。告知：之后出图走 Codex 原生生图；若以后要更高额度/并发，随时可以说「按 SETUP.md 补配生图 API」 |
| 只选 2，或 1 和 2 都选 | 继续第 3 步配置 API |
| 只选 3 | 跳到第 6 步。告知：当前只出 Prompt；之后仍可补选 1 或 2 |

若当前对话看起来就是 Codex，可在选项下面加一句「你现在很像选项 1 的环境，需要批量高并发时建议加上选项 2」，但**仍必须等用户选**，不要替他决定。

## 3. 收集 IMG_BASE_URL 和 IMG_API_KEY

向用户依次索取：

| 变量 | 说明 |
|---|---|
| `IMG_BASE_URL` | OpenAI 兼容 API 根地址，例如 `https://api.openai.com/v1` 或第三方兼容服务 |
| `IMG_API_KEY` | 用户在该服务商的 API 密钥 |

安全规则（必须遵守）：

- API key 只允许写入 `.env`，不得回显到对话、写入日志、README、脚本或任何其他文件。
- 需要向用户确认 key 时，只显示前 6 位和总长度。
- 用户在对话中直接粘贴 key 属于正常输入，不要中断流程，收下后立即进入写文件环节。

## 4. 获取模型列表，让用户选择 IMG_MODEL

1. 请求模型列表：

```
GET {IMG_BASE_URL}/models
Authorization: Bearer {IMG_API_KEY}
```

2. 从响应 `data[].id` 提取全部模型 ID。
3. 筛选出图像生成模型（ID 通常含 `image`、`dall-e`、`flux`、`seedream`、`stable-diffusion`、`sd3`、`imagen` 等）；无法判断用途的模型可以列出但要标注「用途未知」。
4. 以编号列表展示给用户选择；列表中存在 `gpt-image-2` 时标注为推荐。
5. 请求失败时降级处理：
   - `404`：服务商可能不提供 `/models`，或根地址缺少 `/v1` —— 先尝试给 `IMG_BASE_URL` 末尾补 `/v1` 后重试；
   - `401`：key 无效或未授权，请用户检查后重试；
   - 仍然失败：请用户直接输入模型名，并给出常见示例（如 `gpt-image-2`）。

## 5. 写入配置并验证

1. 把 `.env` 写入 **Skill 自己的目录**（刚安装的 `.../skills/dsimage/.env`，与 SKILL.md 同级）。这样配置随 Skill 全局生效——换会话、换项目、换工作目录都可用。**不要**写进某个会话的临时工作目录或"当前项目"，否则其他对话找不到配置。若用户日后想按项目覆盖，可在该项目根目录另放一份 `.env`（优先级更高）：

```dotenv
IMG_BASE_URL=<第 3 步收集的地址>
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

1. 出图
把产品图丢过来，能给的信息一起给（品名、价格、货号、尺寸、卖点、颜色），再说一句要什么，就可以开始。例如：「使用 dsimage 模板：箱包单品报价模板，基于这张图出全套」。缺的会先问一轮，你说先出也行。一套出完：如果已经套了定制模板，会问要不要对照刚出的图改模板；否则会问要不要给这类货新建一个模板。

2. 同类品做模板
同一类货、同一套版式要反复出，就说「使用 dsimage，按这些参考图/PDF 做一个模板」。下次同类品直接套模板，不用从头讲。

3. 模板会越用越好
哪里不对直接说，比如「H5 不该是生活图」「字糊了」「少了拉杆带」。也可以把甲方成品图丢过来，让它对照着改模板。改的是这个品牌模板，下次同类品会跟着变好。
```

## 7. 更新已安装的 dsimage（非首次安装）

用户要求更新时执行本节，跳过第 1-6 步。**铁律：更新不得丢失用户的三样东西——`.env` 配置、自建的模板/情景文件、以及回流沉淀（用户使用过程中写进内置情景 `pitfalls` / 模板槽位 `overrides` / `text_rules` 的条目）。禁止不看差异直接整目录覆盖。**

1. 定位已安装目录（按第 1 步的目录表逐个找；找不到就问用户装在哪）。下面称 `<已装>`。
2. 获取最新代码：本地已有克隆仓库则进入该目录 `git pull`；没有则 `git clone https://github.com/ZMGID/dsimage.git`。下面称 `<新版>` = 仓库里的 `skills/dsimage/`。
3. 覆盖前清点 `<已装>` 中要保留的内容：
   - `.env`（如存在）——原样保留；
   - `references/templates/` 和 `references/scenes/` 下 `<新版>` 里**不存在**的文件——这是用户自建的模板/情景，全部保留；
   - 与 `<新版>` 同名但**内容不同**的内置情景/模板——逐个 diff，把用户沉淀的条目（`pitfalls`、槽位 `overrides`、`text_rules` 等新增项）合并进 `<新版>` 对应文件；拿不准的差异列出来问用户，不要静默丢弃。
4. 把 `<已装>` 重命名为备份（如 `dsimage.bak-20260831`），再把 `<新版>` 复制到原位置。
5. 迁回保留内容：`.env` 放回 Skill 目录（与 SKILL.md 同级）；自建模板/情景文件放回对应子目录，并在新 SKILL.md 的匹配表里各补登记一行（触发词 | 文件名）——校验器会检查漏登记。
6. 运行 `python <已装>/scripts/check_scenes.py`（macOS/Linux 用 `python3`），必须全部通过；不通过就修（常见问题：自建模板漏登记、其 pack 引用的自建情景没迁回）。
7. 收尾汇报：这次更新带来了什么（可用 `git log --oneline` 新旧区间概括）、保留并迁回了哪些用户文件、合并了哪些沉淀条目、校验结果；确认无误后提示用户可删除第 4 步的备份目录。
