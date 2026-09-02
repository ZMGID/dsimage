# replace：按甲方样图换货

模板已经把每一页画好（`h1.png…`）并且每槽 prompt 写死。脚本把 `[示例图, 该品白图]` 和 prompt 组成 jobs 直接出图。你不写 prompt，不派工人写 prompt。

## 流程

```bash
python scripts/dsimage.py template list
python scripts/dsimage.py init --template <模板名> --source "<甲方大文件夹>"
```

`init` 打印每个品选到的白图；多图的品列出候选。逐个看图，定白图：

```bash
python scripts/dsimage.py set "<成图根>" V26008 --front "<路径>" [--back "<路径>"]
python scripts/dsimage.py set "<成图根>" V26031 --kind bag        # 模板有 product_kinds 且这个品不是默认品类
```

品没有背面图、模板有槽位要背面（`init` 那行显示「背面 派生」）→ 先派生并看一眼：

```bash
python scripts/dsimage.py derive "<成图根>" --only V26007
```

打开 `_dsimage/V26007/back.png`：同一个产品的背面？颜色、材质、五金、比例对不对？不对 → 改模板 `derive.back.prompt`（或加一张 `assets/` 背面参考进 `derive.back.refs`）后 `derive --redo`；或者自己找一张背面图 `set --back`。对了再出套图：

```bash
python scripts/dsimage.py run "<成图根>" --only V26007
python scripts/dsimage.py preview "<成图根>" --only V26007
```

打开预览图对照模板示例图。查四件事：版式没动；文字/图标一个没多没少；产品换成了这个品（形、色、材质、五金、logo、挂件）；背面页的颜色跟产品图而不是母版。
问题在某一槽 → 改模板那槽 `prompt`（或 `prompt_by_kind`），`run --redo --only V26007 --slot H5`。白图选错 → `set --front`，`run --redo --only V26007`。

用户点头后铺全部（已出的跳过）：

```bash
python scripts/dsimage.py run "<成图根>"
python scripts/dsimage.py status "<成图根>"
python scripts/dsimage.py deliver "<成图根>"      # 模板 output.deliver 有值时
```

失败的槽位同一条 `run` 再跑一次即可。

## 用户给了样图但库里没模板

先按 `make_template.md` 建 replace 模板（`template init <名> --from <样图夹>`，然后逐槽写 prompt），`template check` 通过再回到上面。

## 模板里跟 replace 有关的字段

- `slots[].refs` 默认 `["@example", "@product.front"]`。需要背面图的页写 `["@example", "@product.front", "@product.back"]`；品没有背面图时脚本先派生一张（存 `_dsimage/<SKU>/back.png`）：模板写了 `derive.back` 用模板的（可带品类细节和 `assets/` 参考图），没写用内置的通用背面 prompt。用户给了真背面图（`set --back`）就不派生。
- `prompt_by_kind` / `refs_by_kind`：按品类分支。品的品类用 `set --kind`。
- `{vary}`：模特页这类需要每个品不一样的槽，模板 `vary` 列表按品轮换；某个品想指定就 `set --vary H8 "…"`。
- `{sku}`：替换成商品编号。

## 出完收口

问一句：这轮哪几槽改了 prompt，要不要留在模板里（已经改在模板里就是留了）。某一页效果比原示例图更好，也可以把成图拷回模板换掉那张 `hN.png`。
