# smart：按模板 brief，每个品单独写 prompt

模板锁的是风格（`style`）、文字策略、画幅、每槽要表达什么（`brief`）。prompt 不锁，你（或子代理）按品写。适合品差异大、每个品要单独发挥的情况。

## 流程

```bash
python scripts/dsimage.py init --template <模板名> --source "<甲方夹|单品夹|一张图>"
# 多图的品先 set --front；见 SKILL.md
python scripts/dsimage.py run "<成图根>"
```

第一次 `run` 不出图：给每个还没 prompt 的品写 `_dsimage/<SKU>/brief.md` + `prompts.json`（键 = 槽位 id，值空）。

## 写 prompt

读 `brief.md`。它里面有：全套约束（品类、语言、画幅）、风格锁、产品图路径、每槽的 brief 和参考图顺序、模板备注。然后：

1. 打开产品图，看清楚它是什么、什么颜色、什么材质、有什么结构/卖点。
2. 每槽一条完整英文 prompt，开头原样贴风格锁，然后写这一页的构图、产品怎么摆、光、底、文字（按模板语言，短）、否定项。构图数值和角度短语可以翻 `knowledge/shots.md` 抄。
3. 写进 `prompts.json`。所有槽非空才算齐。

多个品：一品一个子代理，只做「读 brief → 看图 → 写 prompts.json」。写完主会话一条 `run`。

```bash
python scripts/dsimage.py run "<成图根>" --only <SKU>     # 先出一个看
python scripts/dsimage.py preview "<成图根>" --only <SKU>
python scripts/dsimage.py run "<成图根>"                  # 都写齐后铺全部
```

改 prompt 后 `run --redo --only <SKU> --slot H3` 只重出那槽。

## 冻成 replace 模板

一个品的整套效果被用户认可，后面同类品只想换货：

```bash
python scripts/dsimage.py template freeze "<成图根>" <SKU> <新模板名>
```

会把这个品的 9 张成图拷成新模板的示例图，每槽 prompt = 换货前缀 + 当时的生成 prompt。打开新模板 `template.json` 通读一遍，把「生成一个…」的口吻改成「保留母版…只换产品」，`template check` 通过后就是 replace 模板。

## 模板里跟 smart 有关的字段

- `style`：必填，每条 prompt 开头原样带。
- `slots[].brief`：必填，这一页要表达什么、放什么信息，不写具体 prompt。
- `slots[].example`：可选，只是给你看版式，不进生图。
- `slots[].refs` 默认 `["@product.front"]`。背面页可以写 `["@product.front", "@product.back"]`，品没背面图时和 replace 一样先派生（`derive` 子命令先看）。
