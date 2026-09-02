# gen：只要一张 / 几张图，不走模板

用户要的不是一套商品图，只是「给我出一张……」「把这张图改成……」「用这个产品做张海报」「这张换个背景」。不建模板、不建批次，直接出。

```bash
python scripts/dsimage.py gen "<英文 prompt>" [--ref 图1 --ref 图2] [--ratio 4:5] [--resolution 1k] [--out <目录>] [--name <名>] [--n 3]
```

## 流程

1. **看用户给的图**（如果有）。说出它是什么、要保留什么、要改什么。
2. **缺什么才问什么**，一次问完：画幅（默认 1:1）、图上要不要字和什么语言（默认不要）、放哪（默认 `./generated-images`）。风格、构图这些你自己定，用户没说就按常规商业风。
3. **写 prompt**（英文）：先说参考图的用途（「The first image is the product; keep it exactly」/「The first image is the layout to keep, the second is the product to insert」），再说要生成什么、构图、光、底、文字原文和位置、否定项。拍法和数值可以翻 `knowledge/shots.md`。
4. `gen` 出图，把路径给用户。要几个方向就 `--n 3`，或者不同 prompt 各起一个 `--name`。
5. **改图**：从 `<out>/_dsimage/gen.jsonl` 拿上一版 prompt，只改用户点名的那一处，`--name v2` 再出。不要整段重写。

## 例子

```bash
# 白底图
gen "The product in the first image, exactly as is, on a pure #FFFFFF seamless background, soft even studio light, centered, 40% of frame. No text, no props, no shadow on backdrop." --ref cup.jpg --name cup-white

# 场景图，4:5
gen "The exact mug from the first image on a light oak desk by a window, morning light, blurred plant behind, no text." --ref cup.jpg --ratio 4:5 --name cup-scene

# 换背景 / 改图
gen "Keep the product, its pose and lighting from the first image exactly; replace only the background with a dark slate studio wall." --ref hero.png --name hero-dark

# 三个方向一起出
gen "…" --ref cup.jpg --n 3 --name cup-poster
```

## 边界

- 参考图顺序 = prompt 里说的第一张、第二张。Grok 一张走 `image`、多张走 `images`，脚本自己处理。
- 画幅只传比例；分辨率 `1k/2k/4k`；接口给多大存多大。
- 图上的中文字容易错，出完放大看一遍；不行就少写字或换成英文。
- 同一个产品要出 5 张以上、以后还会来同类品 → 别硬用 gen，转 `design.md` 建模板。
