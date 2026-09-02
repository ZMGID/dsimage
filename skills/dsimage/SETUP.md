# dsimage 安装与配置

> 给 Agent 读。用户把这份文件的路径或 URL 交给你，例如：
> `按 https://raw.githubusercontent.com/ZMGID/dsimage/main/skills/dsimage/SETUP.md 安装并配置 dsimage`

用户说「更新 dsimage」→ 直接看第 4 节。

## 1. 安装

1. 拿代码：本地已克隆就用本地；否则 `git clone https://github.com/ZMGID/dsimage.git`。
2. 把 `skills/dsimage/` 拷到技能目录：

| Agent | 项目级 | 全局 |
|---|---|---|
| Claude Code | `<项目>/.claude/skills/` | `~/.claude/skills/` |
| Codex CLI | `<项目>/.codex/skills/` | `~/.codex/skills/` |
| Cursor | `<项目>/.cursor/skills/` | `~/.cursor/skills/` |
| OpenClaw | `<工作区>/skills/` | `~/.openclaw/skills/` |

3. 目标位置已有 `SKILL.md` 或 `.env` → 是已装目录，转第 4 节更新，不要覆盖 `.env`。
4. 依赖：Python 3.10+。`pip install pillow`（预览拼图、交付压图、读示例图比例要用；没有也能出图）。

## 2. 配生图 API

出图只走图片 API。让用户选服务商（官方三家地址写死，不问 URL）：

```text
1. OpenAI   2. Grok（xAI）   3. Gemini（Google）   4. 其他兼容网关（才需要地址）
```

然后**只问 API key**。key 只写进 `.env`，不回显、不写日志；要确认就显示前 6 位 + 长度。

模型按服务商给内置名单让用户选，不要去拉 `/models`（只有兼容网关才拉 `GET {IMG_BASE_URL}/models`）：

- OpenAI：`gpt-image-2`（推荐）/ `gpt-image-1.5` / `gpt-image-1` / `dall-e-3`
- Grok：`grok-imagine-image-2.0`（推荐）/ `grok-imagine-image`
- Gemini：`gemini-3.1-flash-image`（推荐）/ `gemini-2.5-flash-image` / `gemini-3-pro-image-preview`

`.env` 写在 **Skill 自己的目录**（和 SKILL.md 同级），这样换项目、换会话都能用。某个项目要另一套配置可在项目根再放一份，优先级更高。

```dotenv
IMG_PROVIDER=grok            # openai | grok | gemini | custom
IMG_MODEL=grok-imagine-image-2.0
IMG_API_KEY=...
# IMG_BASE_URL=https://gateway.example/v1     ← 仅 custom
```

## 3. 验证

```bash
python <技能目录>/scripts/gen_image.py --check          # 不打接口
python <技能目录>/scripts/gen_image.py --check --live   # 真出一张带参考图的试图，会扣费，先问用户
python <技能目录>/scripts/test_dsimage.py                # 单测，不打接口
python <技能目录>/scripts/dsimage.py template list       # 应列出内置模板
python <技能目录>/scripts/dsimage.py template check 胜利鹰男款商务背包
```

`--check` 失败按报错改 `.env`：401 key 错、404 地址或模型名错、超时是网络。

收尾告诉用户三句话：装在哪；出图走哪个服务商 + 模型（不回显 key）；怎么开口：

```text
使用 dsimage 模板：胜利鹰男款商务背包，把这个文件夹的品换进去      ← replace
使用 dsimage 模板：某某，这几个品每个单独写                      ← smart
使用 dsimage，用这张图给我设计一套亚马逊图                        ← design（会先问你几个问题）
使用 dsimage，把这张图换成深灰背景 / 出一张 4:5 的海报            ← gen（只出一张几张，不建模板）
使用 dsimage，按这套样图做个模板                                  ← 建模板
```

## 4. 更新

更新 = 用新版覆盖技能文件，**保留 `.env` 和用户自建模板**。

1. 找到已装目录（按第 1 节表逐个找；找不到就问）。
2. 新代码：本地仓库 `git pull`，或重新 clone。
3. 已装目录就是仓库目录 → `git pull` 已完成。
4. 否则把新版 `skills/dsimage/` 里的 `SKILL.md`、`SETUP.md`、`guides/`、`knowledge/`、`scripts/`、`templates/` 拷过去覆盖同名文件。**不要碰** `.env`；`templates/` 下新版没有的文件夹是用户自建的，原位保留。
5. 跑第 3 节的 `test_dsimage.py` 和 `template check`。汇报：更新了哪些目录、`.env` 在不在（不回显）、校验结果。

从旧版（有 `references/`、`queue_pack.py` 的那版）升级：旧模板格式不兼容，旧的 `references/` 和 `scripts/queue_pack.py` 等可以删；用户自建的旧模板要按 `guides/make_template.md` 重建（prompt 文字可以原样搬）。
