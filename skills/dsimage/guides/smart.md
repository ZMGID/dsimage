# smart：按模板 brief，每个品单独写 prompt

本路：smart。第一次 `run` 只写 brief，你按品写 `prompts.json` 再出图。
你写：每槽完整英文 prompt；`brief.md` 只是骨架，不要原文照抄。
停：先给两个试出品写 prompt 并 preview；有问题改模板 / prompt，点头了再写其余、再铺（不够两个就全出）。

模板锁的是风格（`style`）、文字策略、画幅、每槽要表达什么（`brief`）。prompt 不锁，你（或子代理）按品写。适合品差异大、每个品要单独发挥的情况。

## 流程

```bash
python scripts/dsimage.py init --template <模板名或甲方/模板名> --source "<甲方夹|单品夹|一张图>"
# 多图的品先 set --front；见 SKILL.md
python scripts/dsimage.py run "<成图根>" --only <SKU1> <SKU2>    # 先给这两个写 brief
```

第一次 `run` 不出图：给这两个还没 prompt 的品写 `_dsimage/<SKU>/brief.md` + `prompts.json`（键 = 槽位 id，值空）。其余品先别写。

## 写 prompt

读 `brief.md`。`brief` 只是骨架（这一页干什么），必须打开产品图按**这件货**写具体 prompt：颜色、材质、结构、卖点、适合它的场景和人物，不要把 brief 原文当 prompt，也不要所有品写成同一套台面静物。

用默认模板（`默认电商套图`）时额外盯三件事：每页背景都要有东西（台面 / 墙 / 场景），不能纯白纯灰；H5 和 H7 是两个不同的人、不同动作、不同场地，prompt 里把人写具体；所有文字 pt-BR，规格数字没给就不编。

用 `童装套图` 时：先 `set --kind`（outerwear / hoodie_set / summer_set / trousers / dress / sleepwear），brief 里「本品类」那行才会给对应的场景、标题、部位、双状态；写 prompt 前先列一张 H1–H9 动作台账（人物 / 动作 / 机位 / 裁切 / 场景），任意两页不能同时重复剪影 + 机位 + 背景；颜色只用品夹里看得到或用户确认的；背面有印花的品别信派生，向用户要真背面图。

`brief.md` 里有：全套约束（品类、语言、画幅）、风格锁、产品图路径、每槽的 brief 和参考图顺序、模板备注。然后：

1. 打开产品图，看清楚它是什么、什么颜色、什么材质、有什么结构/卖点。
2. 每槽一条完整英文 prompt，开头原样贴风格锁，然后写这一页的构图、产品怎么摆、光、底、文字（按模板语言，短）、否定项。构图数值和角度短语可以翻 `knowledge/shots.md` 抄。
3. 写进 `prompts.json`。所有槽非空才算齐。

多个品：先挑两个试出品写 `prompts.json`（一品一个子代理也行）。主会话指令只带该品 `brief.md` 路径和产品图，只许写该品 `prompts.json`（不出图、不改模板、不 init）。这两个出完、用户点头后，再给其余写 prompt，主会话一条 `run` 铺开。

```bash
python scripts/dsimage.py run "<成图根>" --only <SKU1> <SKU2>     # 先出两个
python scripts/dsimage.py preview "<成图根>" --only <SKU1> <SKU2>
python scripts/dsimage.py run "<成图根>"                          # 点头后铺其余
```

改 prompt 后 `run --redo --only <SKU> --slot H3` 只重出那槽。

## 冻成 replace 模板

一个品的整套效果被用户认可，后面同类品只想换货：

```bash
python scripts/dsimage.py template freeze "<成图根>" <SKU> <新模板名>   # 可加 --client <甲方>
```

会把这个品的 9 张成图拷成新模板的示例图，每槽 prompt = 换货前缀 + 当时的生成 prompt。打开新模板 `template.json` 通读一遍，把「生成一个…」的口吻改成「保留母版…只换产品」，`template check` 通过后就是 replace 模板。

## 模板里跟 smart 有关的字段

- `style`：必填，每条 prompt 开头原样带。
- `slots[].brief`：必填，这一页要表达什么、放什么信息，不写具体 prompt。
- `slots[].brief_by_kind`：可选，配合 `product_kinds`，按品类追加一行到 brief 里（童装模板用它区分外套 / 裙装 / 睡衣的场景和标题）。
- `slots[].example`：可选，只是给你看版式，不进生图。
- `slots[].refs` 默认 `["@product.front"]`。背面页可以写 `["@product.front", "@product.back"]`，品没背面图时和 replace 一样先派生（`derive` 子命令先看）。
