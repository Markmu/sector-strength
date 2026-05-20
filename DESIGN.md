---
name: Sector Strength
description: 股票板块强度分析平台
colors:
  slate-primary: "#5E6B7A"
  slate-primary-hover: "#4D5A69"
  slate-primary-light: "#D5DAE0"
  ink-slate: "#242830"
  cool-paper: "#F4F5F7"
  mist-border: "#E0E3E7"
  muted-slate: "#7C828E"
  faint-slate: "#A5ABB5"
  secondary-slate: "#EAECEF"
  pure-white: "#FFFFFF"
  rise-red: "#C04E42"
  fall-green: "#4A8B6F"
  destructive-red: "#C04E42"
typography:
  display:
    fontFamily: "Geist Sans, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "24px"
    fontWeight: 700
    lineHeight: 1.2
  headline:
    fontFamily: "Geist Sans, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.3
  title:
    fontFamily: "Geist Sans, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "Geist Sans, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Geist Sans, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0.05em"
  mono:
    fontFamily: "Geist Mono, SF Mono, Monaco, Cascadia Code, Roboto Mono, Consolas, monospace"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.slate-primary}"
    textColor: "{colors.pure-white}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  button-primary-hover:
    backgroundColor: "{colors.slate-primary-hover}"
  button-secondary:
    backgroundColor: "{colors.secondary-slate}"
    textColor: "{colors.ink-slate}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  button-outline:
    backgroundColor: "{colors.pure-white}"
    textColor: "{colors.ink-slate}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.muted-slate}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  card-default:
    backgroundColor: "{colors.pure-white}"
    textColor: "{colors.ink-slate}"
    rounded: "{rounded.lg}"
    padding: "24px"
  input-default:
    backgroundColor: "{colors.pure-white}"
    textColor: "{colors.ink-slate}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  table-header:
    backgroundColor: "{colors.cool-paper}"
    textColor: "{colors.muted-slate}"
    rounded: "{rounded.lg}"
---

# Design System: Sector Strength

## 1. Overview

**Creative North Star: "The Signal Filter"**

从市场噪音中提取清晰信号的视觉系统。每个像素要么承载数据，要么服务于数据的可读性。没有装饰层，没有情绪化设计，只有冷静的信号呈现。

桌面端盘后复盘场景，屏幕空间充裕，信息密度是美德。用户需要快速扫视板块强弱、定位机会，而非被 UI 打断思考。视觉系统的工作是让自己消失，让数据浮现。

浅色主题，以微带蓝色调的冷灰色为基底，石墨蓝（slate）作为唯一的交互强调色。功能色遵循中国 A 股惯例：红色代表涨/强势，绿色代表跌/弱势。9 级分类色阶从深红（最强）到深绿（最弱），始终搭配数值标签确保无障碍。整体克制、精确、可预测。

**Key Characteristics:**
- 信息密度高，间距紧凑，数据优先
- 单一强调色（石墨蓝），其余均为功能色或中性色
- 低饱和度色板：所有颜色 chroma ≤ 0.06，不刺激不疲劳
- 中式配色：红涨绿跌，符合 A 股市场习惯
- 极低透明度阴影，层次感来自边框和背景色差
- 交互反馈克制：hover 变色、focus 环、loading 旋转，没有多余动效

## 2. Colors

信号过滤器的色彩逻辑：大面积冷灰中性底色上，用极少量石墨蓝强调色标记可操作元素，用色阶编码数据含义。所有颜色经过低饱和度处理，适合长时间复盘分析。

### Primary
- **石墨蓝** (#5E6B7A, oklch 48% 0.04 250): 唯一的交互强调色。用于按钮、焦点环、激活态侧边栏、排序指示器、loading 旋转。出现在 ≤10% 的屏幕面积中。不带渐变，纯色即是力量。

### Neutral
- **墨石蓝** (#242830, oklch 18% 0.015 250): 所有文字的默认色。微带蓝色调的深灰，不是纯黑，避免刺眼对比。
- **冷灰纸** (#F4F5F7, oklch 97% 0.005 250): 页面底色、表头背景、hover 态。微带蓝色调的灰白，不是纯白。
- **薄雾灰** (#E0E3E7, oklch 91% 0.005 250): 边框、分隔线。轻微可见的边界，不喧宾夺主。
- **次级灰** (#EAECEF, oklch 94% 0.005 250): 次级背景（按钮 secondary、表格行分隔）。比底色深一步。
- **中性灰** (#7C828E, oklch 55% 0.01 250): 辅助文字、副标题、说明文案。满足 WCAG AA 对比度。
- **淡灰** (#A5ABB5, oklch 72% 0.008 250): 占位符文字、禁用态文字。最浅的可读灰色。
- **纯白** (#FFFFFF): 卡片背景、输入框背景。用于需要清晰边界的容器。

### Functional
- **涨色** (#C04E42, oklch 55% 0.12 20): 上升趋势、高强度得分（≥80）、反弹状态、市场交易指示。低饱和暖红，不刺眼。
- **跌色** (#4A8B6F, oklch 55% 0.08 155): 下降趋势、低强度得分（<60）、调整状态。低饱和青绿，中性冷静。
- **破坏色** (#C04E42): 错误状态、危险操作、表单验证失败。与涨色同源，但语境明确区分。

### Data Encoding
- **9 级分类色阶（中式）**: red-700 → red-500 → orange-500 → amber-500 → yellow-500 → lime-500 → green-500 → emerald-500 → emerald-700。从最强（深红）到最弱（深绿），始终搭配白色或黑色文字保证可读性。数值标签始终与色块同时出现，不单独依赖颜色传递信息。

**The Signal Rule.** 石墨蓝出现在 ≤10% 的屏幕面积中。它的稀有性就是它的信号强度。如果一个页面上超过 10% 的元素都是石墨蓝，说明层次结构出了问题。

## 3. Typography

**Display Font:** Geist Sans（系统无衬线回退）
**Body Font:** Geist Sans（同上）
**Mono Font:** Geist Mono（数据表格、代码、数值对齐场景）

**Character:** 单一字体家族，通过字重（400 → 700）和字号（12px → 24px）建立层次。没有衬线/无衬线混搭的装饰感，纯功能主义。

### Hierarchy
- **Display** (700, 24px, 1.2): 页面主标题，每个页面最多一个。
- **Headline** (700, 20px, 1.3): 卡片标题、区块标题。
- **Title** (600, 16px, 1.4): 表单标签、小组件标题。
- **Body** (400, 14px, 1.5): 正文、描述文字、表格内容。行宽限制 65ch。
- **Label** (600, 12px, 0.05em, uppercase): 表头、辅助标签、状态标记。全大写 + 宽字距确保小字号下的可读性。
- **Mono** (400, 13px, 1.5): 数值数据、代码片段。等宽字体对齐表格中的数字列。

**The Weight Rule.** 字重只有四档：400（正文）、500（中等强调）、600（标题/标签）、700（主标题）。不使用 300 以下的轻字重，复盘场景下所有文字必须清晰可读。

## 4. Elevation

层次感来自背景色差和 1px 边框，不来自阴影。阴影存在但极度克制，透明度在 0.04 到 0.08 之间，仅用于卡片和滚动后的 Header，营造微弱的浮起感而非戏剧性的深度。

### Shadow Vocabulary
- **微弱投影** (`0 1px 2px rgba(0,0,0,0.05)`): 卡片默认态。
- **中等投影** (`0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -1px rgba(0,0,0,0.04)`): 卡片 hover 态、滚动后 Header。
- **较强投影** (`0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -2px rgba(0,0,0,0.04)`): 弹窗、下拉菜单。

**The Flat-By-Default Rule.** 静态元素是平的。阴影仅作为状态响应出现（hover、滚动、浮层）。如果一个元素在默认态就有明显阴影，它抢了数据的注意力。

## 5. Components

所有组件共享"克制而精确"的交互气质：hover 时微弱变色，focus 时清晰的石墨蓝环，没有弹跳或缩放动画。

### Buttons
- **Shape:** 温和圆角（8px），不锋利也不圆润。
- **Primary:** 石墨蓝纯色底 + 白色文字 + 微弱阴影。Hover 时加深至 #4D5A69。无渐变。
- **Secondary:** 次级灰底 + 墨石蓝文字。Hover 加深透明度。
- **Outline:** 白底 + 薄雾灰边框 + 墨石蓝文字。Hover 边框变为石墨蓝。
- **Ghost:** 透明底 + 中性灰文字。Hover 次级灰底 + 墨石蓝文字。
- **Danger:** 破坏色底 + 白色文字。Hover 加深。
- **Sizes:** sm (px-3 py-1.5), md (px-5 py-2.5), lg (px-6 py-3)。
- **Focus:** 2px 石墨蓝环 + 2px 偏移。

### Cards / Containers
- **Corner:** 12px 圆角，比按钮宽一圈，视觉上区分容器和操作元素。
- **Default:** 白底 + 1px 薄雾灰边框 + 微弱投影。最常用的容器。
- **Outlined:** 白底 + 2px 薄雾灰边框。强调边界的场景。
- **Elevated:** 白底 + 中等投影 + hover 时增强阴影。可交互卡片。
- **Padding:** none / sm(16px) / md(24px) / lg(32px)，默认 md。

### Inputs / Fields
- **Style:** 白底 + 1px 薄雾灰边框 + 8px 圆角。
- **Focus:** 边框变石墨蓝 + 石墨蓝低透明度环。
- **Error:** 破坏色边框 + 破坏色淡底 + 破坏色错误提示。
- **Disabled:** 50% 透明度 + 禁止光标。

### Table
- **Container:** 12px 圆角 + 薄雾灰边框 + 白底。
- **Header:** 冷灰纸底 + 12px 全大写 Label + 可排序时 hover 变次级灰。
- **Sort indicator:** 石墨蓝箭头 SVG。
- **Rows:** hover 时冷灰纸底 + 淡出过渡。斑马纹可选。
- **Loading:** 石墨蓝旋转圆 + "加载中..." 文案。
- **Empty:** 中性灰居中文案 "暂无数据"。

### Navigation (Sidebar)
- **Width:** 256px（展开）/ 64px（折叠），200ms 过渡。
- **Active item:** 石墨蓝纯色底 + 白色文字 + 微弱阴影。这是石墨蓝密度最高的元素。
- **Inactive item:** 中性灰文字 + hover 冷灰纸底。
- **Logo area:** 48px 高 + 底部薄雾灰边框。
- **User area:** 底部固定 + 顶部薄雾灰边框 + 用户首字母头像（石墨蓝圆角方块）。

### Ranking Item (Signature Component)
- **Layout:** 水平排列：排名编号 → 名称/代码 → 趋势箭头 → 强度得分。
- **Rank number:** 淡灰色 + 居中 + 24px 宽。
- **Trend arrow:** ↑（涨色红）/ →（中性灰）/ ↓（跌色绿），18px 加粗。
- **Strength score:** 18px 加粗，按区间着色：≥80 涨色红，≥60 琥珀色，<60 跌色绿。
- **Hover:** 冷灰纸底 + 整行可点击。

## 6. Do's and Don'ts

### Do:
- **Do** 在数据可视化中始终同时提供色块和数值标签，确保红绿色盲用户可以获取完整信息。
- **Do** 保持石墨蓝在 ≤10% 的屏幕面积内，让它保持信号强度。
- **Do** 使用字重和字号建立层次，而非颜色数量。
- **Do** 让表格行高和间距紧凑（py-3），信息密度优先于呼吸感。
- **Do** 在 hover/focus 时使用可预测的变色反馈（次级灰底、石墨蓝边框），不要发明新的交互模式。
- **Do** 遵循中式红涨绿跌配色，保持与 A 股市场习惯一致。

### Don't:
- **Don't** 使用超过 1px 的彩色左边框（border-left）作为卡片或列表项的装饰条纹。
- **Don't** 使用渐变文字（background-clip: text + gradient）。用单色 + 字重表达强调。
- **Don't** 在默认态使用毛玻璃效果（backdrop-blur）。仅在 Header 滚动后使用，且保持克制。
- **Don't** 添加弹跳、弹性、缩放等装饰性动画。过渡限于颜色、阴影、位移，时长 200ms，ease-out。
- **Don't** 在一个页面上使用超过 3 种字号差异超过 1.5 倍的文字。层次要紧凑，不要戏剧化。
- **Don't** 使用纯黑（#000）或纯白（#fff）作为大面积底色。始终用微调后的中性色（墨石蓝、冷灰纸）。
- **Don't** 在按钮或交互元素上使用渐变背景。纯色 + 字重变化足矣。
- **Don't** 使用西式绿涨红跌配色。本产品面向中国 A 股市场，红涨绿跌是标准。
