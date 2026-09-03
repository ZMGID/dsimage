---
name: dsimage
description: 电商商品图技能，也能当普通生图工具用。套图走模板（一个文件夹：template.json + 示例图），三种做法：replace（甲方样图换货，脚本直出）、smart（模板给每槽 brief，按品写 prompt）、design（没模板，从零问需求设计一套）；同一甲方一大夹混了多个大类走甲方大单（先 要求.json，按大类分夹，一类一模板，每类先出 2 个再铺）；零散一张几张图走 gen。出图走 OpenAI / Grok / Gemini 或兼容网关的图片 API。Use when the user says 使用 dsimage / dsimage / dsimage引导 / 打印dsimage引导, or asks 怎么用 / 不会用 / 使用说明, or asks for 电商主图 / 详情页 / 产品图 / 商品图 / 白底图 / 套图 / listing images / product photos / PDP / A+ content, or 生成一张图 / 出张图 / 改图 / 换背景 / 海报 / generate an image / edit this image, or 制作模板 / 创建模板 / 换货 / 换品 / 替换模板 / 按这套样图做, or 甲方大单 / 一个大文件夹很多品 / 按大类做模板.
---

# dsimage

脚本出图。你定**路**、看图、在该写的地方写 prompt、改模板。命令在本技能目录跑（Windows `python`，其他 `python3`）：`python scripts/dsimage.py <子命令>`。

一个模板 = `templates/<名>/`：`template.json` + `h1.png…` + 可选 `assets/`。同一甲方多套放 `templates/{甲方}/`，共用 `要求.json`。
有 `.env` 就能出图；没有 → `SETUP.md`。对话里给了接口地址 / key → 立刻按 `SETUP.md` 第 2 步（`setup env` 不带 `--model`），拉列表等人选模型。不回显 key，不手改 `.env`。

## 路

先对照下表定一条路，用一句话告诉用户，然后**只读那一份**，按它做到该停的地方。命令打印的「下一步」是当前步的清单，照着做。换路要用户改口。

| 用户给了什么 | 路 | 读 |
|---|---|---|
| 「dsimage引导」「怎么用」「不会用」 | **引导**：把 `guides/howto.md` 原样给用户 | `guides/howto.md` |
| 安装 / 配 API / 更新 | **安装** | `SETUP.md` |
| 只要一张或几张：出张图、改这张、换背景、海报 | **gen** | `guides/gen.md` |
| 点名了库里的 replace 模板，或「按这套样图把这些品换进去」 | **replace** | `guides/replace.md` |
| 点名了库里的 smart 模板 | **smart** | `guides/smart.md` |
| 「做个模板」「把这套样图收成模板」 | **建模板** | `guides/make_template.md` |
| 一个甲方、大文件夹、明显不止一个种类、还没有按类的模板 | **甲方大单** | `guides/client.md` |
| 要一套图，没点名模板 | **先问**，先别 `init` / `run` / `derive` | 下一节 |

点名了一个模板 → 走 replace 或 smart，大文件夹也是这一套铺下去，不走甲方大单。
有成品套图、只换货 → replace；只有风格参考、每个品要单独发挥 → smart。问一句。
「套图 / 详情页 / 主图全套 / 这些品都做」→ 套；「一张 / 这张 / 改一下 / 海报」→ gen。
先 `template list`。甲方里的显示成 `甲方/模板名`。点名的不在库里就说没有。开口已点名模板，或说「直接生成」→ 跳过「没点名先问」。

用户用自然语言、还没说「使用 dsimage」：对照 `howto.md` 推荐最贴的 **1 句**，写出来让他确认；点头后再定路。材料已经够定路 → 直接开做。不会用 → 把 howto.md 原样给他。

## 停

做到这里先等人，收到明确答复再往下：

- 没 `.env`：等人给 URL 和 key；模型列表出来后等人选名字。
- 引导：只给 howto，等他用其中一句开口。
- 先问：五问问完等人回（已说的划掉）。用模板时名单最多 5 个，等人回序号或名字。
- 甲方大单：`要求.json`、分类表、每类 2 个预览，三处都等人点头。
- 出图：白图没选完的品先 `set`；先出 **两个** 品 `preview`（不够两个就全出），等人点头再铺。有问题改对应模板（或该品 prompt / 白图）后只 redo 这两个。
- 改某一页：先说清改的是模板（以后所有品）还是这个品（`set --vary`），等人认了再改。

## 写

生图 prompt 只写在下面这些地方，对话里不要另写一套再手调接口。

| 路 | 你写 | 脚本 |
|---|---|---|
| replace | 不写生图 prompt。看图、选白图、改模板槽位 | 按模板 prompt 出图 |
| smart | 先写两个试出品的 `prompts.json`；点头后再写其余。`brief.md` 只是骨架 | 第一次 `run --only` 写这两个的 brief |
| design | 先把需求落成 smart 模板，再按 smart 写 prompts.json | `template init --blank` 骨架 |
| gen | `gen` 的英文 prompt | 出那几张 |
| 建模板 | replace：每槽 `prompt`；smart：每槽 `brief` + 全套 `style` | `template init` 骨架和示例图 |
| 甲方大单 | 先 `要求.json`；一类一模板；出图跟该类的 replace 或 smart | `sort` 拷到同级分类根 |

`knowledge/shots.md` 只在写生图 prompt / brief 时翻。
smart 多个品：一品一个子代理，指令里只给 `brief.md` 路径和产品图，只许写该品 `prompts.json`。写完主会话一条 `run`。

## 没点名先问

看完图先问，等用户回了再出。童装不自动走童装套图，包不自动走胜利鹰。

1. 打开产品图，用人话说：这是什么、颜色材质、可能靠什么卖。
2. 一次问完（已经说了的项划掉）：

```text
我看这是……。这轮怎么出，回我就行：
1. 风格（生活场景 / 干净商业 / 白底信息图…）
2. 几张
3. 图上文字用哪种语言（不要字也说）
4. 分辨率 1k / 2k / 4k，画幅（默认 1:1）
5. 要用库里的模板吗？用 → 我按图匹配给你挑；不用 → 按你的要求现写；直接生成 → 走默认电商套图
```

3. 按他的回答走：

**不用模板** → `guides/design.md`。上面答过的别再问；把还缺的问完（平台、每张干什么、文字谁写、交付尺寸），建成 smart 模板，按这件货写每槽 prompt。

**用模板** → `template list`。按这件货 + 刚说的要求匹配，最多 5 名。每行：名字（甲方里是 `甲方/模板名`）、mode、为什么适合。品类明显不对的别凑。replace 模板：没给成品样图、也没说换货，往后排。等人回序号或名字。选完：replace 读 `replace.md`，smart 读 `smart.md`。

**直接生成** → `默认电商套图` + `smart.md`。只有骨架，必须按这件货写每槽 prompt。

源在哪、成图放哪（默认源夹同级 `XX生成`）：没说的才问。前面已经说的语言 / 画幅 / 分辨率 / 张数当本轮覆盖，别再问；没说的按模板。批量前默认先出两个品，不用问「先看哪个」。

## 出图手活

`init` 扫源、拆 SKU、建成图根，打印「下一步」——照着做。源夹只读。

要铺一批时：**先出两个品**交给用户审核（颜色 / 款式差一些的更好；不够两个就全出）。有问题改对应模板再 redo 这两个；点头了才 `run` 铺其余。单品源没有「其余」，试出过了就是完。

```bash
python scripts/dsimage.py init --template <名> --source <甲方夹|单品夹|一张图> [--out <成图根>]
python scripts/dsimage.py run <成图根> --only <SKU1> <SKU2>   # 先出两个
python scripts/dsimage.py preview <成图根> --only <SKU1> <SKU2>
python scripts/dsimage.py run <成图根>                        # 点头后铺；已有的跳过；--redo 重出
python scripts/dsimage.py status <成图根>
python scripts/dsimage.py deliver <成图根>                    # 模板写了 output.deliver 才有必要
```

smart 多一步：先给这两个试出品写 `prompts.json` 再 `run --only`；模板定了、用户点头后，再写其余品的 prompt 铺开。

1. **选白图**。一品一张图脚本直接用；多张图逐张打开，选白底/抠图商品图（不是场景图、不是合成主图），`set --front`；有背面图再 `--back`。没选的品 `run` 不出。
2. **标品类**。模板有 `product_kinds` 且这个品不是默认类，先 `set --kind`。
3. **看派生图**。要背面、品没有时，两个试出品先 `derive --only`，打开 `_dsimage/<SKU>/back.png`：是不是同一个产品。不对就改 `derive.back` 或 `set --back`。对了再 `run`。铺量时抽查 `run` 新派生的即可。
4. **看成图**。两个试出品 `preview`：replace 对照示例图（版式/字/图标原样，货换成这个品）；smart 对照 brief（这一页要的东西在不在、是这件货）。不对就改模板或该品 prompt / 白图，`run --redo --only <这两个> [--slot H5]`。
5. **收口**。整批出完问一次：改过的 prompt 要不要留在模板里；smart 效果好要不要 `template freeze`。

试出完：两份预览路径 + 你看出来的问题，等人点头或指出哪张不对。铺完：成图根、`status` 完成/失败数、失败同一条 `run` 再补。报错把原文给人，标明配置 / 接口 / 模板 / 源哪一步。

## 边界

- 只做静态图。视频、精修抠图、翻译文案不在这里。
- 一个品只认正面（必有）和背面（可选，没有就派生）。侧面、内部、细节不派生。
- 源夹只读。分类拷到同级 `XX分类`。成图根一个 SKU 一夹；工作文件在 `_dsimage/`。
- 分辨率只有 `1k/2k/4k`，接口给多大存多大。交付尺寸用 `deliver`。
- 并发、画幅、分辨率、格式、模型以模板为准，用户本轮点名才覆盖。
- 同一个成图根换模板：旧图不会自动重出，要 `run --redo`。
- 源根下散图不属于任何品，要出就先挪进品夹。

## 目录

```
skills/dsimage/
  SKILL.md  SETUP.md
  guides/      howto.md  client.md  replace.md  smart.md  design.md  gen.md  make_template.md
  knowledge/   shots.md            写生图 prompt 时翻
  templates/   默认电商套图/  童装套图/  胜利鹰女款商务背包/  胜利鹰男款商务背包/
               {甲方}/要求.json + {甲方}/{模板}/
  scripts/     dsimage.py  core.py  gen_image.py  test_dsimage.py
```
