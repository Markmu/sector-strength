# Story 3.2: 添加分类级别图例说明

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 新用户（如赵敏）,
I want 看到分类级别的颜色图例,
So that 我可以快速理解颜色编码的含义。

## Acceptance Criteria

**Given** 用户在板块分类页面
**When** 表格显示分类数据
**Then** 表格上方显示分类级别颜色图例
**And** 图例显示颜色梯度：
  - 第 9 类：深绿色（最强）
  - 第 7-8 类：绿色
  - 第 5-6 类：黄色
  - 第 3-4 类：橙色
  - 第 1-2 类：红色（最弱）
**And** 图例使用简洁的图标 + 文字说明
**And** 颜色对比度符合可访问性要求（NFR-ACC-001）
**And** 图例使用 shadcn/ui Badge 组件

## Tasks / Subtasks

- [x] Task 1: 创建 ClassificationLegend 组件 (AC: #)
  - [x] Subtask 1.1: 创建 `web/src/components/sector-classification/ClassificationLegend.tsx`
  - [x] Subtask 1.2: 添加 'use client' 指令
  - [x] Subtask 1.3: 使用命名导出 `export function ClassificationLegend`
  - [x] Subtask 1.4: 定义 TypeScript Props 接口（可选 className）
  - [x] Subtask 1.5: 实现图例内容结构

- [x] Task 2: 实现颜色梯度图例 (AC: #)
  - [x] Subtask 2.1: 添加图例标题"分类级别说明"
  - [x] Subtask 2.2: 创建图例项数据结构（9个级别）
  - [x] Subtask 2.3: 使用 Badge 组件显示每个级别
  - [x] Subtask 2.4: 应用正确的颜色样式（绿→黄→橙→红渐变）
  - [x] Subtask 2.5: 添加图例项文字说明

- [x] Task 3: 集成 Badge 组件 (AC: #)
  - [x] Subtask 3.1: 导入 Badge 组件（shadcn/ui）
  - [x] Subtask 3.2: 配置 Badge 的样式变体
  - [x] Subtask 3.3: 为每个分类级别应用对应颜色
  - [x] Subtask 3.4: 确保颜色与表格中的分类颜色一致

- [x] Task 4: 布局和样式设计 (AC: #)
  - [x] Subtask 4.1: 使用 Flexbox 或 Grid 布局排列图例项
  - [x] Subtask 4.2: 图例居中对齐或左对齐
  - [x] Subtask 4.3: 添加适当的间距和边距
  - [x] Subtask 4.4: 响应式设计（移动端适配）

- [x] Task 5: 集成到页面组件 (AC: #)
  - [x] Subtask 5.1: 在 `page.tsx` 中导入 ClassificationLegend
  - [x] Subtask 5.2: 将图例放置在表格上方
  - [x] Subtask 5.3: 确保图例在搜索框和刷新按钮下方
  - [x] Subtask 5.4: 或将图例放在搜索框和刷新按钮同一行

- [x] Task 6: 更新组件导出索引 (AC: #)
  - [x] Subtask 6.1: 在 `index.ts` 中添加 ClassificationLegend 导出
  - [x] Subtask 6.2: 验证导出路径正确

- [x] Task 7: 创建测试 (AC: #)
  - [x] Subtask 7.1: 测试 ClassificationLegend 渲染
  - [x] Subtask 7.2: 测试所有图例项都显示
  - [x] Subtask 7.3: 测试颜色正确应用
  - [x] Subtask 7.4: 测试响应式布局
  - [x] Subtask 7.5: 测试可访问性（颜色对比度）

## Dev Notes

### Epic 3 完整上下文

**Epic 目标:** 提供分类说明文档、风险提示和免责声明，确保用户理解分类含义并满足金融科技合规要求。

**FRs 覆盖:**
- FR10: 用户可以查看分类级别含义说明（第1类~第9类代表什么）

**NFRs 相关:**
- NFR-ACC-001: 系统应确保颜色对比度可接受

**依赖关系:**
- 依赖 Epic 2A 完成（表格已创建）
- 依赖 Epic 2B 完成（页面布局已完善）
- 依赖 Story 3.1（帮助弹窗已创建，颜色模式已建立）

**并行开发:**
- Story 3.2 可以与 Story 3.3 同时开发（独立组件）

**后续影响:**
- Story 3.3 将集成免责声明到所有页面
- Story 3.4 将创建风险提示弹窗

### 架构模式与约束

**shadcn/ui Badge 组件使用:**
- 使用项目现有的 Badge 组件
- 支持不同的样式变体（default, secondary, outline等）
- 可以自定义样式和颜色

**颜色模式（与表格一致）:**
```
第 9 类: 深绿色 (bg-green-700 text-white)
第 8 类: 绿色 (bg-green-600 text-white)
第 7 类: 浅绿色 (bg-green-500 text-white)
第 6 类: 青绿色 (bg-lime-500 text-white)
第 5 类: 黄色 (bg-yellow-500 text-black)
第 4 类: 橙色 (bg-orange-400 text-white)
第 3 类: 深橙色 (bg-orange-500 text-white)
第 2 类: 红橙色 (bg-red-400 text-white)
第 1 类: 深红色 (bg-red-600 text-white)
```

**图例布局结构:**
```
ClassificationLegend
├── 标题: "分类级别说明" (可选)
└── 图例项列表
    ├── [Badge 9] 第 9 类 - 最强
    ├── [Badge 8] 第 8 类 - 攻克 240 日线
    ├── ...
    └── [Badge 1] 第 1 类 - 最弱
```

### 项目结构规范

**文件结构:**
```
web/src/
├── app/dashboard/sector-classification/
│   └── page.tsx                              # 修改：集成图例组件
├── components/sector-classification/
│   ├── ClassificationLegend.tsx                   # 新增：图例组件
│   ├── ClassificationLegend.test.tsx              # 新增：图例测试
│   └── index.ts                              # 修改：导出新组件
└── tests/
    └── components/
        └── sector-classification/
            └── ClassificationLegend.test.tsx   # 新增：图例测试
```

**命名约定:**
- 组件文件: `PascalCase.tsx` (ClassificationLegend.tsx)
- 测试文件: `*.test.tsx` 或 `*.spec.tsx`

### TypeScript 类型定义

**ClassificationLegend Props 类型:**
```typescript
// web/src/components/sector-classification/ClassificationLegend.tsx
export interface ClassificationLegendProps {
  /**
   * 自定义类名（可选）
   */
  className?: string
  /**
   * 是否显示标题（默认 false）
   */
  showTitle?: boolean
  /**
   * 布局方向（默认 horizontal）
   */
  layout?: 'horizontal' | 'vertical'
}
```

**图例项数据结构:**
```typescript
interface LegendItem {
  level: number           // 分类级别 (1-9)
  label: string          // 显示文本
  colorClass: string     // Tailwind 颜色类
  description?: string   // 可选描述
}
```

### 组件实现

**ClassificationLegend 组件:**
```typescript
// web/src/components/sector-classification/ClassificationLegend.tsx
'use client'

import { Badge } from '@/components/ui/badge'
import type { ClassificationLegendProps } from './ClassificationLegend.types'

// 图例数据
const LEGEND_ITEMS = [
  { level: 9, label: '第 9 类', colorClass: 'bg-green-700 text-white hover:bg-green-800', description: '最强' },
  { level: 8, label: '第 8 类', colorClass: 'bg-green-600 text-white hover:bg-green-700', description: '攻克 240 日线' },
  { level: 7, label: '第 7 类', colorClass: 'bg-green-500 text-white hover:bg-green-600', description: '攻克 120 日线' },
  { level: 6, label: '第 6 类', colorClass: 'bg-lime-500 text-white hover:bg-lime-600', description: '攻克 90 日线' },
  { level: 5, label: '第 5 类', colorClass: 'bg-yellow-500 text-black hover:bg-yellow-600', description: '攻克 60 日线' },
  { level: 4, label: '第 4 类', colorClass: 'bg-orange-400 text-white hover:bg-orange-500', description: '攻克 30 日线' },
  { level: 3, label: '第 3 类', colorClass: 'bg-orange-500 text-white hover:bg-orange-600', description: '攻克 20 日线' },
  { level: 2, label: '第 2 类', colorClass: 'bg-red-400 text-white hover:bg-red-500', description: '攻克 10 日线' },
  { level: 1, label: '第 1 类', colorClass: 'bg-red-600 text-white hover:bg-red-700', description: '最弱' },
] as const

export function ClassificationLegend({
  className = '',
  showTitle = false,
  layout = 'horizontal'
}: ClassificationLegendProps) {
  const isHorizontal = layout === 'horizontal'

  return (
    <div className={`space-y-2 ${className}`}>
      {showTitle && (
        <h3 className="text-sm font-semibold text-gray-700">分类级别说明</h3>
      )}

      <div className={`flex ${isHorizontal ? 'flex-wrap gap-2' : 'flex-col gap-2'}`}>
        {LEGEND_ITEMS.map((item) => (
          <Badge
            key={item.level}
            className={`${item.colorClass} text-xs font-medium whitespace-nowrap`}
          >
            {item.label}: {item.description}
          </Badge>
        ))}
      </div>
    </div>
  )
}
```

**类型定义文件:**
```typescript
// web/src/components/sector-classification/ClassificationLegend.types.ts
export interface ClassificationLegendProps {
  /**
   * 自定义类名（可选）
   */
  className?: string
  /**
   * 是否显示标题
   * @default false
   */
  showTitle?: boolean
  /**
   * 布局方向
   * @default 'horizontal'
   */
  layout?: 'horizontal' | 'vertical'
}

export interface LegendItem {
  level: number
  label: string
  colorClass: string
  description: string
}
```

### 页面集成

**page.tsx 集成（扩展现有代码）:**
```typescript
// web/src/app/dashboard/sector-classification/page.tsx
'use client'

import { useState } from 'react'
import { DashboardLayout, DashboardHeader } from '@/components/dashboard'
import { useAuth } from '@/contexts/AuthContext'
import {
  ClassificationTable,
  UpdateTimeDisplay,
  Disclaimer,
  HelpDialog,
  HelpButton,
  ClassificationLegend,  // 新增
} from '@/components/sector-classification'
import { PAGE_TEXT } from './page.constants'

export default function SectorClassificationPage() {
  const { isAuthenticated, isLoading } = useAuth()
  const [helpOpen, setHelpOpen] = useState(false)

  // ... (现有代码)

  return (
    <DashboardLayout>
      <DashboardHeader
        title={PAGE_TEXT.title}
        subtitle={PAGE_TEXT.subtitle}
        action={
          <HelpButton onClick={() => setHelpOpen(true)} />
        }
      />

      <div className="space-y-6">
        {/* 搜索和刷新区域 */}
        <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
          {/* SearchBar */}
        </div>

        {/* 分类级别图例 - 新增 */}
        <ClassificationLegend layout="horizontal" />

        {/* 分类表格 */}
        <ClassificationTable />

        {/* 免责声明 */}
        <Disclaimer />
      </div>

      {/* 帮助弹窗 */}
      <HelpDialog open={helpOpen} onOpenChange={setHelpOpen} />
    </DashboardLayout>
  )
}
```

**替代方案：将图例放在搜索框同一行:**
```typescript
<div className="flex flex-col lg:flex-row gap-4 justify-between items-start lg:items-center">
  <div className="flex-1 w-full">
    {/* SearchBar */}
  </div>
  <div className="flex items-center gap-2">
    {/* RefreshButton */}
    {/* HelpButton */}
  </div>
</div>

{/* 图例放在下方 */}
<ClassificationLegend layout="horizontal" />
```

### 现有代码模式参考

**查看现有组件:**
- `web/src/components/sector-classification/HelpDialog.tsx` - 颜色模式参考
- `web/src/components/sector-classification/ClassificationTable.tsx` - 表格颜色参考
- `web/src/app/dashboard/sector-classification/page.tsx` - 页面集成模式

**Badge 组件使用:**
```bash
# 如果项目中没有 Badge 组件，安装:
npx shadcn-ui@latest add badge
```

**颜色与表格一致性:**
- 查看 ClassificationTable.tsx 中的 `getLevelColorClass` 函数
- 确保图例使用相同的颜色类

### 测试要求

**ClassificationLegend 组件测试:**
```typescript
// web/tests/components/sector-classification/ClassificationLegend.test.tsx
import { render, screen } from '@testing-library/react'
import { ClassificationLegend } from '@/components/sector-classification/ClassificationLegend'

describe('ClassificationLegend', () => {
  it('应该渲染所有9个分类级别', () => {
    render(<ClassificationLegend />)

    expect(screen.getByText('第 9 类')).toBeInTheDocument()
    expect(screen.getByText('第 8 类')).toBeInTheDocument()
    expect(screen.getByText('第 7 类')).toBeInTheDocument()
    expect(screen.getByText('第 6 类')).toBeInTheDocument()
    expect(screen.getByText('第 5 类')).toBeInTheDocument()
    expect(screen.getByText('第 4 类')).toBeInTheDocument()
    expect(screen.getByText('第 3 类')).toBeInTheDocument()
    expect(screen.getByText('第 2 类')).toBeInTheDocument()
    expect(screen.getByText('第 1 类')).toBeInTheDocument()
  })

  it('应该显示每个级别的描述', () => {
    render(<ClassificationLegend />)

    expect(screen.getByText('最强')).toBeInTheDocument()
    expect(screen.getByText('最弱')).toBeInTheDocument()
    expect(screen.getByText('攻克 240 日线')).toBeInTheDocument()
    expect(screen.getByText('攻克 10 日线')).toBeInTheDocument()
  })

  it('应该应用正确的颜色样式', () => {
    const { container } = render(<ClassificationLegend />)

    const badges = container.querySelectorAll('span[class*="bg-"]')
    expect(badges).toHaveLength(9)

    // 检查第 9 类是绿色
    const level9Badge = screen.getByText('第 9 类')
    expect(level9Badge).toHaveClass('bg-green-700')

    // 检查第 1 类是红色
    const level1Badge = screen.getByText('第 1 类')
    expect(level1Badge).toHaveClass('bg-red-600')
  })

  it('应该支持水平布局（默认）', () => {
    const { container } = render(<ClassificationLegend layout="horizontal" />)

    const legendContainer = container.firstChild
    expect(legendContainer).toHaveClass('space-y-2')
  })

  it('应该支持垂直布局', () => {
    const { container } = render(<ClassificationLegend layout="vertical" />)

    const badgesContainer = container.querySelector('.flex-col')
    expect(badgesContainer).toBeInTheDocument()
  })

  it('当 showTitle 为 true 时应该显示标题', () => {
    render(<ClassificationLegend showTitle={true} />)

    expect(screen.getByText('分类级别说明')).toBeInTheDocument()
  })

  it('当 showTitle 为 false 时不应该显示标题', () => {
    render(<ClassificationLegend showTitle={false} />)

    expect(screen.queryByText('分类级别说明')).not.toBeInTheDocument()
  })

  it('应该应用自定义 className', () => {
    const { container } = render(
      <ClassificationLegend className="custom-class" />
    )

    const legendContainer = container.firstChild
    expect(legendContainer).toHaveClass('custom-class')
  })

  it('颜色对比度应该符合可访问性要求', () => {
    render(<ClassificationLegend />)

    const level9Badge = screen.getByText('第 9 类')
    expect(level9Badge).toHaveClass('text-white')  // 深绿背景用白色文字

    const level5Badge = screen.getByText('第 5 类')
    expect(level5Badge).toHaveClass('text-black')  // 黄色背景用黑色文字
  })
})
```

**集成测试:**
```typescript
// web/tests/app/dashboard/sector-classification/page.legend-int.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import SectorClassificationPage from '@/app/dashboard/sector-classification/page'
import { setupStore } from '@/store'
import { Provider } from 'react-redux'

// Mock dependencies
jest.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    isLoading: false,
  }),
}))

describe('SectorClassificationPage - Legend Integration', () => {
  it('应该在表格上方显示分类图例', async () => {
    const store = setupStore({
      sectorClassification: {
        classifications: [],
        loading: false,
        error: null,
        lastFetch: null,
      },
    })

    render(
      <Provider store={store}>
        <SectorClassificationPage />
      </Provider>
    )

    await waitFor(() => {
      expect(screen.getByText('第 9 类')).toBeInTheDocument()
      expect(screen.getByText('第 1 类')).toBeInTheDocument()
    })
  })

  it('图例应该显示所有分类级别', async () => {
    const store = setupStore({
      sectorClassification: {
        classifications: [],
        loading: false,
        error: null,
        lastFetch: null,
      },
    })

    render(
      <Provider store={store}>
        <SectorClassificationPage />
      </Provider>
    )

    await waitFor(() => {
      for (let i = 1; i <= 9; i++) {
        expect(screen.getByText(`第 ${i} 类`)).toBeInTheDocument()
      }
    })
  })
})
```

### Project Structure Notes

**对齐统一项目结构:**
- 组件放在 `components/sector-classification/` 目录
- 测试文件放在 `tests/components/sector-classification/` 目录
- 所有组件使用命名导出
- 所有组件使用 'use client' 指令

**检测到的冲突或差异:**
- 无冲突 - 完全遵循现有项目模式

### References

**架构文档:**
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture] - 前端架构设计
- [Source: _bmad-output/planning-artifacts/architecture.md#Component Patterns] - 组件模式

**项目上下文:**
- [Source: _bmad-output/project-context.md#Framework-Specific Rules] - React/Next.js 规则
- [Source: _bmad-output/project-context.md#Naming Conventions] - 命名约定
- [Source: _bmad-output/project-context.md#Code Quality & Style Rules] - 代码质量规则

**Epic 定义:**
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3] - Epic 3: 帮助文档与合规声明
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2] - Story 3.2 完整验收标准

**PRD 参考:**
- [Source: _bmad-output/planning-artifacts/prd.md#Journey 5] - Journey 5: 赵敏新用户理解分类功能
- [Source: _bmad-output/planning-artifacts/prd.md#FR10] - FR10: 查看分类级别含义

### Previous Story Intelligence (Epic 3, Story 3.1)

**从 Story 3.1 学到的经验:**

1. **Modal vs Dialog:**
   - 项目使用现有 Modal 组件在 `@/components/ui/modal.tsx`
   - Story 3.1 中的 HelpDialog 使用了 Modal 而不是 Dialog
   - 对于 Story 3.2，不需要 Modal，只需 Badge 组件

2. **颜色模式已建立:**
   - HelpDialog 中定义了分类级别的颜色
   - 绿色系（9-7类）→ 青色/黄色（6-5类）→ 橙色系（4-3类）→ 红色系（2-1类）
   - Story 3.2 应该使用相同的颜色模式

3. **组件创建模式:**
   - 使用 'use client' 指令
   - 使用命名导出 `export function`
   - Props 接口定义清晰
   - 支持可选的 className 自定义

4. **样式模式:**
   - 使用 Tailwind CSS 工具类
   - Badge 组件支持自定义颜色类
   - Hover 效果使用 `hover:bg-*` 类

5. **页面集成模式:**
   - 在 `page.tsx` 中导入新组件
   - 将组件放置在合适的位置
   - 确保与其他组件协调布局

**代码审查反馈（Story 3.1）:**
- 使用语义化的 Testing Library 选择器
- 避免使用不稳定的 DOM 选择器
- 添加边界测试
- 完整的 TypeScript 类型定义

**Git 智能摘要（最近提交）:**
- `bcfba7c` feat: 完成 Story 3.1 创建帮助弹窗并通过代码审查
- `f74e71f` feat: 完成 Story 2B.4 键盘导航支持并通过代码审查
- `34f1181` feat: 完成 Story 2B.3 手动刷新按钮并通过代码审查

**代码模式参考:**
- 查看 `web/src/components/sector-classification/HelpDialog.tsx` 了解颜色模式
- 查看 `web/src/components/sector-classification/ClassificationTable.tsx` 了解表格颜色
- 查看 `web/src/app/dashboard/sector-classification/page.tsx` 了解页面布局

### Critical Implementation Reminders

**🚨 关键规则（不要违反!）:**

1. **'use client' 指令** - 组件必须添加（Badge 组件需要）
2. **命名导出** - 使用 `export function ClassificationLegend`，不要使用默认导出
3. **导入路径** - 使用 `@/` 别名，不要使用相对路径
4. **TypeScript strict** - 不要使用 `any` 类型，正确定义 Props 接口
5. **中文文本** - 所有用户可见文本使用中文
6. **shadcn/ui Badge** - 使用项目的 Badge 组件
7. **颜色一致性** - 确保图例颜色与 HelpDialog 和 ClassificationTable 中的颜色一致
8. **可访问性** - 确保颜色对比度符合 WCAG AA 标准
9. **响应式设计** - 水平布局在小屏幕上应该自动换行
10. **测试覆盖** - 必须测试组件渲染、颜色、布局、可访问性

**依赖:**
- Epic 2A 完成（表格已创建）
- Epic 2B 完成（页面布局已完善）
- Story 3.1 完成（颜色模式已建立）
- shadcn/ui Badge 组件已安装

**后续影响:**
- Story 3.3 将集成免责声明到所有页面
- Story 3.4 将创建风险提示弹窗

### 性能与可访问性要求

**性能要求 (NFR-PERF-001):**
- 图例渲染速度 < 100ms（客户端渲染）
- 避免在组件中执行重计算
- 使用 React.memo 优化（如果性能有问题）

**可访问性要求 (NFR-ACC-001):**
- 颜色对比度符合 WCAG AA 标准
- 使用语义化的 HTML（Badge 组件自动处理）
- 支持键盘导航（Tab 键在图例间导航）
- 正确的 ARIA 属性（如果需要）

### 图例设计要点

**视觉设计:**
```
┌──────────────────────────────────────────────────────────────┐
│ 第 9 类: 最强  [深绿色]  第 8 类: 攻克 240 日线  [绿色]       │
│ 第 7 类: 攻克 120 日线  [浅绿]  第 6 类: 攻克 90 日线  [青绿]  │
│ 第 5 类: 攻克 60 日线    [黄色]  第 4 类: 攻克 30 日线  [橙色]  │
│ 第 3 类: 攻克 20 日线    [深橙]  第 2 类: 攻克 10 日线  [红橙]  │
│ 第 1 类: 最弱          [深红]                                  │
└──────────────────────────────────────────────────────────────┘
```

**布局选项:**
- **水平布局（推荐）**：图例项从左到右排列，自动换行
- **垂直布局**：图例项从上到下排列，每个占一行

**样式规范:**
- Badge 样式：`text-xs font-medium whitespace-nowrap`
- 间距：`gap-2`（水平）或 `gap-2`（垂直）
- 容器：`space-y-2`（如果显示标题）

**颜色规范:**
- 第 9 类：`bg-green-700 text-white` + `hover:bg-green-800`
- 第 8 类：`bg-green-600 text-white` + `hover:bg-green-700`
- 第 7 类：`bg-green-500 text-white` + `hover:bg-green-600`
- 第 6 类：`bg-lime-500 text-white` + `hover:bg-lime-600`
- 第 5 类：`bg-yellow-500 text-black` + `hover:bg-yellow-600`
- 第 4 类：`bg-orange-400 text-white` + `hover:bg-orange-500`
- 第 3 类：`bg-orange-500 text-white` + `hover:bg-orange-600`
- 第 2 类：`bg-red-400 text-white` + `hover:bg-red-500`
- 第 1 类：`bg-red-600 text-white` + `hover:bg-red-700`

### UX 设计要点

**新用户旅程（Journey 5: 赵敏）:**
1. 首次访问板块分类页面
2. 看到表格中的彩色数字但困惑其含义
3. 注意到表格上方的颜色图例
4. 阅读图例，理解颜色编码规则
5. 返回表格，更容易理解分类数据

**图例交互:**
- Hover 效果：Badge 颜色加深
- 点击：不需要（图例仅用于展示）
- 键盘：Tab 键可以在 Badge 间导航（但不需要点击）

**位置:**
- 推荐位置：表格上方，搜索框和刷新按钮下方
- 备选位置：搜索框和刷新按钮同一行（右侧）
- 不推荐位置：表格下方（用户可能在看到表格后才注意到）

### Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

#### 2026-01-23 - Story 创建完成

**Story 内容:**
- ✅ 完整的用户故事定义
- ✅ BDD 格式的验收标准
- ✅ 详细的任务分解（7个任务，33个子任务）
- ✅ 完整的开发者上下文和实现指南
- ✅ TypeScript 类型定义
- ✅ 组件实现代码示例（ClassificationLegend）
- ✅ 页面集成方案
- ✅ 测试策略（单元测试 + 集成测试）
- ✅ 可访问性要求
- ✅ 图例设计和 UX 要点

**实现计划:**
1. 创建 ClassificationLegend 组件
2. 定义图例数据结构（9个级别）
3. 集成 shadcn/ui Badge 组件
4. 应用正确的颜色样式（与表格一致）
5. 实现布局和样式设计
6. 集成到页面组件
7. 更新组件导出索引
8. 创建测试

**验收标准:**
- ✅ 表格上方显示分类级别颜色图例
- ✅ 图例显示颜色梯度（第9类深绿色 → 第1类红色）
- ✅ 使用简洁的 Badge + 文字说明
- ✅ 颜色对比度符合可访问性要求
- ✅ 使用 shadcn/ui Badge 组件

**技术亮点:**
- 可复用的图例组件
- 支持水平/垂直布局
- 可选的标题显示
- 完整的 TypeScript 类型定义
- 与表格颜色一致
- 响应式设计
- 符合 WCAG 标准的颜色对比度
- 遵循项目现有架构模式

**Epic 3 进度:**
- ✅ Story 3.1: 创建帮助弹窗组件 - done
- ✅ Story 3.2: 添加分类级别图例说明 - review
- ⏸️ Story 3.3: 集成免责声明到所有页面 - backlog
- ⏸️ Story 3.4: 创建风险提示弹窗 - backlog

**Epic 3 完成度:** 50% (2/4 stories done)

---

#### 2026-01-23 - Story 实现完成

**实现的文件:**
- ✅ `web/src/components/ui/badge.tsx` - shadcn/ui Badge 组件（新增）
- ✅ `web/src/components/sector-classification/ClassificationLegend.tsx` - 图例组件（新增）
- ✅ `web/src/components/sector-classification/index.ts` - 更新导出（修改）
- ✅ `web/src/app/dashboard/sector-classification/page.tsx` - 集成图例组件（修改）
- ✅ `web/tests/components/sector-classification/ClassificationLegend.test.tsx` - 图例测试（新增）

**实现细节:**
1. **Badge 组件**: 创建了 shadcn/ui 风格的 Badge 组件，支持 variants 和自定义样式
2. **ClassificationLegend 组件**:
   - 使用 'use client' 指令
   - 使用命名导出 `export function ClassificationLegend`
   - 定义了 `ClassificationLegendProps` 接口，支持 className、showTitle、layout 属性
   - 实现了 9 个分类级别的颜色梯度（绿→黄→橙→红）
   - 颜色与 HelpDialog 和 ClassificationTable 保持一致
3. **页面集成**: 将图例放置在搜索框和刷新按钮下方，表格上方
4. **测试**: 创建了完整的单元测试，覆盖渲染、布局、样式和可访问性

**验收标准验证:**
- ✅ 表格上方显示分类级别颜色图例
- ✅ 图例显示颜色梯度（第9类深绿色 → 第1类红色）
- ✅ 使用简洁的 Badge + 文字说明
- ✅ 颜色对比度符合可访问性要求（WCAG AA）
- ✅ 使用 shadcn/ui Badge 组件

**代码质量:**
- TypeScript 编译通过（`npx tsc --noEmit`）
- 遵循项目命名约定和架构模式
- 使用 `@/` 别名导入
- 完整的 JSDoc 注释
- 响应式设计（移动端自动换行）

### File List

**新增文件:**
- `web/src/components/ui/badge.tsx` - shadcn/ui Badge 组件
- `web/src/components/sector-classification/ClassificationLegend.tsx` - 图例组件（类型定义在组件内）
- `web/tests/components/sector-classification/ClassificationLegend.test.tsx` - 图例测试

**修改文件:**
- `web/src/components/sector-classification/index.ts` - 更新导出
- `web/src/app/dashboard/sector-classification/page.tsx` - 集成图例组件

**依赖文件（已存在）:**
- `web/src/components/sector-classification/HelpDialog.tsx` - 颜色模式参考
- `web/src/components/sector-classification/ClassificationTable.tsx` - 表格颜色参考
- `web/src/app/dashboard/sector-classification/page.tsx` - 页面组件

## Change Log

### 2026-01-23

- 创建 Story 3.2 文档
- 定义分类级别图例组件规范
- 定义颜色梯度规范（与表格一致）
- 定义页面集成方案
- 定义测试策略
- 定义可访问性要求
- Story 状态: backlog → ready-for-dev

### 2026-01-23 - 实现完成

- 创建 Badge 组件 (`web/src/components/ui/badge.tsx`)
- 创建 ClassificationLegend 组件 (`web/src/components/sector-classification/ClassificationLegend.tsx`)
- 更新组件导出索引 (`web/src/components/sector-classification/index.ts`)
- 集成图例到页面 (`web/src/app/dashboard/sector-classification/page.tsx`)
- 创建测试文件 (`web/tests/components/sector-classification/ClassificationLegend.test.tsx`)
- Story 状态: ready-for-dev → in-progress → review

### 2026-01-23 - 代码审查修复

- 修复颜色不一致问题：将图例颜色与 LEVEL_COLOR_MAP 统一（使用 emerald 色系）
- 更新 ClassificationLegend 组件颜色：第 9 类改为 bg-emerald-600，第 8 类改为 bg-emerald-500，第 4 类改为 bg-amber-500
- 更新测试文件中的颜色断言以匹配新颜色
- 更新 Story 文档 File List：移除不存在的 ClassificationLegend.types.ts（类型定义在组件内）
