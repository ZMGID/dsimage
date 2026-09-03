# dsimage

**给 AI 装一个电商美工。**

装进 Claude Code / Codex / Cursor / OpenClaw，开口带「使用 dsimage」。不会用打 `dsimage引导`。

```text
使用 dsimage，这些是产品图，帮我出一套电商主图
使用 dsimage 模板：胜利鹰男款商务背包，版式别动，只把包换成这些新产品
使用 dsimage，用这张产品图给我设计一套亚马逊图
使用 dsimage，把这套已经做好的图做成模板，以后换产品用
使用 dsimage，这是某某甲方的一批货，大文件夹在这，按大类做模板再出图
```

## 三种做法

| | 什么时候 | 谁写 prompt | 速度 |
|---|---|---|---|
| **replace** | 甲方给了一套做好的图，后面很多同类品只换货 | 模板里写死，脚本直出 | 快，一条命令铺一夹 |
| **smart** | 有风格/版式要求，但每个品差别大要单独发挥 | 模板给每槽 brief，Agent 按品写 | 中 |
| **design** | 用户说不用库里的模板，从零定一套 | Agent 再问平台/每张干什么，建成 smart 模板再出 | 慢一点，但下次同类品就有模板了 |

只要一张两张图（出张图、改背景、做张海报）不用模板，直接 `gen`，它就是个带参考图的生图工具。

模板是一个文件夹：`template.json` + 示例图 `h1.png…`，整夹拷走就能分享。smart 出的效果好，一条 `template freeze` 就冻成 replace 模板。

Agent 只做人该做的事：多张图的品挑出白底图、标品类、看图挑毛病、改模板。扫品、组 prompt、并发出图、进度、压交付尺寸都是脚本。

## 安装

把这段发给 AI：

```text
按 https://raw.githubusercontent.com/ZMGID/dsimage/main/skills/dsimage/SETUP.md 安装并配置 dsimage
```

它会问你接口地址和 API key，拉模型列表让你挑（可以推荐，但要你选），试出一张，最后把库里的模板列给你。

或者手动：clone 后把 `skills/dsimage/` 拷到技能目录（`~/.claude/skills/`、`~/.codex/skills/`、`~/.cursor/skills/`、`~/.openclaw/skills/`），在里面跑：

```bash
python scripts/dsimage.py setup env --provider custom --base-url https://xxx/v1 --key ...
# 官方地址（api.openai.com / api.x.ai / generativelanguage.googleapis.com）改成对应 --provider openai|grok|gemini，不用 --base-url
python scripts/dsimage.py setup model <列表里挑的模型>                        # 等人选完再跑；顺手试出一张 + 列模板
```

可选 `pip install pillow`（预览拼图、交付压图）。

更新：`python scripts/dsimage.py update`（`--dry-run` 先看），`.env` 和自建模板不动。

## 直接用脚本

在 `skills/dsimage/` 下（Windows `python`，其他 `python3`）：

```bash
python scripts/dsimage.py template list
python scripts/dsimage.py init --template 胜利鹰男款商务背包 --source "D:/甲方/VE男包系列"
python scripts/dsimage.py set "D:/甲方/VE男包生成" V26008 --front "…/V26008正面.jpg" --back "…/V26008背面.jpg"
python scripts/dsimage.py derive "D:/甲方/VE男包生成" --only V26007   # 品没背面图时先派生一张，看一眼
python scripts/dsimage.py run "D:/甲方/VE男包生成" --only V26007      # 先出一个
python scripts/dsimage.py preview "D:/甲方/VE男包生成" --only V26007
python scripts/dsimage.py run "D:/甲方/VE男包生成"                    # 铺全部；已有的跳过
python scripts/dsimage.py status "D:/甲方/VE男包生成"
python scripts/dsimage.py deliver "D:/甲方/VE男包生成"                # 模板写了交付尺寸时
```

```text
VE男包系列/            ← 甲方源，只读
  V26007-V26010/       ← 一夹多品按文件名商品号拆
  V26025/
VE男包生成/            ← 同级默认成图根
  V26007/h1.png … h9.png + 白图
  _dsimage/batch.json  _dsimage/V26007/jobs.json
```

建模板：`template init <名> --from <样图夹>`（replace）或 `--blank --slots 7 --mode smart`，填 `template.json`，`template check`。字段说明在 `skills/dsimage/guides/make_template.md`。

一个甲方、大文件夹里好几个大类：`template client` 填 `要求.json`，`sort --source … --group 大类=SKU,…` 拷到同级分类根（源夹不改），一类一模板，每类 `run --only` 先出两个。流程在 `skills/dsimage/guides/client.md`。

单张 / 几张：`python scripts/dsimage.py gen "…" --ref a.jpg --ratio 4:5 --name hero [--n 3]`，输出到 `./generated-images/`，prompt 记在 `_dsimage/gen.jsonl` 方便改图。

## 目录

```
skills/dsimage/
  SKILL.md              Agent 入口：分流 + 硬规矩
  SETUP.md              安装 / 配 API（setup）/ 更新（update）
  guides/               howto.md  client.md  replace.md  smart.md  design.md  gen.md  make_template.md
  knowledge/shots.md    26 类电商图拍法速查
  templates/            默认电商套图/  童装套图/  胜利鹰女款…/；同一甲方多套时 {甲方}/要求.json + 模板夹
  scripts/              dsimage.py  core.py  gen_image.py  test_dsimage.py
```

## 说明

- 不内置 API key；`.env` 已 gitignore。
- 分辨率只有 1k / 2k / 4k，接口给多大存多大。交付尺寸走 `deliver`。
- 内置四份模板：`默认电商套图`（smart，不点名模板时用：9 张 + 白图，pt-BR，每页有背景，800×800 ≤2MB）；`童装套图`（smart，六个童装子品类合成一份，用 `set --kind` 区分）；两份胜利鹰商务双肩包（replace，实战打磨过，可当写模板的范本）。

MIT
