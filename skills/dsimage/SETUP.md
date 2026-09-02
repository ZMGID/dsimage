# dsimage 安装与配置

> 给 Agent 读。用户把这份文件的路径或 URL 交给你，例如：
> `按 https://raw.githubusercontent.com/ZMGID/dsimage/main/skills/dsimage/SETUP.md 安装并配置 dsimage`

用户说「更新 dsimage」→ 直接看第 4 节。
下面所有命令都在**技能目录**跑（Windows `python`，macOS/Linux `python3`）。

## 1. 装文件

1. 拿代码：本地已克隆就用本地；否则 `git clone https://github.com/ZMGID/dsimage.git`。
2. 把 `skills/dsimage/` 拷到技能目录：

| Agent | 项目级 | 全局 |
|---|---|---|
| Claude Code | `<项目>/.claude/skills/` | `~/.claude/skills/` |
| Codex CLI | `<项目>/.codex/skills/` | `~/.codex/skills/` |
| Cursor | `<项目>/.cursor/skills/` | `~/.cursor/skills/` |
| OpenClaw | `<工作区>/skills/` | `~/.openclaw/skills/` |

3. 目标位置已有 `SKILL.md` 或 `.env` → 是已装目录，转第 4 节更新，不要覆盖 `.env`。
4. Python 3.10+。`pip install pillow`（预览拼图、交付压图要用；装不上也能出图）。

装完**先停下来问**第 2 节的那一个问题，不要自己往下走。

## 2. 配生图 API（只问一次）

出图只走图片 API，不用宿主自带的生图。**不要问**是 OpenAI / Grok / Gemini 还是哪家。只问这一句，等 URL 和 key 都到了再往下：

```text
把生图接口地址和 API key 发给我。
地址形如 https://xxx/v1
```

缺哪样补哪样，不要替用户填官方地址，也不要猜服务商。key 只进 `.env`，聊天里不要再回显整串。

拿到后**你自己从 URL 判断** `--provider`，**不要带 `--model`**：

| URL 里的主机 | 命令 |
|---|---|
| `api.openai.com` | `python scripts/dsimage.py setup env --provider openai --key <KEY>` |
| `api.x.ai` | `python scripts/dsimage.py setup env --provider grok --key <KEY>` |
| `generativelanguage.googleapis.com` | `python scripts/dsimage.py setup env --provider gemini --key <KEY>` |
| 其他 | `python scripts/dsimage.py setup env --provider custom --base-url <用户给的地址> --key <KEY>` |

它会写 `.env`，再拉模型列表打出来（官方三家和网关都拉；拉不到就用内置名单）。把列表原样给用户，**推荐的可以标出来并建议用哪个**，然后停下来等他回模型名或序号。

**模型必须用户自己选。** 没点名就不要往下：不要用列表里的「推荐」或「当前」，不要自己 `setup model`，不要 `setup test`。用户说「看着办 / 随便」也要把你建议的那个名字问他确认，得到明确答复再跑。

用户选定后才：

```bash
python scripts/dsimage.py setup model <用户选的模型名>
```

这条会**直接试出一张**（拿模板示例图当参考，出一张白底图，1k，一次费用），不用再问「要不要试」。成功会打印图片路径和库里的模板清单。打开图看一眼是不是白底上的那个包。

失败按报错处理：401/403 key 错、404 地址或模型名错、超时是网络。改法就是重跑 `setup env` / `setup model`，不要手改 `.env`。

`.env` 在技能目录，和 `SKILL.md` 同级，换项目换会话都能用；某个项目要另一套配置可在项目根再放一份，优先级更高。

## 3. 收尾

`setup model` 试图通过后跟用户说四件事：

1. 装在哪（路径）。
2. 出图走哪家 + 哪个模型（不回显 key）。
3. 库里有哪些模板——就是试图最后打印的那张表，原样给他，每个加一句是干什么的：
   - `默认电商套图`（smart）：只给产品图不点名模板时用，9 张 + 白图，pt-BR，800×800
   - `童装套图`（smart）：童装六类合一，`set --kind` 区分外套 / 套装 / 裤 / 裙 / 睡衣
   - `胜利鹰女款 / 男款商务背包`（replace）：样图换货，脚本直出
4. 怎么开口：

```text
使用 dsimage，这些是产品图，帮我出一套电商主图                      ← 默认套图
使用 dsimage 模板：胜利鹰男款商务背包，版式别动，只把包换成这些新产品 ← 按样板换产品
使用 dsimage 模板：童装套图，这些是童装外套                        ← 按模板出童装
使用 dsimage，用这张产品图给我设计一套亚马逊图                      ← 从零设计（会先问几个问题）
使用 dsimage，把这张图换成深灰背景 / 出一张 4:5 的海报              ← 只出一张或几张
使用 dsimage，把这套已经做好的图做成模板，以后换产品用              ← 收成模板
```

## 4. 更新

```bash
python scripts/dsimage.py update            # 从 GitHub 拉 main 覆盖技能文件
python scripts/dsimage.py update --dry-run  # 先看会改什么
python scripts/dsimage.py update --from <本地仓库夹或 zip>   # 没网 / 想用本地版本
```

只动 `SKILL.md`、`SETUP.md`、`guides/`、`knowledge/`、`scripts/` 和内置模板；**`.env` 和用户自建模板原位不动**（自建 = 新版里没有的模板夹）。已装目录本身就是仓库克隆时它会改走 `git pull`。跑完打印新增 / 更新 / 删除了什么和模板清单，照着汇报；再跑一遍 `python scripts/test_dsimage.py` 确认。

找不到已装目录就按第 1 节的表逐个找；找不到问用户。

从旧版（有 `references/`、`queue_pack.py` 的那版）升级：旧模板格式不兼容，`update` 会删掉旧脚本，旧的 `references/` 手动删；用户自建的旧模板要按 `guides/make_template.md` 重建（prompt 文字可以原样搬）。
