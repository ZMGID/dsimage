# 建模板

模板 = `templates/<名>/` 夹：`template.json` + `h1.png…` + 可选 `assets/`。整夹拷走就能分享。

同一甲方有多套时，不要摊在根下：建 `templates/{甲方}/`，共用一份 `要求.json`，下面每个模板一个夹。一个大文件夹里混了多个大类、要一类一模板再出图：整条流程见 `client.md`（先 `template client` 填要求，再 `sort` 分类）。

```text
templates/
  默认电商套图/                 ← 零散
  BeautyU/                     ← 甲方（夹名不要用 &）
    要求.json                  ← 共用语言 / 风格 / 分辨率 / 色板；templates 列出下面的夹名
    箱包单品报价/
      template.json
      h1.png …
```

```bash
python scripts/dsimage.py template init <模板名> --from "<样图夹>" --mode replace --client <甲方>
python scripts/dsimage.py template init <模板名> --blank --slots 9 --mode smart --client <甲方>
```

`--client` 会建甲方夹、写或更新 `要求.json` 的 `templates`。本套和别的套一样的字段（语言、风格、分辨率、brand）只写在 `要求.json`，不要再抄进 `template.json`；这一套独有的才写模板。出图时模板同名字段覆盖 `要求.json`。夹名不在 `templates` 列表里，脚本会拒绝加载。

`要求.json`：

```json
{
  "id": "BeautyU",
  "name": "BEAUTY&U",
  "templates": ["箱包单品报价"],
  "language": "图内文字默认葡萄牙语（巴西）",
  "generation": {"resolution": "1k", "format": "png", "quality": "high"},
  "style": "专业商务、产品主导",
  "brand": {"background": "#F3F3F3", "text": "#111111", "accent": "#D6B77A"}
}
```

`id` 必须等于甲方夹名。分享整甲方就拷 `{甲方}/`；只把其中一套丢到根下当零散时，先把 `要求.json` 里的 language / generation / style / brand 写进那份 `template.json`。

## 从甲方样图建 replace 模板

甲方给了一套做好的图（一个品 9 张），以后只换品。

```bash
python scripts/dsimage.py template init <模板名> --from "<样图夹>" --mode replace --category "<品类>" --language "<图内文字语言>"
# 同一甲方还有别的套：加上 --client <甲方>，语言写进 要求.json 而不是这条
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

一个大类下有几个子品类、九页骨架一样只是场景 / 标题 / 关注部位不同（童装：外套 / 套装 / 裤 / 裙 / 睡衣）：不要建六个模板，建一个，`product_kinds` 列子品类，差异写进 `slots[].brief_by_kind`，第一个键当默认。范本：`templates/童装套图/`。

## 从 smart 结果冻成 replace

`template freeze <成图根> <SKU> <新名>`（可加 `--client <甲方>`），见 `smart.md`。

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
      "brief": "…",                                      // smart 必填
      "brief_by_kind": {"bag": "…"}                      // smart 可选，按品类追加一行
    }
  ],
  "notes": ["给下次用这个模板的人看的提醒"]
}
```

`language` / `style` / `output` 在甲方夹里可省，跟 `要求.json`；这一套不一样才写。smart 的 `style`：模板和 `要求.json` 都没有则校验不过。

`template check` 会查：示例图在不在、refs 引用的文件在不在、占位符合法、`{vary}` 有列表、`prompt_by_kind` / `refs_by_kind` / `brief_by_kind` 键在 `product_kinds` 里、需要 `@product.back` 的模板有没有 `derive.back`、deliver 比例和 ratio 一致。甲方夹还会查 `要求.json` 的 `templates` 是否和磁盘上的模板夹一一对应。
