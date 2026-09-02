# 拍法速查（smart / design 模式写 prompt 时翻）

26 类电商图各自的默认拍法：产品占比、留白、常用角度、文字、容易翻车的点，以及一条能直接改的英文 prompt。
这是参考，不是规则：模板 style 和用户本轮要求优先。写 prompt 时挑对应条目，把数值和角度短语抄进去，再按品改。

| # | 情景 | 适合 | 默认画幅 |
|---|---|---|---|
| 01 | 白底/纯色底产品主图 | 白底图、主图、hero image、白背景 | 1:1 |
| 02 | 场景化生活图 | 场景图、生活图、lifestyle、使用场景 | 4:5 |
| 03 | 平铺图 | 平铺图、flat lay、俯拍、top-down | 1:1 |
| 04 | 细节微距图 | 细节图、微距、macro、特写 | 1:1 |
| 05 | 促销海报/Banner | 海报、poster、banner、促销 | 16:9 |
| 06 | 社交媒体素材 | 社交媒体、小红书、instagram、tiktok | 4:5 |
| 07 | UGC风格/买家秀 | UGC、买家秀、用户生成、真实用户 | 9:16 |
| 08 | 模特展示图 | 模特、model、人物展示、模特图 | 2:3 |
| 09 | 使用前后对比图 | 对比、before after、前后、效果对比 | 1:1 |
| 10 | 包装设计展示 | 包装、packaging、礼盒、gift box | 1:1 |
| 11 | 信息图/A+Content | 信息图、infographic、A+、详情页 | 2:3 |
| 12 | 创意概念广告图 | 创意图、概念图、creative、概念广告 | 16:9 |
| 13 | 尺寸规格+使用步骤图 | 尺寸、规格、尺寸图、使用步骤 | 2:3 |
| 14 | 多产品套装/组合展示 | 套装、组合、多产品、bundle | 1:1 |
| 15 | 电商直播间场景 | 直播、livestream、直播间、电商直播 | 9:16 |
| 16 | 虚拟试穿/产品融入场景 | 试穿、融入、虚拟试穿、try on | 2:3 |
| 17 | 技术拆解/爆炸图 | 拆解图、爆炸图、exploded view、技术图 | 16:9 |
| 18 | 隐形模特 | 隐形模特、ghost mannequin、invisible model、3D服装 | 2:3 |
| 19 | 产品多角度网格 | 多角度、网格、grid、多面 | 1:1 |
| 20 | 杂志大片/封面 | 杂志、封面、杂志大片、editorial | 2:3 |
| 21 | 季节主题网格 | 季节、四季、campaign、季节主题 | 1:1 |
| 22 | 奢华氛围渲染 | 奢华、氛围、烟雾、高级感 | 4:5 |
| 23 | 设备界面模型 | 设备模型、界面模型、mockup、UI展示 | 16:9 |
| 24 | 店铺门面/空间摄影 | 店铺、门面、店面、storefront | 16:9 |
| 25 | 运动/健身广告 | 运动、健身、广告、sports | 16:9 |
| 26 | 箱包功能证据图 | 箱包功能证据、箱包功能图、背包结构证明、bag feature proof | 1:1 |


## 01 白底/纯色底产品主图

- 构图：产品占比 35-40%（太小显廉价，太大显拥挤）；留白 ≥45%
- 角度：正面 3/4 = `at a slight 3/4 angle, front-facing`；正上方俯视 = `photographed directly from above at a 90-degree overhead angle`；微距特写 = `tight zoom on surface texture, extreme close-up`
- 光/底：soft diffused studio lighting, even illumination；#FFFFFF seamless studio background
- 文字：default: 纯白底主图通常无文字；国内平台主图可加一句核心卖点 ≤10 字，颜色 #2D2D2D；note: 海外平台（Amazon 主图）禁止任何文字和图形叠加
- 品类加成：beauty: emphasize texture and glow, show formula details；electronics: highlight metallic finish, screen details, port precision；food: vibrant colors, fresh appearance, show texture；fashion: show fabric texture, drape quality, stitching details
- 翻车：白底发灰（必须写 #FFFFFF）；产品占比过大显拥挤；反光过曝有 AI 感；底部阴影杂乱

```text
{product}, professional product photography on #FFFFFF seamless background, soft diffused studio lighting, centered, commercial e-commerce photography, native API resolution, no shadows, no props
```

## 02 场景化生活图

- 构图：产品占比 20-25%（场景图里氛围才是主角）；留白 ≥50%
- 角度：平视环境视角 = `eye-level environmental shot`；低角度氛围 = `slightly low angle for a cozy atmospheric feel`
- 光/底：natural {time_of_day} light
- 文字：default: 生活场景图通常无文字
- 品类加成：beauty: bathroom vanity with botanical elements, skincare ritual feel；electronics: modern desk setup, minimal aesthetic, tech-forward；food: kitchen counter or dining table, fresh ingredients, warm tones；fashion: urban street or boutique fitting room, model wearing the item
- 翻车：场景喧宾夺主产品看不清；光线色温与产品图不一致；产品占比过大变成摆拍

```text
{product} naturally placed in {scene}, morning sunlight through window, botanical touches, warm atmosphere, professional lifestyle photography
```

## 03 平铺图

- 构图：产品占比 30-40%（满铺构图可到 70%）；留白 常规 ≥40%；满铺构图不要求
- 角度：垂直俯拍（唯一角度） = `photographed directly from above at a 90-degree overhead angle`
- 光/底：soft natural window light from top-left at 45 degrees；{background_material}
- 文字：default: 无文字
- 品类加成：beauty: skincare ritual flat lay, open product showing formula, botanical elements；food: ingredients spread, fresh produce, kitchen tools；fashion: clothing + accessories + shoes arranged aesthetically, fabric textures；home: decor items, textures, materials spread showing lifestyle
- 翻车：不是纯正俯拍有透视；道具喧宾夺主；影子方向互相矛盾

```text
Luxurious {category} ritual flat lay, top-down photography. {product} with lid open showing texture as hero at bottom center. Surrounding: gold-tone palette, crystal bottle, dried lavender with silk ribbon, gold foil flakes, pearl beads. Background: ivory linen. Color: ivory, blush, champagne gold. Soft window light top-left at 45 degrees. no text, no watermark
```

## 04 细节微距图

- 构图：产品占比 特写区域占 55-60%；留白 ≥30%
- 角度：微距特写 = `extreme close-up macro shot, shallow depth of field`；侧面侧光 = `strong side lighting raking across the surface to reveal texture`
- 光/底：{lighting_style}
- 文字：default: 可加一行材质/工艺标注，≤8 字，#888888
- 品类加成：beauty: show cream formula texture, shimmer particles, light reflection；electronics: show port precision, material finish, button detail；food: show ingredient texture, cross-section, freshness；fashion: show fabric weave, stitching quality, hardware detail
- 防 AI 味：For hand shots: specify real skin (visible knuckle lines, slight dryness on cuticles, natural warm tone). NOT retouched or smoothed.
- 翻车：纹理含糊看不出材质；全景深没有呼吸感；高光过曝一片白

```text
Extreme close-up beauty macro, Canon EOS R5 100mm f/2.8 macro. {product} filling 80% of frame, focusing on {focus_area}. Visible pores, fine lines, natural imperfections, NOT retouched. Formula visible with realistic light reflection. Natural side lighting. native resolution
```

## 05 促销海报/Banner

- 构图：产品占比 40%；留白 ≥30%（促销视觉允许更满）
- 角度：正面平铺 = `front-facing product hero shot`；动态悬浮 = `product floating with dynamic motion feel`
- 光/底：；{background_description}
- 文字：headline: 主标题 ≤8 字，品牌强调色 hex，字号 40-60pt；cta: 行动按钮 ≤6 字；promo: 促销信息 ≤2 行（折扣数字大、说明文字小）
- 品类加成：beauty: rose gold accents, elegant serif fonts, luxury gift aesthetic；electronics: dark backgrounds, neon accents, futuristic typography；food: warm colors, dynamic food elements, freshness cues；fashion: editorial style, model inclusion, aspirational lifestyle
- 翻车：图内文字乱码；促销信息太多没有重点；文字与产品互相遮挡

```text
Luxury {category} campaign poster. Full-bleed gradient ivory to rose. Top: {headline} elegant serif. Center: {product} with decorative elements. {subtitle}. Bottom left: price {price} original crossed out. Bottom right: brand logo and {cta}. Gold foil accents, premium aesthetic, 2000x3000px
```

## 06 社交媒体素材

- 构图：产品占比 30%；留白 ≥40%
- 角度：手持视角 = `casual handheld phone photography feel`；桌面平视 = `eye-level shot on a desk among daily items`
- 光/底：natural indoor lighting
- 文字：headline: 一句话口语化标题，平台母语，短句不换行
- 品类加成：beauty: show product in use on skin, texture close-up, real results；food: overhead dish/drink shot, appetizing colors, 45-degree angle；fashion: mirror selfie or outfit grid, casual styling, real-person aesthetic；home: corner shot in styled room, cozy atmosphere, warm tones
- 防 AI 味：Specify phone model. Add imperfection: noise, warm cast, not centered, slight blur. Use 'NOT AI-generated look'. Reference Kodak Portra 400 tone. Show lived-in environment.
- 翻车：太完美像硬广，没有种草感；出现平台 logo 或水印；文案过长

```text
Ultra-realistic Xiaohongshu RED product lifestyle photo, iPhone 15 Pro, NOT professional photographer. Slightly tilted angle, {product} on {surface}, lid off showing texture. Environmental details: slight water stain, natural shadows, lived-in feel. iPhone warm auto-white-balance, natural noise, NOT sharpened, Kodak Portra 400 feel, NOT AI-generated look, 1080x1350px
```

## 07 UGC风格/买家秀

- 构图：产品占比 25-35%；留白 0-15%（生活化满构图，不强制大留白）
- 角度：镜面自拍 = `mirror selfie angle with slight tilt`；手持第一视角 = `first-person handheld POV`
- 光/底：indoor lighting with warm yellow cast, uneven
- 文字：default: 通常无文字；可选手写体短标签
- 品类加成：beauty: product in use on real skin, visible pores, bathroom setting；food: phone snap on table, casual restaurant or home；fashion: mirror selfie wearing item, bedroom or fitting room；electronics: desk setup with product in use, realistic cables
- 防 AI 味：CRITICAL: (1) Specify phone model (iPhone 14 Pro/15), (2) Add imperfection (pores, noise, warm cast, off-center), (3) Candid language (NOT professional), (4) Real environment (slightly messy), (5) Avoid AI words (no perfect, flawless, stunning), (6) State 'NOT AI-generated look', (7) Reference Kodak Portra 400 tone
- 翻车：过度磨皮塑料感；打光太完美；环境太干净不像真人拍的

```text
Bathroom mirror selfie, iPhone front camera. Person with {product}. Mirror has slight condensation. Warm yellowish indoor lighting. {product} label recognizable but not centered. Skin: visible pores, slight redness, NOT flawless. Warm yellow cast, phone noise, natural unposed, NOT AI-generated look, authentic UGC, 1080x1350px
```

## 08 模特展示图

- 构图：产品占比 模特全身占 60-70%；留白 ≥30%
- 角度：全身正面 = `full-body front-facing shot`；3/4 侧身 = `three-quarter turn showing garment drape`；背面 = `full-body rear view`
- 光/底：natural window light creating realistic highlights
- 文字：default: 无文字
- 品类加成：beauty: extreme close-up on application moment, formula texture on skin, real skin mandatory；fashion: full outfit showcase, pose highlighting garment, editorial lighting；accessories: product being worn/used, hand or body detail, lifestyle context；sports: active pose in appropriate setting, show performance
- 防 AI 味：MANDATORY: (1) Real camera (Canon EOS R5 / Sony A7 IV), (2) Visible skin imperfections (pores, uneven tone, blemishes, fine lines), (3) Natural expression asymmetry, (4) 'NOT retouched, NOT AI-generated look', (5) Real lighting (natural window, NOT studio-perfect), (6) Natural hand details (knuckle lines, cuticle texture)
- 翻车：手部畸形（重点检查）；面部 AI 塑料感；衣服贴合身体失真

```text
Extreme close-up beauty macro, Canon EOS R5 100mm f/2.8 macro. Face filling 80% of frame, {product} being applied on {focus_area}. Skin incredibly detailed: pores, fine lines, natural imperfections, NOT retouched. Formula visible with realistic reflection. Natural side lighting. NOT AI-generated look, 1080x1350px
```

## 09 使用前后对比图

- 构图：产品占比 每侧 35%；留白 分屏标签区留白 ≥30%；版式：左右分屏 50/50，或上下分屏；两边构图、光线、角度严格一致
- 角度：同机位两侧 = `identical camera position and lighting on both sides`
- 文字：labels: BEFORE / AFTER 标签，无衬线体，放角落
- 品类加成：beauty: show skin texture change, include moisture/radiance percentage data；fitness: body transformation, consistent pose and lighting；home: room before/after renovation or cleaning；automotive: vehicle before/after detailing
- 翻车：左右光线角度不一致穿帮；效果差异太夸张失去可信度；两侧构图没对齐

```text
Cinematic before/after {category} transformation. Left: moody lighting showing {before}, cool tone. Right: bright golden hour showing {after}, warm tone. Center: decorative frame with product. Bottom: comparison data grid. Premium campaign layout, 1080x1620px
```

## 10 包装设计展示

- 构图：产品占比 40-50%；留白 ≥40%
- 角度：正面 3/4 展示盒型 = `three-quarter view showing box structure and finish`；微距工艺 = `macro close-up on foil stamping / embossing detail`
- 光/底：soft directional with metallic reflections
- 文字：default: 品牌名与品类词用占位符描述，明确要求 no readable text 或给定真实文字
- 品类加成：beauty: label design, ingredient preview, formula through transparent elements；food: nutritional info area, ingredient imagery, freshness seals；fashion: branded tissue, garment tag, care instructions, shopping bag；electronics: box design, inner foam, cable organization, quick-start guide
- 翻车：包装文字乱码；盒型结构透视错误；工艺质感画不出来显廉价

```text
Luxury {category} packaging concept. Full spread: (1) product with lid, label visible, (2) outer gift box: embossed pattern, gold logo, magnetic closure, (3) tissue with subtle watermark, (4) satin ribbon with monogram, (5) brand card gold foil, (6) sustainable fill. On marble with gold foil, pearls, dried petals. Soft directional lighting, metallic reflections. Premium presentation, 1080x1620px
```

## 11 信息图/A+Content

- 构图：产品占比 30-40%；留白 ≥45%；版式：电商信息图结构：标题区 + 产品区 + 利益点/图标区，双栏或网格
- 角度：正面 3/4 = `front 3/4 product view`；俯视 = `elevated overhead angle`；微距 = `macro detail shot`
- 文字：headline: 主标题 28-48pt，#2D2D2D；labels: 利益点标签 16-20pt，图标 + 短文案；notes: 标注 10-14pt，#888888
- 品类加成：beauty: ingredient breakdown with %, before/after data, dermatologist badges；electronics: spec comparison, performance metrics, compatibility icons；food: nutritional visualization, ingredient sourcing, recipe flow；fashion: size guide, material composition, care instructions
- 翻车：退化成纯产品照片没有信息图结构；大段小字密密麻麻；图标风格每屏漂移

```text
Complex Amazon A+ Content module. Top banner with brand and tagline. Main: 4 quadrants each showing product detail with labeled feature: (1) {f1}, (2) {f2}, (3) {f3}, (4) {f4}. Below: comparison table. Bottom: spec chart and certification badges. {color} palette. Mobile-first, professional e-commerce, 2000x2500px
```

## 12 创意概念广告图

- 构图：产品占比 25-35%；留白 ≥40%
- 角度：戏剧化视角 = `dramatic hero angle with surreal staging`
- 文字：default: 通常无文字；可加一句 slogan，serif 字体
- 品类加成：beauty: floating product with splash, ethereal lighting, formula particles；electronics: holographic interfaces, data visualization, futuristic；food: ingredient explosion, dynamic pour/splash, steam and fire；fashion: editorial art direction, dramatic poses, fabric in motion
- 翻车：创意与产品卖点无关；画面元素过杂；AI 拼贴感明显

```text
{product} floating in {dramatic_environment}, {effects: splash/particles/smoke}, {bold colors}, art direction: {style}, ultra-detailed, cinematic lighting, award-winning advertising
```

## 13 尺寸规格+使用步骤图

- 构图：产品占比 40-50%；留白 标注区留白 ≥30%；版式：三视图 / 标注线 / 步骤时间线，留出标注区
- 角度：标准三视图 = `front, side and back orthographic views`
- 文字：default: 以数字标注为主：尺寸线 + 数字，单位明确；style: 标注线细线 #888888，数字 14-16pt #2D2D2D
- 品类加成：beauty: dimension callout badge, usage ritual steps, ingredient percentages；electronics: precise dimensions with comparison objects, port specs；food: serving size, preparation steps, nutritional highlights；fashion: size chart with body measurements, care instructions
- 翻车：标注数字与实际不符；产品比例失真；标注线宽和颜色不统一

```text
Premium {category} specification and ritual guide, luxury editorial. White background, subtle border. Top: {product} centered with dimension badge. Left: 4-step usage guide with decorative icons. Right: highlights with colored pills. Bottom: {data}. Decorative corner accents. Magazine-quality, 2000x2800px
```

## 14 多产品套装/组合展示

- 构图：产品占比 整体 60-70%；留白 ≥25%
- 角度：组合群像 = `group arrangement, slight high angle looking down`
- 光/底：；{background_description}
- 文字：default: 无文字或一个套装名
- 品类加成：beauty: complete routine (cleanser → toner → serum → cream), gift-ready；food: product range, variety pack, flavor assortment；fashion: outfit coordination pieces, colorway options；home: collection of coordinating items
- 翻车：产品数量与要求不符；大小比例失真；每个产品光影方向不一致

```text
Luxury {category} gift set on premium surface: {product_list}. Organized composition with product cards. Scattered: gold foil, pearls, dried flowers, velvet ribbon. Bottom left: set description. Bottom right: price with original crossed out. Soft directional lighting, premium photography
```

## 15 电商直播间场景

- 构图：产品占比 30%；留白 0-10%（UI 满版，不强制大留白）；版式：竖屏直播间：主播 + 产品同框 + UI 元素（顶部条/价格贴/弹幕）
- 角度：手机竖屏视角 = `vertical phone screen view of a livestream room`
- 光/底：ring light from front, warm indoor overhead mixing in；real home-style livestream setup
- 文字：ui: 价格贴/促销条文字简短（价格 + 一个卖点），平台母语；note: UI 元素明确描述位置和内容，避免随机乱码
- 品类加成：beauty: host demonstrating application, showing texture, real-time swatching；fashion: host wearing/showing clothing, fit demo, fabric close-up；food: host tasting/preparing, showing freshness, unboxing；electronics: host demonstrating features, hands-on product demo
- 防 AI 味：CRITICAL: (1) Phone screen capture style, (2) Ring light: circular catchlight in eyes, (3) Real skin: pores, undereye darkness, NOT smoothed, (4) Real environment: slightly messy, real objects, (5) Warm yellowish cast, (6) Slight noise, (7) 'NOT AI-generated look, NOT plastic smooth', (8) Kodak Portra 400 tone, (9) Realistic UI overlay
- 翻车：UI 文字乱码；人手畸形；出现假平台 logo

```text
Ultra-realistic Douyin livestream screenshot, phone screen capture. Host in casual {outfit}, minimal makeup, visible pores and skin texture, NOT retouched. Demonstrating {product}, showing details, other hand gesturing. Ring light natural shine, NOT plastic AI look. Background: real home setup - product shelf, whiteboard with prices, string lights, coffee mug. Phone UI: LIVE badge, viewer count, scrolling comments, product card with price, yellow buy button. Warm cast, slight noise, Kodak Portra 400 tone, NOT AI-generated look, 1080x1920px
```

## 16 虚拟试穿/产品融入场景

- 构图：产品占比 30-40%；留白 ≥35%
- 角度：融入环境视角 = `product naturally integrated into the scene with matching perspective`
- 文字：default: 无文字
- 品类加成：beauty: spa bathroom, vanity mirror, botanical elements, skincare ritual；fashion: model wearing item in appropriate setting, natural styling；furniture: product in complete room setting, complementary decor；electronics: modern desk setup, in-use context, tech-forward
- 翻车：产品悬浮没有接触阴影；透视与场景不匹配；产品细节变形走样；产品细节与参考图不一致（必须 --image 传入并出图后核对）

```text
Cinematic luxury {category} integration. High-end {interior} with {materials}. {product} prominently displayed. Morning sunlight through frosted glass, ethereal light rays. Fresh flowers, botanical elements. Product label visible, ingredient card beside it. Decorative: tray, pearls, gold foil. Color: {colors}. Cinematic depth, warm grading, premium, 1080x1620px
```

## 17 技术拆解/爆炸图

- 构图：产品占比 60-70%；留白 ≥20%（部件展开占位）；版式：部件沿展开轴线排列，等距视角
- 角度：等距拆解 = `isometric exploded view, components separated along axis lines`
- 光/底：；clean light gray or white
- 文字：labels: 部件标注（可选）：细线引出 + 短词，风格统一
- 品类加成：electronics: highlight circuit boards, chips, battery modules with spec labels；audio: show speaker drivers, diaphragms, ANC modules, battery size；wearables: include sensors, display panel, waterproof seals, strap mechanism；home_appliance: show motor, filter system, internal wiring, control board
- 翻车：部件数量与真实不符；透视关系混乱；标注文字乱码

```text
Product exploded view. {product} disassembled into 5 components floating in mid-air with spacing, arranged vertically. Clean light gray background. Soft shadows beneath each part. Technical illustration style, no text
```

## 18 隐形模特

- 构图：产品占比 65-75%；留白 ≥25%
- 角度：正面立体 = `3D ghost mannequin effect, front view with natural volume`；背面立体 = `ghost mannequin rear view showing back construction`
- 光/底：three-point studio setup, gentle dimension；clean white or soft gray gradient
- 文字：default: 无文字
- 品类加成：shirts: collar standing naturally, top buttons detail, cuff visibility；dresses: natural waist cinch, skirt drape showing fabric weight, back zipper detail；coats: architectural shoulder structure, fabric texture visible, button and pocket details；knitwear: visible knit pattern and texture, natural stretch around body contours
- 翻车：画面出现人体部位；服装扁平没有立体感；背景杂色

```text
Ghost mannequin photography. {product} on invisible mannequin, natural body contours visible. Fabric drapes naturally showing material weight. Pure white background. Soft studio lighting, fashion e-commerce standard
```

## 19 产品多角度网格

- 构图：产品占比 等分网格每格 40%；主次配色布局主产品 42-48%、小产品每格 24-30%；留白 每格 ≥20%；版式：网格布局 2×2 / 3×3，或主色产品左侧大图 + 右侧 2×2 已确认配色网格
- 角度：正面 = `front view`；侧面 = `90-degree side profile`；背面 = `rear view`；俯视 = `90-degree overhead view`
- 光/底：；clean white in each cell
- 文字：labels: 每格可加角度或配色短标签，11-16pt 现代无衬线半粗体，#111111，风格统一；sku: 配色页可在色名下加 10-13pt 现代无衬线常规体 #3A3A3A 的 SKU；色名与 SKU 必须由用户确认；limit: 单格最多两行文字；不得生成未确认颜色、型号、货号或价格
- 品类加成：beauty: show bottle angle, cap detail, texture close-up, and open product；electronics: show front face, side ports, back panel, and included accessories；fashion: show front view, back view, detail close-up, and fabric texture；food: show packaging front, back nutrition, open product, and serving suggestion
- 翻车：各格光线色温不一致（所有格子固定同一灯位、曝光和白平衡）；产品在各格大小不一（等分网格固定产品占比；主次布局只允许主产品更大）；角度重复没有信息增量（多角度模式按正面、侧面、背面、俯视分配）；生成未确认颜色或 SKU（配色模式只读取用户确认的颜色名单、色名和货号）

```text
2x2 product grid. {product} shown from 4 angles: front, side, back, top-down. Clean white background per cell. Thin borders. Uniform studio lighting, 2000x2000px
```

## 20 杂志大片/封面

- 构图：产品占比 30-40%；留白 ≥35%（编辑风排版留白）
- 角度：编辑部人像 = `editorial fashion pose, dramatic lighting`；场景大片 = `cinematic wide editorial scene`
- 光/底：beauty dish + rim light, editorial setup；studio backdrop in warm/tonal color
- 文字：masthead: 刊名（占位符）+ 封面标题，衬线体（Didot 类）；note: 文字内容用占位描述或用户提供的确切文字
- 品类加成：skincare: dewy skin, product held at chin level, beauty lighting；fragrance: atmospheric smoke, contemplative mood, bottle prominent；fashion: confident pose, outfit fully visible, dramatic lighting；jewelry: close-up on hands/neck, editorial styling, luxury backdrop
- 防 AI 味：For authentic editorial feel: specify actual camera (Phase One IQ4, Canon EOS R5 85mm f/1.2), add visible skin texture, use real beauty lighting terminology
- 翻车：像普通电商图没有大片感；封面文字乱码；构图平淡

```text
Beauty magazine cover. Woman with glowing skin holding {product} near face. Beauty dish lighting, soft background. Top area for masthead. Vogue-quality editorial, 1080x1350px
```

## 21 季节主题网格

- 构图：产品占比 30%；留白 ≥40%
- 角度：季节符号场景 = `product staged with seasonal props and color grading`
- 文字：labels: 节日/季节短标签，≤6 字
- 品类加成：skincare: spring=blossoms+dew, summer=sun+kisses, autumn=cozy+cream, winter=frost+glow；fragrance: each season with matching botanical elements and color palette；fashion: season-appropriate styling visible in each quadrant；food: seasonal ingredients and color palette matching product
- 翻车：季节符号用错（圣诞配樱花）；系列各张风格漂移；节日元素堆砌杂乱

```text
2x2 seasonal grid. Same {product} in four settings: Spring with cherry blossoms, Summer with citrus and sunshine, Autumn with maple leaves, Winter with pine and snow. Consistent product angle, 2000x2000px
```

## 22 奢华氛围渲染

- 构图：产品占比 30-35%；留白 ≥50%（留白就是高级感）
- 角度：单光源戏剧光 = `single dramatic key light on dark background`；微距质感 = `macro on material finish with elegant reflections`
- 光/底：dramatic rim light + cool ambient fill；infinite dark void with subtle gradient
- 文字：default: 品牌 slogan，serif 衬线体（Didot 类），小字号低调放置
- 品类加成：fragrance: multi-layer smoke + matching botanical elements, amber liquid visible inside；skincare: ethereal glow around product, subtle condensation, dreamy quality；jewelry: diamond-like light bokeh, dark background, sparkle and reflection focus；wine: rich amber or ruby liquid, smoke wisps matching color, candlelight warmth
- 翻车：画面太亮失去奢华感；反光过曝；元素太多显得廉价

```text
Luxury product photography with atmospheric effects. {product} on polished dark surface, surrounded by wisps of purple-blue smoke. Dramatic rim light. Deep black background. cinematic quality
```

## 23 设备界面模型

- 构图：产品占比 40-50%；留白 ≥35%
- 角度：正面悬浮 = `front-facing floating device mockup with soft shadow`；多设备组合 = `laptop + phone + tablet arranged in a clean composition`
- 光/底：natural window light with warm fill
- 文字：screen: 屏幕内容用 UI 占位描述（色块/假文），明确 no readable text 或提供真实界面描述
- 品类加成：saas: show dashboard with charts, KPI cards, data visualizations；mobile_app: show app interface on phone, notification visible, clean UI；ecommerce_platform: show store admin dashboard with product listings and analytics；fintech: show financial dashboard with graphs, portfolio summary
- 翻车：屏幕内容乱码；设备比例错误；反光遮挡了界面

```text
Product mockup on laptop. Silver laptop on white desk, screen showing modern dashboard with charts. Coffee cup and small plant nearby. Natural window light. Clean product photography
```

## 24 店铺门面/空间摄影

- 构图：产品占比 建筑主体占 60-70%；留白 天空/街道留 30%
- 角度：正面 3/4 街面 = `slight 3/4 angle showing full front facade`；低角度仰视 = `low angle looking up at the building`；航拍 = `aerial drone view of the storefront and street`
- 光/底：golden hour exterior or warm ambient interior
- 文字：signage: 招牌文字用占位符或用户提供的确切文字，其余 no readable text
- 品类加成：coffee_shop: espresso machine visible, warm wood tones, latte art, pastry display；beauty_store: illuminated niches, marble counter, product wall, consultation area；fashion_boutique: minimalist racks, curated display, premium flooring, mirror accents；restaurant: table setting, kitchen pass visible, ambient lighting, menu display
- 翻车：招牌文字乱码；建筑透视倾斜；街道空间比例失真

```text
Storefront photography. Modern {business} with glass windows showing warm interior. Entrance with potted plants. Golden hour light. Architectural photography
```

## 25 运动/健身广告

- 构图：产品占比 35-40%；留白 ≥30%
- 角度：动态瞬间 = `frozen mid-action moment, motion energy`；装备特写 = `close-up on gear detail with sweat and texture`
- 光/底：；minimal dark studio with reflective floor
- 文字：headline: 口号式标题，粗体无衬线，≤6 词
- 品类加成：running_shoes: dynamic forward motion, speed lines, track or road surface context；basketball: mid-dunk or crossover pose, stadium lighting, court texture；fitness_equipment: athlete using product, sweat detail, gym environment；sportswear: compression fit visible, fabric technology highlighted, movement pose
- 翻车：人物动作僵硬不自然；产品被动态元素盖住；dynamic 感不足像摆拍

```text
Sports advertising photo. {product} placed diagonally on reflective dark surface. Dramatic side lighting, speed lines around product. Bold headline text. Dynamic and energetic, 1080x1350px
```

## 26 箱包功能证据图

- 构图：产品占比 42-62%（按变体）；留白 ≥28%；版式：标题区 + 产品证据区 + 单列标注/放大框/图标区；每页只证明一个功能主题
- 角度：正面 3/4 = `front-facing at a slight three-quarter angle`；正背面 = `straight rear view, camera parallel to the back panel`；背面 3/4 = `rear three-quarter view exposing the confirmed back feature`；略高前侧视角 = `slightly elevated front three-quarter view`
- 光/底：neutral-cool studio lighting with directional side light preserving dark textile texture and edge separation；{background_color}
- 文字：headline: 主标题 28-42pt，现代无衬线粗体，#111111，最多两行；feature_heading: 功能标题 11-15pt，现代无衬线半粗体，#111111，每项不超过 24 个拉丁字符；feature_body: 说明 9-12pt，现代无衬线常规体，#3A3A3A，最多两行
- 品类加成：backpacks: preserve the exact pocket count, zipper routes, straps, adjusters, back padding, side pockets, trolley sleeves and hidden-pocket placement from the supplied references；travel-bags: show luggage attachment or security access only when the corresponding product structure is visible or explicitly confirmed；handbags: use callouts for visible closures, handles, straps and compartments; do not infer an unseen interior
- 防 AI 味：Keep callout endpoints attached to real seams, pockets, zippers, straps or hardware visible in the references. A magnified inset must reproduce the same structure, material, color and orientation as its source area.
- 翻车：把风格参考中的功能当成当前产品事实（只允许使用产品参考图可见或用户明确确认的结构与声明）；背面、侧面或内部结构被模型补画（缺对应参考图时停止该功能页或使用证据占位，不生成猜测结构）；引导线或放大框没有落在真实结构上（端点必须锚定可见的车线、口袋、拉链、肩带或五金）；容量页退化成纯平铺或物品喧宾夺主（产品保持 42-48%，物品只在右侧对齐且必须已确认）

```text
Evidence-led e-commerce bag feature infographic, square 1:1. Preserve the exact supplied backpack identity. Front-facing slight 3/4 view on the left occupying 52% of the canvas. Add five short callouts in one aligned right column, each anchored to a visible compartment or zipper path from the reference. Clean #F4F4F4 background, neutral-cool side lighting, at least 30% whitespace. Use only confirmed text. No invented interior, hidden pocket, capacity number, fake logo, extra zipper, watermark, or unsupported claim.
```
