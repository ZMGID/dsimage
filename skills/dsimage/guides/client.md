# 甲方大单：一个甲方、一个大文件夹、好几个大类

本路：甲方大单。出图阶段跟单套一样：这类先出两个审核，改的是该类模板，点头再铺这类。
你写：先 `要求.json`；一类一模板；出图跟该类的 replace 或 smart。
停：要求、分类表、每类两个预览，三处都等人点头。点名了单套模板、或只有一个种类，不走这里。

同一甲方、要求大体一样，但源夹里混了多种货。整夹直接 `init` 会把不同类揉进一套模板。大类即可，不要按颜色 / 尺码拆。

节奏：**先定 `要求.json` → 按大类分夹 → 一类一模板 → 每类先出 2 个审核，过了再铺这一类。**

## 1. 共用要求

甲方名用文件夹能用的字（不要 `&`）。没有夹就建：

```bash
python scripts/dsimage.py template client <甲方>
```

打开 `templates/{甲方}/要求.json`，把各套都会一样的写进去：`language`、`style`、`generation`（分辨率 / 格式）、`brand`（色板）。这一套才不一样的以后写进该模板。

跟用户确认这份要求。没点头不要分类、不要建模板。字段说明见 `make_template.md`。

## 2. 按大类分类

```bash
python scripts/dsimage.py sort --source "<甲方大文件夹>"
```

列出源里每个品。看图，只拆**大类**（外套 / 裤装 / 箱包，不要黑 / 白 / S / M）。一类里还有子品类、页骨架一样 → 仍算一类，模板里用 `product_kinds`，不要多分夹。

把分类表给用户，等人点头。然后拷到源夹**同级**「分类」根（源夹只读，一个字都不改）：

```bash
python scripts/dsimage.py sort --source "<甲方大文件夹>" --group 外套=SKU1,SKU2 --group 裤装=SKU3,SKU4
```

或写一份 `分类.json`（`source` + `groups`）再 `sort <这份.json>`。得到：

```text
VE男包系列/                 ← 甲方源，只读
VE男包分类/
  分类.json
  双肩包/{SKU}/图
  腰包/{SKU}/图
```

用户已经按大类分好夹了 → 跳过 `sort`，把现成分类根当下面的源。

## 3. 一类一模板

所有大类的模板都做完、`template check` 都过了，再出样。不要做一套就出图。

```bash
python scripts/dsimage.py template init <大类名> --from "<样图夹>" --mode replace --client <甲方>
python scripts/dsimage.py template init <大类名> --blank --slots 9 --mode smart --client <甲方>
```

`--from` 用这一类里最能代表版式的样图（用户给了样板就用样板；没有就从分类夹里挑一套看得懂的）。共用字段不要抄进 `template.json`。写法见 `make_template.md`。校验：

```bash
python scripts/dsimage.py template check <甲方>/<大类名>
```

## 4. 每类先出 2 个，过了再铺

一类一类来。成图根放到源夹同级的「生成」下，不要堆进分类根：

```bash
python scripts/dsimage.py init --template <甲方>/<大类> --source "<分类根>/<大类>" --out "<源同级>/<名>生成/<大类>"
```

挑这一类里**两个**有代表性的品（颜色 / 款式差一些的，别挑两件几乎一样的）。选白图、该 `derive` 的先看派生，再：

```bash
python scripts/dsimage.py run "<成图根>" --only <SKU1> <SKU2>
python scripts/dsimage.py preview "<成图根>" --only <SKU1> <SKU2>
```

把预览给用户。不对 → **只改这一类的模板**（或白图），`run --redo --only <这两个>`，再送审。未点头不要铺这一类，也不要开始下一类的 2 个。

点头后铺这一类其余品：

```bash
python scripts/dsimage.py run "<成图根>"
python scripts/dsimage.py status "<成图根>"
```

再做下一个大类。replace 读 `replace.md`，smart 读 `smart.md`；选白图、看成图仍按 SKILL.md。
