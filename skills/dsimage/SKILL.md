---
name: dsimage
description: E-commerce visual creation skill. Turns product photos plus a one-line request into complete, conversion-optimized image sets — marketplace hero images, Amazon/Shopify PDP detail pages, social/ad creatives, livestream scenes — using 25 built-in shooting scenes, with Campaign Style Lock keeping multi-image sets visually consistent. Uses the user's reference photos to preserve product identity. Generates images directly via the host agent's built-in image generation (e.g. Codex) when available, or via the user's configured OpenAI-compatible image API. Also builds reusable client-specific scenes from client materials (style reference PDFs, brand requirements). Use when the user asks for 电商主图 / 详情页 / 产品图 / 商品图 / 白底图 / listing images / product photos / PDP / A+ content / social or ad creatives, or visual strategy and image-generation prompts for selling scenarios, or asks to 制作模板 / 创建模板 / 建一个模板 / create a template from their materials.
---

# dsimage Skill

当用户需要视觉策略、图片 Prompt、商品主图、营销图、社媒图、广告图、电商 PDP 视觉，或要求直接 AI 生图时，使用这个 Skill。

这个 Skill 有两种模式：

1. **Brief / Prompt 模式**：只输出视觉简报和可执行图片 Prompt。
2. **Generate 模式**：当用户明确要求"生图、生成图片、出图、render image"时，先输出最终 Prompt，再调用生图。

不要暴露、索要、写入、提交或回显真实 API key。使用者必须通过自己的环境变量配置 API。

---

## 核心流程

**本 Skill 只规定通用流程。每个场景具体怎么拍、占多少、写什么字、注意什么，全部以命中的情景文件为准。**

1. 判断任务类型，按下方**情景匹配表**找到情景文件。
2. **完整读取命中的情景文件**，之后一切按情景内容执行：
   - `workflow` — 该场景的执行步骤（照做）
   - `composition_rules` — 产品占比、留白、角度（照做）
   - `text_rules` — 图内文字规则（照做）
   - `pitfalls` — 出图后按这个清单检查
   - `anti_ai_tips` — 有则必须应用
3. 只收集会实质影响结果的缺失信息；缺非关键信息时明确假设后继续，不要阻塞。
4. 多图任务：先建立 **Campaign Style Lock**（见下文），原样放进每张 Prompt 开头。
5. 商品/营销任务：先做**转化驱动力诊断**（见下文）。
6. 逐张写 Prompt：Style Lock → 情景 `prompt_template` 骨架（替换 `{variables}`）→ 按需套用 `variants` / `category_tips` → 按通用规则收尾。
7. Generate 模式：宿主自带生图工具（如 Codex 的 imagegen）优先直接使用；没有时调用 `scripts/gen_image.py`，用户提供了产品图必须带 `--image`。**命令参数从情景取**：`--size` 用情景 `default_ratio`；`--resolution` / `--format` / `--quality` 用情景 `generation` 字段（未写则用脚本默认）；用户显式指定的参数优先于情景值。
8. 出图后按情景 `pitfalls` + 下方 QA 清单检查，返回文件路径和关键假设。

---

## 生图配置

图像生成使用任意 OpenAI 兼容 API（示例用官方地址）。`.env` 放在 Skill 目录内（与 SKILL.md 同级）即全局生效，换会话、换项目都可用；脚本查找顺序：`--env-file` > 从当前目录向上查找 > Skill 自身目录。不要把真实 API key 写进仓库：

```dotenv
IMG_BASE_URL=https://api.openai.com/v1
IMG_MODEL=gpt-image-2
IMG_API_KEY=your-api-key
```

脚本兼容别名：`OPENAI_BASE_URL`、`OPENAI_API_BASE`、`OPENAI_IMAGE_MODEL`、`OPENAI_MODEL`、`OPENAI_API_KEY`。

**出图通道优先级**：宿主 Agent 自带生图能力（如 Codex 的原生 imagegen）时优先直接使用，Prompt 交给它即可，无需任何配置；否则调用脚本：

```bash
python3 scripts/gen_image.py --prompt "..." --size 1:1 --resolution 2k
python3 scripts/gen_image.py --prompt-file prompt.txt --output-dir generated-images
python3 scripts/gen_image.py --env-file .env --prompt-file prompt.txt
```

脚本要点：

- 自动适配两种 API：URL 含 `apimart` → 异步轮询（比例格式 `1:1` + `--resolution`）；其他 → OpenAI 同步（像素尺寸自动转换）
- **带参考图时同步模式自动走 `/images/edits` 图生图端点**，原图真实上传给模型
- `--image`：参考产品图路径，保证产品一致性，强烈建议总是使用
- 其他参数：`--output-dir`、`--poll-interval`、`--timeout`、`--format`、`--quality`、`--n`

如果缺少任何生图配置，先询问用户是否现在配置：确认后读取本 Skill 目录下的 `SETUP.md`，按其中流程引导完成（收集 `IMG_BASE_URL` / `IMG_API_KEY` → 拉取模型列表让用户选择 `IMG_MODEL` → 写入 Skill 目录 `.env`）；用户暂不配置则只输出 Prompt 包。

---

## 情景系统

`references/scenes/` 下 25 个情景，**每个情景是该类画面的完整执行规范**，包含：

| 字段 | 含义 |
|---|---|
| `prompt_template` | Prompt 骨架，替换 `{variables}` 使用 |
| `variants` / `category_tips` | 风格变体、品类加成建议 |
| `default_ratio` | 该场景默认画幅（用户指定优先） |
| `composition_rules` | 产品占比、留白、平台预留区、推荐角度及英文短语 |
| `text_rules` | 图内文字的字号、颜色、长度规则 |
| `workflow` | 该场景的执行步骤 |
| `pitfalls` | 该场景常见翻车点（出图后检查用） |
| `anti_ai_tips` | 防 AI 味技巧（UGC/社媒/直播类必读） |
| `examples` | 成品 Prompt 示例 |

### 情景匹配表

| 触发词 | 情景文件 |
|---|---|
| 白底图, 主图, hero image, packshot | `01-hero-image.json` |
| 场景图, 生活图, lifestyle | `02-lifestyle-scene.json` |
| 平铺图, flat lay, 俯拍 | `03-flat-lay.json` |
| 细节图, 微距, macro, 特写 | `04-detail-macro.json` |
| 海报, poster, banner, 促销 | `05-poster-banner.json` |
| 社交媒体, 小红书, Instagram, TikTok | `06-social-media.json` |
| UGC, 买家秀, GRWM | `07-ugc-style.json` |
| 模特, model, 人物展示 | `08-model-showcase.json` |
| 对比, before after, 前后 | `09-before-after.json` |
| 包装, packaging, 礼盒 | `10-packaging.json` |
| 信息图, A+, 详情页, PDP | `11-infographic.json` |
| 创意, 概念, creative | `12-creative-concept.json` |
| 尺寸, 规格, 使用步骤 | `13-size-spec.json` |
| 套装, 组合, bundle | `14-multi-product.json` |
| 直播, livestream | `15-livestream.json` |
| 试穿, 融入, try on | `16-try-on-virtual.json` |
| 拆解图, 爆炸图, exploded view | `17-exploded-view.json` |
| 隐形模特, ghost mannequin, 3D服装 | `18-ghost-mannequin.json` |
| 多角度, 网格, grid, 多色展示 | `19-multi-angle-grid.json` |
| 杂志, 封面, editorial, magazine | `20-magazine-editorial.json` |
| 季节, 四季, campaign, 春夏秋冬 | `21-seasonal-campaign.json` |
| 奢华, 氛围, 烟雾, luxury, atmospheric | `22-luxury-atmospherics.json` |
| 设备模型, 界面, mockup, SaaS, APP | `23-device-mockup.json` |
| 店铺, 门面, 空间, storefront, 实体店 | `24-storefront.json` |
| 运动, 健身, sports, fitness | `25-sports-campaign.json` |

无匹配 → 默认 `01-hero-image.json`。**只读取匹配到的情景，不要一次性加载全部。**

多图任务通常一次命中多个情景（如详情页 = 信息图 + 细节 + 场景的组合），每张图按其对应情景执行。

**区分两种任务**：

- **用情景出图**（"基于 xx.jpg 生成主图"）→ 按上方核心流程走。
- **制作一个模板**（用户丢来一堆甲方材料/风格参考/要求总结，说"制作一个模板 / 创建模板 / 建个模板"，可能带"使用 dsimage"）→ 这是模板创建任务：以甲方材料生成一条带品牌风格的**定制情景**（业务上就是你说的"模板"），**读 `CREATE_TEMPLATE.md`**，按其 4 个固定检查点（素材分析 → 骨架 → 执行规则 → 成稿登记）引导用户完成，每个检查点必须等用户确认才能进下一轮。

**新建或修改情景的规范**：字段规范看 `references/scenes/_SCENE_SPEC.md`；写完跑 `python3 scripts/check_scenes.py` 校验，并在上方匹配表登记。

---

## 通用 Prompt 规则

以下铁律适用于所有场景（具体数值以情景 `composition_rules` / `text_rules` 为准）：

1. **颜色用 hex 码**，不用形容词："白底"是淡灰，`#FFFFFF` 才是白。
2. **产品占比和留白必须显式写出数字**，不写模型一定把画面填满。
3. **否定清单不能省**，写具体禁止项：`不要添加：道具、手、水印、假 logo、额外文字、装饰元素、渐变背景`。
4. **图内文字量严格控制**：主标题短、标签化，禁止大段小字；颜色和字号给明确指令。
5. 中文文字用「」包裹渲染更准；复杂笔画中文字换简单同义字；拉丁语言（英/葡/西等）直接写。
6. Prompt 结构顺序：Style Lock → 主体场景 → 目的与情绪 → 构图镜头 → 光线材质 → 风格真实感 → 画幅比例 → 图内文字 → 负面约束。
7. Prompt 保持简洁具体，自然语言优于关键词堆砌；写清楚材质（磨砂玻璃、拉丝金属、哑光饰面）。

---

## Campaign Style Lock（多图一致性）

多张图必须先建 Style Lock：这是整套图的视觉合同，原样复制进每张 Prompt 开头，不能改写或缩短。用户给了品牌规范就按品牌规范建；没给就用下面的默认锁：

```text
Campaign Style Lock: consistent premium ecommerce visual system across the entire image set; fixed palette of clean off-white background, deep charcoal text, one product-matched accent color, and one soft secondary accent; neutral-cool studio lighting; modern geometric sans-serif headline placeholders only; consistent rounded rectangular info labels; consistent thin-line icon style; clean high-end product photography mixed with minimal infographic elements; stable product scale and placement; generous whitespace; no color palette changes, no mixed fonts, no random backgrounds, no inconsistent lighting, no mismatched icon styles.
```

要点：固定 2-3 主色 + 1 强调色（写 hex）；冷暖调统一；字体系统统一；背景和光线系统统一；产品角度和大小稳定。单张图只能改画面目的、主体动作、局部构图和短文案。重生某张图必须复用原 Lock。

---

## 转化驱动力诊断

商品主图、电商图、广告图和 PDP 视觉，动手前先判断产品靠什么打动买家：

- **A 视觉驱动型**：外观、质感、礼品属性 → 主图序列主打视觉主张、质感特写、场景。
- **B 痛点驱动型**：解决明确摩擦/风险/烦恼 → 严格按"问题 → 解决机制 → 利益证明 → 信任 → CTA"推进。
- **C 情感价值驱动型**：身份、归属、冲动消费 → 情绪钩子、身份表达、社交信号。

**完整的图片包结构**（5 主图 + 9 详情页的逐屏定义、每屏的信息图元素、角度分配、字体搭配、背景节奏）在 `11-infographic.json` 的 `pack_structure` 字段中——详情页/PDP 任务必须读取它。用户明确指定数量和比例时，以用户为准。

---

## 多图执行规则

1. 先建 Campaign Style Lock 并写入图片包计划。
2. 每张图独立编号、独立用途、独立 Prompt，写入单独文件（如 `prompt-H1.txt`），禁止一张 Prompt 生成多屏拼图。
3. 数量、比例、用途：**用户指定优先**，未指定时按 `11-infographic.json` 的 `pack_structure` 默认。
4. 每张 Prompt 开头必须是同一段 Style Lock。
5. 输出目录用产品英文 slug：`generated-images/<slug>-pdp/`。
6. API 或模型不支持某尺寸时，改用最接近的支持尺寸并说明。
7. 缺生图配置时只输出完整 Prompt 包，不调用脚本。
8. 不虚构认证、实验数据、评分、销量、真实评价或品牌授权；证据缺失用 proof placeholder。

---

## QA 检查

最终输出前确认：

- [ ] 已读取命中的情景，Prompt 基于情景的 `prompt_template` 和 `composition_rules` 组装
- [ ] 多图任务已建 Style Lock 且每张开头一致
- [ ] 商品/营销任务已做转化驱动力诊断
- [ ] 颜色全部 hex、占比和留白有数字、否定清单具体
- [ ] 图内文字短且必要，符合情景 `text_rules`
- [ ] 参考图已通过 `--image` 或宿主生图传入
- [ ] 出图后按情景 `pitfalls` 逐条检查通过
- [ ] UGC / 社媒 / 直播场景已应用 `anti_ai_tips`
- [ ] 文件和输出中没有 API key 或私密凭据

---

## 常见翻车点

| 翻车 | 防护 |
|---|---|
| 中文字笔画错 | 放大 200% 逐字核对；复杂字换简单同义字 |
| 品牌色漂移 | 全部用 hex 码 |
| 画面填满无留白 | 按情景 `composition_rules` 显式声明 |
| 全套图角度雷同 | 按情景 `composition_rules.angles` 分配，不连续 3 张同角度 |
| 图内文字乱码 | 放大检查，乱码整张重出 |

场景特化的翻车点见各情景 `pitfalls` 字段，出图后必须对照检查。
