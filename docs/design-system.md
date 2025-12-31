# Sector Strength - 设计系统文档

## 版本
- v3.0.0
- 最后更新: 2025-12-31

## 设计理念
**晨曦实验室美学** - 清新、明亮、专业的数据分析界面。如同清晨阳光透过实验室玻璃窗，数据在洁净的空间中清晰呈现。克制而不失精致，现代而不失温度。

> "Clarity is the ultimate sophistication."

---

## 1. 色彩系统

### 1.1 主题色
```css
/* 主色调 - 精密青 */
--primary-50:  #ecfeff
--primary-100: #cffafe
--primary-200: #a5f3fc
--primary-300: #67e8f9
--primary-400: #22d3ee  /* 主色 - cyan-400 */
--primary-500: #06b6d4  /* 品牌色 - cyan-500 */
--primary-600: #0891b2  /* cyan-600 */
--primary-700: #0e7490  /* cyan-700 */
```

### 1.2 基础色系 - 清透基调
```css
/* 背景色 - 层次丰富的浅灰系统 */
--bg-deep:      #f8f9fb   /* 主背景 - 淡蓝灰 */
--bg-surface:   #ffffff   /* 卡片/容器背景 - 纯白 */
--bg-elevated:  #ffffff   /* 悬浮元素背景 */
--bg-input:     #ffffff   /* 输入框背景 */
--bg-subtle:    #f1f3f5   /* 次级背景 */

/* 边框色 - 精致分割 */
--border-subtle:  #f1f3f5  /* 微妙边框 */
--border-default: #e9ecef  /* 默认边框 */
--border-strong:  #dee2e6  /* 强调边框 */

/* 文本色 - 清晰可读 */
--text-primary:   #1a1a2e   /* 深蓝灰 - 主要文字 */
--text-secondary: #6c757d   /* 中灰 - 次要文字 */
--text-tertiary:  #adb5bd   /* 浅灰 - 辅助文字 */
--text-inverse:   #ffffff   /* 纯白 - 反白文字 */
```

### 1.3 等级色彩系统 - 精致渐变
```css
/* S+ 级 - 荣耀金 (90-100分) */
--grade-s-plus-from: #fcd34d  /* amber-300 */
--grade-s-plus-via:   #f59e0b  /* amber-500 */
--grade-s-plus-to:     #d97706  /* amber-600 */
--grade-s-plus-text:   #fef3c7  /* amber-100 */
/* bg-gradient-to-r from-amber-300 via-amber-500 to-amber-600 */

/* S 级 - 烈焰橙 (80-89分) */
--grade-s-from:    #fb923c  /* orange-400 */
--grade-s-to:      #ea580c  /* orange-600 */
--grade-s-text:    #fed7aa  /* orange-200 */
/* bg-gradient-to-r from-orange-400 to-orange-600 */

/* A+ 级 - 明亮黄 (70-79分) */
--grade-a-plus-from: #facc15  /* yellow-400 */
--grade-a-plus-to:   #ca8a04  /* yellow-600 */
--grade-a-plus-text: #fef08a  /* yellow-200 */
/* bg-gradient-to-r from-yellow-400 to-yellow-600 */

/* A 级 - 生机绿 (60-69分) */
--grade-a-from:  #a3e635  /* lime-400 */
--grade-a-to:    #65a30d  /* lime-600 */
--grade-a-text:  #d9f99d  /* lime-200 */
/* bg-gradient-to-r from-lime-400 to-lime-600 */

/* B+ 级 - 翡翠青 (50-59分) */
--grade-b-plus-from: #34d399  /* emerald-400 */
--grade-b-plus-to:   #059669  /* emerald-600 */
--grade-b-plus-text: #6ee7b7  /* emerald-300 */
/* bg-gradient-to-r from-emerald-400 to-emerald-600 */

/* B 级 - 清澈蓝 (40-49分) */
--grade-b-from:  #22d3ee  /* cyan-400 */
--grade-b-to:    #0891b2  /* cyan-600 */
--grade-b-text:  #67e8f9  /* cyan-300 */
/* bg-gradient-to-r from-cyan-400 to-cyan-600 */

/* C 级 - 谨慎紫 (30-39分) */
--grade-c-from:  #a78bfa  /* violet-400 */
--grade-c-to:    #7c3aed  /* violet-600 */
--grade-c-text:  #c4b5fd  /* violet-300 */
/* bg-gradient-to-r from-violet-400 to-violet-600 */

/* D 级 - 警戒灰 (0-29分) */
--grade-d-from:  #a1a1aa  /* gray-400 */
--grade-d-to:    #737373  /* gray-500 */
--grade-d-text:  #d4d4d8  /* gray-300 */
/* bg-gradient-to-r from-gray-400 to-gray-500 */
```

### 1.4 语义色
```css
/* 成功 */
--success-bg:   rgba(34, 197, 94, 0.12)
--success-text: #16a34a
--success-border: rgba(34, 197, 94, 0.25)

/* 警告 */
--warning-bg:   rgba(251, 191, 36, 0.12)
--warning-text: #d97706
--warning-border: rgba(251, 191, 36, 0.25)

/* 错误 */
--error-bg:     rgba(239, 68, 68, 0.08)
--error-text:   #dc2626
--error-border: rgba(239, 68, 68, 0.2)

/* 信息 */
--info-bg:      rgba(6, 182, 212, 0.12)
--info-text:    #0891b2
--info-border:  rgba(6, 182, 212, 0.25)
```

---

## 2. 排版系统

### 2.1 字体家族
```css
/* 主字体 - Geist (Vercel设计) */
--font-sans: var(--font-geist-sans), -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;

/* 等宽字体 - Geist Mono */
--font-mono: var(--font-geist-mono), "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace;
```

**字体配置 (Next.js)**:
```tsx
// app/layout.tsx
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className={`${GeistSans.variable} ${GeistMono.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
```

**安装**:
```bash
npm install geist
```

### 2.2 字体尺度
```css
/* Display - 超大标题 */
--text-4xl:  2.25rem;  /* 36px - line-height: 2.5rem - 用于页面主标题 */
--text-3xl:  1.875rem; /* 30px - line-height: 2.25rem - 用于章节标题 */

/* Heading */
--text-2xl:  1.5rem;   /* 24px - line-height: 2rem - 大标题 */
--text-xl:   1.25rem;  /* 20px - line-height: 1.75rem - 中标题 */
--text-lg:   1.125rem; /* 18px - line-height: 1.75rem - 小标题 */

/* Body */
--text-base: 1rem;     /* 16px - line-height: 1.5rem - 正文 */
--text-sm:   0.875rem; /* 14px - line-height: 1.25rem - 小字 */
--text-xs:   0.75rem;  /* 12px - line-height: 1rem - 辅助文字 */

/* Data Display */
--text-data-xl: 3rem;   /* 48px - 大数据展示 */
--text-data-lg: 2.5rem; /* 40px - 中数据展示 */
--text-data-md: 2rem;   /* 32px - 小数据展示 */
```

### 2.3 字重与样式
```css
/* 字重 */
--font-light:   300  /* 极少使用 */
--font-normal:  400  /* 正文 */
--font-medium:  500  /* 强调 */
--font-semibold: 600  /* 小标题 */
--font-bold:    700  /* 标题 */

/* 字母间距 */
--tracking-tight:    -0.025em  /* 大标题 */
--tracking-normal:   0         /* 默认 */
--tracking-wide:     0.025em   /* 小型大写字母 */

/* 行高 */
--leading-tight:   1.25  /* 标题 */
--leading-normal:  1.5   /* 正文 */
--leading-relaxed: 1.75  /* 长文本 */
```

---

## 3. 间距系统

采用 4px 基础单位（更精确）：

```css
--spacing-0:   0
--spacing-1:   0.25rem  /* 4px */
--spacing-2:   0.5rem   /* 8px */
--spacing-3:   0.75rem  /* 12px */
--spacing-4:   1rem     /* 16px */
--spacing-5:   1.25rem  /* 20px */
--spacing-6:   1.5rem   /* 24px */
--spacing-8:   2rem     /* 32px */
--spacing-10:  2.5rem   /* 40px */
--spacing-12:  3rem     /* 48px */
--spacing-16:  4rem     /* 64px */
```

### 推荐间距
- 页面内边距: `p-6` 或 `p-8`
- 卡片内边距: `p-6`
- 卡片间距: `gap-6`
- 章节间距: `mb-12`
- 元素间距: `gap-4`

---

## 4. 组件规范

### 4.1 卡片 (Card)
```tsx
// 基础卡片
<div className="bg-white rounded-xl border border-[#e9ecef] shadow-sm">
  <div className="p-6">
    {/* 内容 */}
  </div>
</div>

// 悬浮卡片（带微妙阴影）
<div className="bg-white rounded-xl border border-[#e9ecef] shadow-md hover:shadow-lg
                transition-shadow duration-200">
  <div className="p-6">
    {/* 内容 */}
  </div>
</div>

// 强调卡片
<div className="bg-white rounded-xl border border-[#dee2e6] shadow-md">
  <div className="p-6">
    {/* 内容 */}
  </div>
</div>

// 次级背景卡片
<div className="bg-[#f1f3f5] rounded-xl border border-transparent">
  <div className="p-6">
    {/* 内容 */}
  </div>
</div>
```

### 4.2 按钮 (Button)
```tsx
// 主按钮 - 青色渐变
<button className="px-5 py-2.5 bg-gradient-to-r from-cyan-400 to-cyan-500
                   hover:from-cyan-500 hover:to-cyan-600
                   text-white font-medium rounded-lg
                   transition-all duration-200
                   shadow-sm hover:shadow-md">
  按钮
</button>

// 次按钮 - 边框样式
<button className="px-5 py-2.5 bg-transparent
                   text-[#1a1a2e] font-medium rounded-lg
                   border border-[#dee2e6]
                   hover:border-cyan-400 hover:bg-cyan-50/50
                   transition-all duration-200">
  按钮
</button>

// 文字按钮
<button className="px-4 py-2 text-cyan-600 hover:text-cyan-700
                   font-medium transition-colors duration-200">
  按钮
</button>

// 图标按钮
<button className="p-2 text-[#6c757d] hover:text-[#1a1a2e]
                   hover:bg-[#f1f3f5] rounded-lg
                   transition-all duration-200">
  <Icon className="w-5 h-5" />
</button>
```

### 4.3 筛选标签 (Filter Tab)
```tsx
// 选中状态 - 青色高亮
<button className="px-4 py-2
                   bg-cyan-500 text-white
                   border border-cyan-500
                   rounded-lg font-medium
                   shadow-sm
                   transition-all duration-200">
  选中
</button>

// 未选中状态
<button className="px-4 py-2
                   text-[#6c757d] hover:text-[#1a1a2e]
                   border border-[#e9ecef] hover:border-[#dee2e6]
                   bg-white hover:bg-[#f8f9fb]
                   rounded-lg font-medium
                   transition-all duration-200">
  未选中
</button>
```

### 4.4 输入框 (Input)
```tsx
<input
  className="w-full px-4 py-2.5
             bg-white border border-[#dee2e6]
             rounded-lg
             text-[#1a1a2e] placeholder-[#adb5bd]
             focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100
             transition-all duration-200"
  placeholder="输入内容..."
/>
```

### 4.5 数据表格 (Data Table)
```tsx
<div className="overflow-x-auto bg-white rounded-xl border border-[#e9ecef]">
  <table className="w-full">
    {/* 表头 */
      <tr className="border-b border-[#e9ecef] bg-[#f8f9fb]">
        <th className="px-4 py-3 text-left text-xs font-semibold text-[#6c757d] uppercase tracking-wider">
          列名
        </th>
      </tr>
    </thead>
    {/* 表体 */
      <tr className="border-b border-[#f1f3f5] hover:bg-[#f8f9fb]/80
                    transition-colors duration-150">
        <td className="px-4 py-3 text-sm text-[#1a1a2e]">数据</td>
      </tr>
    </tbody>
  </table>
</div>
```

### 4.6 统计卡片 (Stat Card)
```tsx
// 小统计卡片
<div className="bg-white rounded-xl border border-[#e9ecef] shadow-sm p-5">
  <div className="text-xs text-[#6c757d] font-medium uppercase tracking-wider mb-2">
    标签
  </div>
  <div className="text-3xl font-bold text-[#1a1a2e] tabular-nums">
    1,234
  </div>
  {/* 可选：变化指示 */}
  <div className="mt-2 flex items-center text-xs text-emerald-600">
    <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" />
    </svg>
    +12.5%
  </div>
</div>

// 大统计卡片
<div className="bg-gradient-to-br from-white to-[#f8f9fb]
                rounded-xl border border-[#e9ecef] p-8
                shadow-md">
  <div className="flex items-baseline gap-4">
    <div className="text-6xl font-bold text-[#1a1a2e] tabular-nums">
      98.6
    </div>
    <div className="text-sm text-[#6c757d] uppercase tracking-wider">
      市场强度指数
    </div>
  </div>
</div>
```

### 4.7 等级徽章 (Grade Badge)
```tsx
// S+ 级 - 精致渐变
<span className="inline-flex items-center gap-1.5 px-3 py-1
                 bg-gradient-to-r from-amber-300 via-amber-500 to-amber-600
                 text-amber-100 rounded-md
                 font-bold text-sm
                 shadow-[0_0_15px_rgba(245,158,11,0.3)]">
  <span className="text-base">🔥</span>
  <span>S+</span>
</span>

// S 级
<span className="inline-flex items-center gap-1.5 px-3 py-1
                 bg-gradient-to-r from-orange-400 to-orange-600
                 text-orange-100 rounded-md
                 font-bold text-sm">
  <span className="text-base">⚡</span>
  <span>S</span>
</span>

// A+ 级
<span className="inline-flex items-center gap-1.5 px-3 py-1
                 bg-gradient-to-r from-yellow-400 to-yellow-600
                 text-yellow-100 rounded-md
                 font-bold text-sm">
  <span className="text-base">⭐</span>
  <span>A+</span>
</span>
```

---

## 5. 布局与间距

### 5.1 容器
```tsx
// 页面容器
<div className="max-w-7xl mx-auto px-6">
  {/* 内容 */}
</div>

// 网格系统
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {/* 卡片 */}
</div>

// 响应式网格
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
  {/* 自适应卡片 */}
</div>
```

### 5.2 分割线
```tsx
// 基础分割线
<div className="h-px bg-[#e9ecef]" />

// 强调分割线
<div className="h-px bg-gradient-to-r from-transparent via-[#dee2e6] to-transparent" />
```

---

## 6. 视觉细节

### 6.1 圆角
```css
--radius-sm:  0.5rem   /* 8px - 小元素 */
--radius:     0.75rem  /* 12px - 按钮、输入框 */
--radius-lg:  1rem     /* 16px - 卡片 */
--radius-xl:  1.25rem  /* 20px - 大卡片 */
```

**原则**：浅色主题使用稍大的圆角，营造柔和友好感。

### 6.2 阴影
```css
/* 微妙阴影 - 用于卡片 */
--shadow-sm:  0 1px 2px 0 rgba(0, 0, 0, 0.05);

/* 标准阴影 - 用于悬浮卡片 */
--shadow-md:  0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -1px rgba(0, 0, 0, 0.04);

/* 强调阴影 - 用于模态框 */
--shadow-lg:  0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);

/* 青色发光 - 用于强调元素 */
--glow-cyan:  0 0 20px rgba(6, 182, 212, 0.25);
```

### 6.3 模糊效果
```tsx
// 背景模糊 - 用于模态背景
<div className="backdrop-blur-sm bg-white/80" />

// 微妙模糊
<div className="backdrop-blur-xs" />
```

### 6.4 渐变
```tsx
// 背景渐变 - 微妙
<div className="bg-gradient-to-br from-[#f8f9fb] via-white to-[#f8f9fb]" />

// 边框渐变（微妙）
<div className="border border-[#e9ecef] hover:border-[#dee2e6]
              transition-colors duration-200" />
```

---

## 7. 动画与过渡

### 7.1 过渡时长
```css
--duration-fast:   150ms  /* 微交互 */
--duration-base:   200ms  /* 标准过渡 */
--duration-slow:   300ms  /* 复杂动画 */
```

### 7.2 缓动函数
```css
--ease-out: cubic-bezier(0, 0, 0.2, 1)      /* 标准输出 */
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1) /* 双向 */
```

### 7.3 动画示例
```tsx
// 淡入
className="animate-[fadeIn_0.3s_ease-out]"

// 滑入
className="animate-[slideUp_0.4s_ease-out]"

// 脉冲（用于强调）
className="animate-[pulse_2s_ease-in-out_infinite]"
```

### 7.4 关键帧定义
```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes shimmer {
  0% { background-position: -1000px 0; }
  100% { background-position: 1000px 0; }
}
```

---

## 8. 图标系统

### 8.1 图标库
- **Heroicons** (MIT License) - 主要图标库
- **Lucide Icons** (MIT License) - 补充图标

### 8.2 使用规范
```tsx
// Outline 风格 - 常规图标
import { ChevronDownIcon, XMarkIcon } from '@heroicons/react/24/outline'

// Solid 风格 - 仅用于强调状态
import { CheckIcon } from '@heroicons/react/24/solid'

// 使用示例
<ChevronDownIcon className="w-5 h-5 text-[#6c757d]" />
<XMarkIcon className="w-6 h-6 text-[#adb5bd] hover:text-[#1a1a2e]
                    cursor-pointer transition-colors" />
```

### 8.3 尺寸规范
```tsx
// 小图标
className="w-4 h-4"  // 16px

// 常规图标
className="w-5 h-5"  // 20px

// 中图标
className="w-6 h-6"  // 24px

// 大图标
className="w-8 h-8"  // 32px
```

---

## 9. 状态规范

### 9.1 加载状态
```tsx
// 加载动画
<div className="flex items-center justify-center py-12">
  <div className="relative w-10 h-10">
    <div className="absolute inset-0 rounded-full border-2 border-[#e9ecef]" />
    <div className="absolute inset-0 rounded-full border-2 border-transparent
                    border-t-cyan-500 animate-spin" />
  </div>
  <p className="ml-3 text-sm text-[#6c757d]">加载中...</p>
</div>

// 骨架屏
<div className="animate-pulse bg-[#e9ecef] rounded-xl h-20" />
```

### 9.2 空状态
```tsx
<div className="flex flex-col items-center justify-center py-16">
  <div className="text-5xl mb-4 opacity-50">📊</div>
  <p className="text-lg font-semibold text-[#1a1a2e] mb-2">暂无数据</p>
  <p className="text-sm text-[#6c757d]">请尝试调整筛选条件</p>
</div>
```

### 9.3 错误状态
```tsx
<div className="bg-red-50 border border-red-200 rounded-xl p-6">
  <div className="flex items-start">
    <ExclamationTriangleIcon className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
    <div className="ml-3">
      <p className="text-sm font-semibold text-red-700">操作失败</p>
      <p className="text-sm text-[#6c757d] mt-1">{error.message}</p>
    </div>
  </div>
</div>
```

---

## 10. 响应式设计

### 10.1 断点
```css
/* 移动优先 */
--breakpoint-sm:  640px   /* sm: */
--breakpoint-md:  768px   /* md: */
--breakpoint-lg:  1024px  /* lg: */
--breakpoint-xl:  1280px  /* xl: */
--breakpoint-2xl: 1536px  /* 2xl: */
```

### 10.2 响应式模式
```tsx
// 移动端垂直，桌面端水平
<div className="flex flex-col md:flex-row gap-4">

// 移动端隐藏
<div className="hidden lg:block">

// 响应式字体
<h1 className="text-2xl md:text-3xl lg:text-4xl">

// 响应式网格
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
```

---

## 11. 可访问性

### 11.1 焦点状态
```css
/* 所有可交互元素 */
*:focus-visible {
  outline: 2px solid #22d3ee;  /* cyan-400 */
  outline-offset: 2px;
}

/* 移除默认焦点 */
*:focus {
  outline: none;
}
```

### 11.2 对比度
- 正文文字与背景对比度 ≥ 7:1 (AAA)
- 大文字与背景对比度 ≥ 4.5:1 (AA)

### 11.3 触摸目标
- 最小可点击区域：44×44px
- 按钮内边距至少 12px

### 11.4 ARIA 标签
```tsx
// 图标按钮
<button aria-label="关闭">
  <XMarkIcon className="w-6 h-6" />
</button>

// 加载状态
<div role="status" aria-live="polite">
  <span className="sr-only">加载中...</span>
  {/* 加载动画 */}
</div>
```

---

## 12. 性能优化

### 12.1 CSS 优化
```tsx
// 使用 will-change 优化动画
<div className="will-change-transform" />

// 使用 CSS transforms 而非 position
<div className="hover:scale-105 transition-transform" />

// 使用 contain 隔离重绘
<div className="contain-layout" />
```

### 12.2 渲染优化
```tsx
// 虚拟滚动
import { useVirtualizer } from '@tanstack/react-virtual'

// 图片懒加载
<img loading="lazy" src="..." alt="..." />

// 代码分割
const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <Skeleton />
})
```

---

## 13. 设计原则

### ✅ 遵循原则
- **精确**：每个像素都有目的
- **克制**：去除不必要装饰
- **高效**：信息优先，减少认知负担
- **一致**：统一的设计语言
- **犀利**：锐利边缘，明确分割

### ❌ 避免事项
- Inter 字体（已过度使用）
- 大圆角（>12px）
- 紫色渐变（AI 生成刻板印象）
- 过度装饰和花哨效果
- 模糊不清的层次
- 无目的的动画

---

## 14. 附录：快速参考

### 等级色彩速查

| 等级 | 分数 | 渐变 | 文字 | 图标 |
|------|------|------|------|------|
| S+ | 90-100 | amber-300 → amber-600 | amber-100 | 🔥 |
| S | 80-89 | orange-400 → orange-600 | orange-200 | ⚡ |
| A+ | 70-79 | yellow-400 → yellow-600 | yellow-200 | ⭐ |
| A | 60-69 | lime-400 → lime-600 | lime-200 | 📈 |
| B+ | 50-59 | emerald-400 → emerald-600 | emerald-300 | ✓ |
| B | 40-49 | cyan-400 → cyan-600 | cyan-300 | ○ |
| C | 30-39 | violet-400 → violet-600 | violet-300 | ↓ |
| D | 0-29 | gray-400 → gray-500 | gray-300 | ⚠ |

### 常用组件代码片段

```tsx
// 页面容器
<div className="min-h-screen bg-[#f8f9fb]">
  <div className="max-w-7xl mx-auto px-6 py-8">
    {/* 内容 */}
  </div>
</div>

// 卡片网格
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {/* 卡片 */}
</div>

// 主按钮
<button className="px-5 py-2.5 bg-gradient-to-r from-cyan-400 to-cyan-500
                   hover:from-cyan-500 hover:to-cyan-600 text-white
                   font-medium rounded-lg transition-all duration-200">
  按钮
</button>
```

---

## 15. 更新日志

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2025-12-31 | 初始版本（浅色主题） |
| 2.0.0 | 2025-12-31 | 重新设计为精密仪器美学（深色主题） |
| 3.0.0 | 2025-12-31 | 晨曦实验室美学（浅色主题） |

---

**设计系统维护者**: Sector Strength Design Team
**最后审查**: 2025-12-31
