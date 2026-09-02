# 建模板

模板 = `templates/<名>/` 夹：`template.json` + `h1.png…` + 可选 `assets/`。整夹拷走就能分享。

## 从甲方样图建 replace 模板

甲方给了一套做好的图（一个品 9 张），以后只换品。

```bash
python scripts/dsimage.py template init <模板名> --from "<样图夹>" --mode replace --category "<品类>" --language "<图内文字语言>"
```

脚本按文件名自然顺序把样图拷成 `h1.png…`，写骨架，`notes[0]` 记着谁对谁。**打开每张图核对顺序**：主图是不是 h1、顺序对不对；不对就改文件名和 `slots[].example`。

然后逐槽写 `prompt`。结构固定：

```
<换货前缀（骨架里已带）> H3: <这一页保留什么、产品在哪、什么角度、要看到产品的哪部分>. Negative: <禁止什么>.
```

写法要点（来自两份实战模板）：

- 每槽把**这一页的文字原文**写进 prompt（`headline ESPACO INTELIGENTE, subtitle …`），模型才不会改字。
- 写清产品在页面的**位置和姿态**（left 40%, front 3/4, on the reflective table）。
- 背面页写死「颜色跟产品图，不继承母版」。细节页写「拉链拉片没刻字就不刻字」。
- 每槽末尾加一句「Use the product reference image(s) as the ONLY source of truth for shape, material, hardware, logo」。
- 模特页这类每品不一样的：prompt 里放 `{vary}`，`vary` 列表写 6–9 种模特/动作/场景描述。
- 混品类（双肩包模板里会来旅行包）：写 `product_kinds`，用到的槽写 `prompt_by_kind` / `refs_by_kind`。
- 要背面图的槽 `refs` 加 `@product.back`。品没背面时脚本先派生一张：不写 `derive.back` 用内置通用 prompt（「同一产品的正后视图，颜色材质五金一致」）；品类有讲究（背包要背板/肩带/行李带）就写 `derive.back`，prompt 里点明这个品类背面该有什么，`refs` 可以加一张 `assets/` 里的背面参考图。只支持 back，不派生其他视角。
- 模板要用的固定素材（logo、背面参考）放 `assets/`，refs 里写相对路径。

```bash
python scripts/dsimage.py template check <模板名>
```

通过后按 `replace.md` 用一个品试出，对着样图改到像，再铺。

## 建 smart 模板

有风格要求、每个品要单独写：见 `design.md` 第 3 步（`template init --blank --slots N --mode smart`）。有版式参考图可以 `--from <参考夹>`，图只当示例不进生图。

## 从 smart 结果冻成 replace

`template freeze <成图根> <SKU> <新名>`，见 `smart.md`。

## template.json 字段

```jsonc
{
  "name": "胜利鹰男款商务背包",
  "mode": "replace",                       // replace | smart
  "category": "男款商务双肩包",
  "language": "pt-BR",                     // 图内文字语言
  "model": "grok-imagine-image-2.0",       // 可选，锁模型；不写用 .env
  "output": {
    "ratio": "1:1", "resolution": "1k", "format": "png", "quality": "high",
    "deliver": {"width": 800, "height": 800, "max_bytes": "2MB"}   // 可选；或 max_px
  },
  "style": "…",                            // smart 必填：风格锁
  "text_policy": "…",                      // 文字规则
  "product_kinds": {"backpack": "双肩包（默认，第一个）", "bag": "非背包"},   // 可选
  "derive": {"back": {"prompt": "…", "refs": ["@product.front", "assets/back_template.png"]}},  // 可选
  "slots": [
    {
      "id": "H1", "purpose": "主图", "example": "h1.png",
      "refs": ["@example", "@product.front"],          // 可用 @example @product.front @product.back 模板内文件
      "refs_by_kind": {"bag": ["@example", "@product.front"]},
      "prompt": "…{sku}…{vary}…",                       // replace 必填
      "prompt_by_kind": {"bag": "…"},
      "vary": ["…", "…"],                               // prompt 用了 {vary} 才要
      "brief": "…"                                       // smart 必填
    }
  ],
  "notes": ["给下次用这个模板的人看的提醒"]
}
```

`template check` 会查：示例图在不在、refs 引用的文件在不在、占位符合法、`{vary}` 有列表、`prompt_by_kind` 键在 `product_kinds` 里、需要 `@product.back` 的模板有没有 `derive.back`、deliver 比例和 ratio 一致。
