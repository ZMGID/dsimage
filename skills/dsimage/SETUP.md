# dsimage 安装与配置指南

> 本文件供 AI Agent 读取并执行（自动安装 / 首次配置）。用户只需把本文件的 URL 或路径交给 Agent，例如：
> `Install and configure dsimage by following the instructions at: https://raw.githubusercontent.com/ZMGID/dsimage/main/skills/dsimage/SETUP.md`

你（Agent）正在为用户安装和配置 dsimage 电商图片生成 Skill。严格按以下流程执行，根据每一步的结果决定下一步。

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

## 2. 询问是否配置生图 API

安装完成后，必须询问用户：

> 是否现在配置生图 API？配置后可直接出图；也可以跳过，Skill 会以 Prompt 模式工作（只输出提示词，不出图）。

- 用户暂不配置 → 跳到第 6 步收尾，并告知随时可以让 Agent 按本文件重新配置。
- 用户确认配置 → 继续第 3 步。

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
python3 <技能目录>/dsimage/scripts/gen_image.py \
  --prompt "a single red apple on pure white background, studio lighting" \
  --size 1:1
```

3. 成功 → 向用户报告生成文件路径；失败 → 按报错排查（`401` = key 有误、`404` = 地址或模型名有误、超时 = 网络），修正后最多重试一次。

## 6. 收尾汇报

最后向用户确认：

- Skill 安装位置（具体技能目录路径）。
- 配置状态：已配置（不回显 key）或暂未配置。
- 使用方式：之后用自然语言直接描述需求即可触发，例如「基于 data/product.jpg 生成 Amazon 详情页全套图片」。
- 修改配置：编辑 Skill 目录内的 `.env` 即可（全局生效，改完无需重启）；某项目根目录若也存在 `.env`，该项目优先使用自己的。
