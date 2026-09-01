# 快速换货（Agent 按此执行）

> 用户说「快速换货 / 同类快换 / 快速替换」，或给了样板套图 + 很多型号、只要换商品时读本文件。
> 这不是第三种模板。锁的还是母版（`lock=master`），执行改成脚本：一句提示词、两张参考图，先试一套，点头后再铺开。铺开期间不要写 Prompt、不要派品工人。
> 适合：同一类货、版式不动、字不改、数量多。不适合：要重画、要改货号/价格、品类差很远、没有齐套母版。

默认提示词只写在 `scripts/swap_fast.py` 的 `DEFAULT_PROMPT`。各槽共用这一句，差别在图（母版 `hN` + 该槽 `product_ref` 产品图），不要给 H1–H9 各写一版。

```text
Replace only the product in the first image with the product from the second image. Keep layout, text, icons, and background unchanged.
```

---

## 步骤

每步做完再进下一步。未点头不要 `--blast`。

### 1. 对齐材料

要有两样：一套母版页（样板主图 / 已登记 `lock=master` 模板），加上要换进去的产品图（大文件夹时每个子文件夹一个型号）。

对用户确认下面几件事（一次说完）。**抽检默认关**，不说就不停。尺寸、档位、交付**不要抄技能里的数字**，由你按本轮原话 + 母版像素 + 模板/甲方 `generation` 填进命令。

1. 母版和新品是同一类（书包换书包）。不是就停下，不要硬换。
2. 图上的字一律不动。要改货号/价格就改走 SKILL「换货」长 Prompt，不要用本文件。
3. 你填这些参数（用户没说的项用模板/甲方；都没有才用脚本兜底，不要自己发明一套固定尺寸）：
   - `--resolution`：`1k` / `2k` / `4k`。用户点了用用户的；否则模板/甲方；都没有才 `1k`。不要把像素（如 800、1024x1024）当成档。
   - 各槽生图比例：跟母版像素走。用户要了精确画布，则生图比例必须等于那张画布；对不上就停，不要变形压。
   - 交付：精确宽高 → `--output-size <宽x高>`（同一比例生，出完再缩）；只限长边 → `--max-px <长边>`（保持比例）；体积 → `--max-bytes <体积>`。没说交付就不加这些旗，不压。
4. 铺开时默认一口气出完。用户要每隔 N 个品停，填 `--inspect-every <N>`；不说就 `0`。

库里没有 `lock=master` 模板时，用用户给的样板文件夹 `--masters`，不要改走默认电商模板、不要按规则重画。

**完成：用户确认同类、冻字、生图档、交付（或不压）、抽检（或默认不停）。**

### 2. 建批次并试跑一套

跑 `match_pack.py --query "<用户原话>"`，把 stdout 给用户看。第 1 名若不是母版，仍用 `--masters` 或用户点的母版模板，不要换成白底主图。

```bash
python scripts/queue_pack.py --init --fast --source "<大文件夹>" --masters "<样板文件夹>" --category "<品类>"
# 已有 lock=master 模板时用 --template，不要再用 --masters（除非母版图不在模板夹）
# 按本轮填，不要照抄数字：
#   --resolution <1k|2k|4k>
#   --output-size <宽x高>    或  --max-px <长边>  --max-bytes <体积>
#   --inspect-every <N>
```

Windows 用 `python`，macOS/Linux 用 `python3`。`jobs.json` 的 `resolution` / `format` / `quality` / `size` 写成你填进批次的那些值，不要写像素档，也不要一律写成 `1k` 或 `1:1`。

先出**一整套**试跑品（H1 到最后一槽都要，不要只出主图）。用户没点名就用批次里的 `pilot`（默认第一个品文件夹）：

```bash
python scripts/queue_pack.py --queue "<成图根>/_prompts/批次.json" --pilot "<品名>" --run
```

有生图 API 才 `--run`。没有 API、走宿主生图：jobs 已写好，按 jobs.json 出图，附上该槽两张参考（先母版后产品），**沿用 `swap_prompt.txt`，不要改写**。单品槽位同时最多 4 路。

缺背面产品图的槽会跳过并写入 `_prompts/<品>/skipped.json`。不要拿正面硬贴背面页。把跳过的槽告诉用户。

**完成：试跑品成图已在成图文件夹，路径已给用户。**

### 3. 等用户看过再锁

把试跑成图路径给用户。问：要不要改那一句提示词，或某一页单独改。

- 改共用句：`--queue ... --set-prompt "新的一句"`，再 `--pilot <品名> --run`（不要 `--skip-existing`，让试跑页重出）。
- 只改某一槽：`--set-slot-prompt H5 "该槽的一句"`，再重出该试跑品。
- 用户说没问题 → 进入第 4 步。不要在这一步铺开。

**完成：用户点头，或改句后的新试跑已通过。**

### 4. 脚本铺开（大模型不写 Prompt）

```bash
python scripts/queue_pack.py --queue "<成图根>/_prompts/批次.json" --blast --run --skip-existing
```

`--blast` 给剩余型号写同一份 jobs（提示词已锁，生图档用批次里的 `generation.resolution`）。`--skip-existing` 保住试跑成图。主会话不要 `--next` 派品工人，不要给每个型号写 Prompt。

批次 `inspect_every` 大于 0 时：`--run` **一次只出 N 个品**，然后停下来把这一波路径给用户看。通过再跑同一条 `--run --skip-existing` 出下一波。不要一次出完全部。不对就 `--set-prompt` / `--set-slot-prompt`，只重跑有问题的品（不要 `--skip-existing`），再继续。

`inspect_every` 为 0（默认）：`--blast --run --skip-existing` 一口气出完，最后再问要不要抽查。

没有 API：jobs 已齐，按品出图仍用 `swap_prompt.txt` + 两张参考。数量大时告知用户宿主并发上不去，建议配 API；用户坚持就继续，仍然不改 Prompt。

失败槽位改句后只重跑失败的：`--run --skip-existing`。某一槽系统性翻车 → `--set-slot-prompt` 再 `--blast --run --skip-existing`（已成功的页会跳过）。

**完成：`--next` 显示全部完成，或只剩 skip/empty。**

### 5. 交付压图（有要求才做）

批次.json 里有 `deliver`（`width`/`height` 或 `max_px` / `max_bytes`）才跑。没有就跳过。

```bash
python scripts/queue_pack.py --queue "<成图根>/_prompts/批次.json" --deliver
```

需要 Pillow（`pip install pillow`）。只缩小、不放大、不变形。`--output-size` 的宽高比例必须已经是生图比例；对不上就失败，不要拉变形。只设 `--max-px` 则缩长边、比例不变。生图仍用批次里的档（`1k` / `2k` / `4k`），不要把交付像素写进模型档。

**完成：压完列出路径，或本步跳过。**

### 6. 问要不要检查

问一句：要不要抽查成图（对照产品外形、母版上的字和图标、明显坏图）。已经按波检查过的，问一句还要不要再看一遍即可。用户说不用则结束。

要检查：对照母版 + 该品产品图，看产品是否换成新货、未点名的字/图标是否被改、有没有坏图。问题记在一起再改，不要边看边改一张。改法：收紧提示词或换某槽母版，再只重跑有问题的槽。

整批收口一次。问要不要把这套样板登记成 `lock=master` 模板（还没有的话）；用户说要 → `CREATE_TEMPLATE.md`。不要每个型号问一遍。

**完成：用户已答要不要检查；有问题已记下来或已改完。**
