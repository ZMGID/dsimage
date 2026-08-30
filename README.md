# Dsimage

面向 Claude Code / Codex / OpenClaw 等 AI 编程助手的**电商视觉创作 Skill**。输入产品图和一句需求，自动生成电商主图、Amazon/Shopify 详情页全套、社媒推广图、直播间场景图等完整视觉素材。

- **25 个场景模板**：白底主图、生活方式、平铺、细节特写、海报、社媒、UGC、模特、前后对比、包装、信息图、尺码、多品组合、直播间、虚拟试穿、爆炸图、隐形人台、多角度、杂志、季节、轻奢、设备样机、店铺陈列、运动 Campaign 等
- **Campaign Style Lock**：多图任务自动锁定色板、冷暖调、字体、背景、光线，保证整套图风格一致
- **转化驱动**：先诊断产品是视觉驱动 / 痛点驱动 / 情感价值驱动，再按转化逻辑规划图片序列（如 Amazon PDP 默认 5 张主图 + 9 张详情页）
- **双模式**：未配置 API 时输出视觉简报和可执行 Prompt；配置任意 OpenAI 兼容图片 API 后直接出图
- **零依赖**：生图脚本纯 Python 标准库，无需安装第三方包

## 安装

dsimage 遵循 Agent Skills 开放标准（一个含 `SKILL.md` 的文件夹），Claude Code / Codex / OpenClaw 都直接支持。

### 方式一：手动安装

```bash
# 1. 克隆仓库
git clone https://github.com/ZMGID/dsimage.git
cd dsimage

# 2. 把 skills/dsimage 复制到你所用工具的技能目录（目录见下表）
mkdir -p .claude/skills && cp -r skills/dsimage .claude/skills/

# 3. 配置 API（见下节），重启工具即可使用
```

各工具的技能目录（`<项目>` 指你的项目根目录 / OpenClaw 工作区）：

| 工具 | 项目级（仅当前项目可用） | 全局（所有项目可用） |
|------|--------------------------|----------------------|
| Claude Code | `<项目>/.claude/skills/` | `~/.claude/skills/` |
| Codex CLI | `<项目>/.codex/skills/` | `~/.codex/skills/` |
| OpenClaw | `<工作区>/skills/` | `~/.openclaw/skills/` |

OpenClaw 也可以在克隆出的仓库目录内用命令安装：`openclaw skills install ./skills/dsimage --as dsimage`。

### 方式二：让 AI 自动安装

把下面这段提示词发给项目里的 AI（Claude Code / Codex 等），它会自己读 README 完成安装：

```text
请为我安装 dsimage 电商图片生成 Skill：

1. 获取仓库 https://github.com/ZMGID/dsimage（已克隆到本地则直接用本地路径）。
2. 阅读仓库根目录 README.md 的「安装」一节，按说明把 skills/dsimage 安装到你正在使用的 Agent 技能目录（Claude Code / Codex / OpenClaw 任一）；如目标位置已有同名 Skill，先备份再覆盖。
3. 生图配置见 README 的「API 配置」一节：IMG_BASE_URL、IMG_MODEL、IMG_API_KEY。不要向我要 API key，也不要把 key 写进任何文件或对话，留占位符即可，我自己填。
4. 安装完成后告诉我：这个 Skill 怎么触发、支持哪些场景、还缺什么配置。
```

### API 配置

在项目根目录或 `skills/dsimage/` 下创建 `.env`：

```dotenv
IMG_BASE_URL=https://api.apimart.ai/v1
IMG_MODEL=gpt-image-2
IMG_API_KEY=your-api-key-here
```

| 变量 | 说明 |
|------|------|
| `IMG_BASE_URL` | OpenAI 兼容 API 根地址 |
| `IMG_MODEL` | 图片模型名（如 `gpt-image-2`） |
| `IMG_API_KEY` | 你的 API 密钥 |

也兼容 `OPENAI_BASE_URL`、`OPENAI_API_BASE`、`OPENAI_MODEL`、`OPENAI_API_KEY` 等常见别名。

## 使用

安装后在 Claude Code 里用自然语言直接说：

```
基于 data/产品图.jpg 生成 Amazon 详情页全套图片
```

```
用 data/产品图.jpg 生成 3 张 Twitter/X 推广帖，风格要真实手机拍照感
```

```
为我的护肤品设计一张白底主图 Prompt      # 未配置 API 时只出 Prompt，不出图
```

也可以不经过 Skill，直接调用生图脚本：

```bash
python3 skills/dsimage/scripts/generate_image.py \
  --prompt "clean product hero image, white background, studio lighting" \
  --size 1:1 --resolution 2k --image data/product.jpg
```

全部脚本参数（比例、分辨率、参考图、轮询、超时等）见 [skills/dsimage/README.md](skills/dsimage/README.md)。

## 项目结构

```
dsimage/
├── skills/dsimage/          # Skill 本体：SKILL.md + 25 个场景模板 + 生图脚本
├── docs/                    # API 文档、教程笔记、演示截图
├── generated-images/        # 生图输出目录（运行时自动创建，不入库）
└── .env.example             # API 配置模板
```

## 说明

- 本项目不内置任何 API 密钥；`.env` 已被 gitignore，请勿把 key 提交进仓库或在对话中回显
- 营销图中的效果承诺必须有真实证据支持，Skill 不虚构认证、数据或评价
- 直接生图依赖 apimart.ai（异步轮询模式）或任意 OpenAI 兼容 Images API，不同服务商对尺寸/分辨率/参考图的支持范围不同

## 许可

MIT
