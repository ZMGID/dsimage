# 情景规范（新建情景前必读）

> 新建或修改任何情景**之前必读本文件**。每个情景 JSON 是一个场景的完整执行规范：Agent 按 SKILL.md 匹配表命中后，以情景字段为准执行，SKILL.md 不含场景细节。
> 模板层说明：`references/templates/`（甲方定制模板）沿用本规范的字段结构，额外增加 `template_meta`（品牌色板/语言/风格来源）；模板创建流程见 CREATE_TEMPLATE.md。
> 写完必须：① 跑 `python3 scripts/check_scenes.py` 通过 → ② 在 SKILL.md 匹配表登记 → ③ 提交。

## 一、文件约定

- 位置：`references/scenes/`，命名 `NN-kebab-case.json`，NN 用下一个可用序号（00 和本文件保留）
- 编码 UTF-8，标准 JSON，缩进 2 空格，中文直接写（禁止 `\uXXXX` 转义）
- `id` 与文件名一致（`09-before-after.json` → `"id": "before-after"`）
- prompt 骨架和角度短语用**英文**，规则说明、workflow、pitfalls 用**中文**

## 二、字段清单（★必填 ◐按场景 ○可选）

| 字段 | 要求 | 说明 |
|---|---|---|
| ★ `id` | 必填 | kebab-case，与文件名一致 |
| ★ `name` | 必填 | 中文场景名，≤12 字 |
| ★ `keywords` | ≥5 个 | 中英文混合，用于语义匹配，**不得与其他情景重复** |
| ★ `trigger_phrases` | ≥3 个 | 用户最可能说出的短语 |
| ★ `prompt_template` | 必填 | Prompt 骨架：type/subject/background/lighting/composition/quality，用 `{variables}` 占位 |
| ○ `defaults` | 可选 | 默认 background/lighting/composition |
| ◐ `variants` | 2-4 个 | 风格变体，每个只写 `overrides`（覆盖哪些字段） |
| ◐ `category_tips` | 按品类可写 | 键为品类（beauty/electronics/food/fashion/home/jewelry…），值为该品类的加成建议（英文短语） |
| ★ `default_ratio` | 必填 | 该场景默认画幅，如 `1:1`、`2:3`、`16:9`、`4:5` |
| ★ `composition_rules` | 必填 | 见下方"结构化字段细则" |
| ★ `text_rules` | 必填 | 见下方"结构化字段细则" |
| ★ `workflow` | 4-6 步 | 该场景的执行步骤，中文，必须场景特化 |
| ★ `pitfalls` | 3-5 条 | 场景特化翻车点，写"症状（→修法）" |
| ★ `examples` | ≥2 条 | 完整可直接执行的英文 Prompt |
| ★ `supports_image_reference` | 必填 | bool，是否支持 `--image` 参考图 |
| ○ `generation` | 可选 | 脚本参数预设：`{"resolution": "2k", "format": "png", "quality": "high"}`；不写则用脚本默认（2k/png） |
| ◐ `anti_ai_tips` | UGC/社媒/直播/买家秀类**必填**，其余可选 | 防 AI 味技巧 |
| ◐ `pack_structure` | 仅多图编排型情景（如 11-infographic） | 图片包的逐屏结构定义 |

## 三、结构化字段细则

### composition_rules

```json
{
  "product_ratio": "35-40%（太小显廉价，太大显拥挤）",
  "whitespace": "≥45%",
  "platform_reserved": "仅国内电商需要的预留区；海外场景省略此键",
  "layout": "仅版式类情景需要（如网格/分屏/时间线）；摄影类省略",
  "angles": [
    {"angle": "正面 3/4", "prompt": "at a slight 3/4 angle, front-facing"}
  ]
}
```

- `product_ratio` / `whitespace` 必须是**数字或范围**，禁止写"适当""合理"
- `angles` 列 2-4 个该场景真正会用到的角度，每个必须带可拼进 Prompt 的**英文短语**
- 数值参照现有情景校准（如 01 主图 35-40%、02 场景图 20-25%）

### generation（脚本参数预设）

```json
{"resolution": "2k", "format": "png", "quality": "high"}
```

- 可写键：`resolution`（`1k`/`2k`/`4k`，异步模式生效）、`format`（`png`/`jpeg`/`webp`）、`quality`（`low`/`medium`/`high`，仅同步模式生效）
- 不写该字段 = 用脚本默认（2k / png）；写了一个键就表示该情景有意覆盖默认
- 画幅 `--size` 不在本字段里，由 `default_ratio` 承担
- 优先级：用户命令行显式指定 > 情景 `generation` > 脚本默认
- 参考图 `--image`、输出目录 `--output-dir`、模式 `--mode` 是运行时信息，**禁止**写入情景

### text_rules

- 每个键是一个文字角色（`headline` / `labels` / `default` / `note`…），值写清**长度上限 + 字号 + 颜色 hex + 字体**
- 无文字场景也必须写：`{"default": "无文字"}`，不能省略字段

### workflow

- 4-6 步，编号列表，中文
- 必须是**本场景特有**的步骤（背景写 hex、声明浅景深、UI 元素逐个描述……）
- 禁止空话："按需调整""注意效果"这类句子不许出现
- 最后一步通常是出图后的核对动作

### pitfalls

- 3-5 条，每条 = 症状（→ 修法），如 `"白底发灰（必须写 #FFFFFF）"`
- 写这个场景**真的会踩**的坑，不写通用废话

### pack_structure（仅多图编排型）

- 定义图片包：`conversion_drivers`（各驱动力序列）、`hero_pack` / `detail_pack`（张数、每屏 id/名称/信息图元素/角度/对应情景）、`font_pairing`、`rhythm`
- 用户明确指定的数量和比例**永远优先**于 pack 默认，本字段只是缺省值

## 四、{variables} 占位符

- 命名统一 **snake_case**（如 `{product}`、`{headline_text}`、`{scene_description}`），语义清晰即可；禁止驼峰或中划线
- 高频通用变量优先复用：`{product_description}`、`{material_description}`、`{color}`、`{scene_description}`、`{brand_name}`
- 校验器只检查命名格式，不限制变量集合

## 五、最小骨架（复制即用）

```json
{
  "id": "your-scene",
  "name": "场景中文名",
  "keywords": ["中文词", "english keyword"],
  "trigger_phrases": ["用户会说的话"],
  "prompt_template": {
    "type": "photography type",
    "subject": "{product_description}",
    "background": "描述背景 + hex",
    "lighting": "光线描述 + 方向",
    "composition": "构图描述 + 占比",
    "quality": "commercial e-commerce photography"
  },
  "default_ratio": "1:1",
  "composition_rules": {
    "product_ratio": "35%",
    "whitespace": "≥40%",
    "angles": [{"angle": "角度名", "prompt": "english prompt phrase"}]
  },
  "text_rules": {"default": "无文字"},
  "workflow": ["步骤1", "步骤2", "步骤3", "步骤4"],
  "pitfalls": ["症状（→修法）"],
  "examples": ["full english prompt here"],
  "supports_image_reference": true
}
```

## 六、完整性校验清单

- [ ] `python3 scripts/check_scenes.py` 全部通过
- [ ] keywords 与现有情景无重复
- [ ] workflow 是场景特化步骤，无空话
- [ ] composition_rules 数值齐、angles 带英文短语
- [ ] 已在 SKILL.md 匹配表登记
- [ ] README 中情景数量描述已同步（如涉及）
