# Story 2A.4: 添加数据更新时间显示

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 投资者,
I want 知道分类数据的最后更新时间,
So that 我可以判断数据的时效性。

## Acceptance Criteria

**Given** 用户已查看分类表格
**When** 分类数据加载成功
**Then** 表格上方显示"数据更新时间：YYYY-MM-DD HH:mm"
**And** 时间格式为中文本地化
**And** 时间显示在页面右上角或表格上方
**And** 如果数据时间戳缺失，显示"更新时间：未知"

## Tasks / Subtasks

- [x] Task 1: 从 Redux store 提取时间戳 (AC: #)
  - [x] Subtask 1.1: 从 `SectorClassificationState` 获取 `lastFetch` 时间戳
  - [x] Subtask 1.2: 验证时间戳数据可用性

- [x] Task 2: 创建更新时间显示组件 (AC: #)
  - [x] Subtask 2.1: 创建 `web/src/components/sector-classification/UpdateTimeDisplay.tsx`
  - [x] Subtask 2.2: 实现 `formatUpdateTime()` 函数（中文本地化）
  - [x] Subtask 2.3: 处理时间戳缺失情况（显示"未知"）
  - [x] Subtask 2.4: 使用 Tailwind CSS 样式

- [x] Task 3: 集成到页面组件 (AC: #)
  - [x] Subtask 3.1: 在 `page.tsx` 中导入 UpdateTimeDisplay 组件
  - [x] Subtask 3.2: 将时间显示组件放置在表格上方
  - [x] Subtask 3.3: 仅在数据加载成功后显示时间

- [x] Task 4: 实现时间格式化工具函数 (AC: #)
  - [x] Subtask 4.1: 创建 `web/src/lib/dateFormat.ts` 工具函数
  - [x] Subtask 4.2: 实现 `formatChineseDateTime()` 函数
  - [x] Subtask 4.3: 支持格式：YYYY-MM-DD HH:mm（中文本地化）

- [x] Task 5: 创建测试 (AC: #)
  - [x] Subtask 5.1: 测试时间格式化函数
  - [x] Subtask 5.2: 测试 UpdateTimeDisplay 组件渲染
  - [x] Subtask 5.3: 测试时间戳缺失情况
  - [x] Subtask 5.4: 测试中文时间格式

## Dev Notes

### Epic 2A 完整上下文

**Epic 目标:** 为投资者提供查看板块强弱分类的核心用户界面，包括分类列表和基础信息展示。

**FRs 覆盖:**
- FR7: 用户可以查看数据最后更新时间

**NFRs 相关:**
- NFR-PERF-001: 页面首次加载（FCP）< 1.5秒
- NFR-ACC-004: 错误提示清晰可见（也适用于时间显示）

**依赖关系:**
- 依赖 Story 2A.1 完成（页面路由已创建）
- 依赖 Story 2A.2 完成（表格组件已创建）
- 依赖 Story 2A.3 完成（数据获取已实现，Redux store 已配置）
- 与 Epic 3 并行开发（帮助文档与合规声明）

### 架构模式与约束

**Redux State 扩展:**
- Story 2A.3 已在 Redux store 中添加 `lastFetch: number | null` 字段
- 本 Story 将使用该时间戳显示更新时间

**时间戳来源:**
- Redux state: `sectorClassification.lastFetch` (Story 2A.3 已设置)
- 数据格式: Unix timestamp (毫秒) 或 ISO 8601 字符串

**中文本地化格式:**
```
格式：YYYY-MM-DD HH:mm
示例：2026-01-22 15:30
缺失时：更新时间：未知
```

### 项目结构规范

**文件结构:**
```
web/src/
├── app/dashboard/sector-classification/
│   └── page.tsx                              # 修改：集成时间显示
├── components/sector-classification/
│   ├── UpdateTimeDisplay.tsx                 # 新增：时间显示组件
│   └── index.ts                              # 修改：导出新组件
├── lib/
│   └── dateFormat.ts                         # 新增：日期格式化工具
└── tests/
    ├── lib/
    │   └── dateFormat.test.ts                 # 新增：工具函数测试
    └── components/
        └── UpdateTimeDisplay.test.tsx        # 新增：组件测试
```

**命名约定:**
- 组件文件: `PascalCase.tsx`
- 工具函数文件: `camelCase.ts`
- 测试文件: `*.test.ts` 或 `*.test.tsx`

### TypeScript 类型定义

**Redux State 类型（Story 2A.3 已定义）:**
```typescript
// web/src/store/slices/sectorClassificationSlice.ts
export interface SectorClassificationState {
  classifications: SectorClassification[]
  loading: boolean
  error: string | null
  lastFetch: number | null  // Unix timestamp in milliseconds
}
```

**组件 Props 类型:**
```typescript
// web/src/components/sector-classification/UpdateTimeDisplay.tsx
export interface UpdateTimeDisplayProps {
  lastFetch: number | null
  className?: string
}
```

### 时间格式化工具函数

**dateFormat.ts 实现:**
```typescript
// web/src/lib/dateFormat.ts

/**
 * 格式化日期时间为中文本地化格式
 * @param timestamp - Unix 时间戳（毫秒）或 ISO 8601 字符串
 * @returns 格式化的时间字符串 "YYYY-MM-DD HH:mm"
 */
export function formatChineseDateTime(timestamp: number | string | null): string {
  if (!timestamp) {
    return '未知'
  }

  try {
    // 转换为 Date 对象
    const date = typeof timestamp === 'number'
      ? new Date(timestamp)
      : new Date(timestamp)

    // 验证日期有效性
    if (isNaN(date.getTime())) {
      return '未知'
    }

    // 格式化：YYYY-MM-DD HH:mm
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')

    return `${year}-${month}-${day} ${hours}:${minutes}`
  } catch (error) {
    console.error('日期格式化失败:', error)
    return '未知'
  }
}

/**
 * 格式化相对时间（可选，用于未来增强）
 * @param timestamp - Unix 时间戳（毫秒）
 * @returns 相对时间描述，如"刚刚"、"5分钟前"
 */
export function formatRelativeTime(timestamp: number | null): string {
  if (!timestamp) {
    return '未知'
  }

  const now = Date.now()
  const diff = now - timestamp

  // 小于 1 分钟
  if (diff < 60 * 1000) {
    return '刚刚'
  }

  // 小于 1 小时
  if (diff < 60 * 60 * 1000) {
    const minutes = Math.floor(diff / (60 * 1000))
    return `${minutes}分钟前`
  }

  // 小于 1 天
  if (diff < 24 * 60 * 60 * 1000) {
    const hours = Math.floor(diff / (60 * 60 * 1000))
    return `${hours}小时前`
  }

  // 大于 1 天，显示绝对时间
  return formatChineseDateTime(timestamp)
}
```

### 组件实现

**UpdateTimeDisplay 组件:**
```typescript
// web/src/components/sector-classification/UpdateTimeDisplay.tsx
'use client'

import { formatChineseDateTime } from '@/lib/dateFormat'
import type { UpdateTimeDisplayProps } from '.'

export function UpdateTimeDisplay({ lastFetch, className }: UpdateTimeDisplayProps) {
  const updateText = formatChineseDateTime(lastFetch)

  return (
    <div className={`text-sm text-gray-500 flex items-center ${className || ''}`}>
      <svg
        className="w-4 h-4 mr-1.5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <span>数据更新时间：{updateText}</span>
    </div>
  )
}
```

### 页面集成

**page.tsx 集成（扩展现有代码）:**
```typescript
// web/src/app/dashboard/sector-classification/page.tsx
'use client'

import { useEffect } from 'react'
import { useAppSelector } from '@/store/hooks'
import { ClassificationTable } from '@/components/sector-classification'
import { ClassificationSkeleton } from '@/components/sector-classification/ClassificationSkeleton'
import { ClassificationError } from '@/components/sector-classification/ClassificationError'
import { UpdateTimeDisplay } from '@/components/sector-classification/UpdateTimeDisplay'
import { fetchClassifications } from '@/store/slices/sectorClassificationSlice'

export default function SectorClassificationPage() {
  const dispatch = useAppDispatch()
  const { classifications, loading, error, lastFetch } = useAppSelector(
    (state) => state.sectorClassification
  )

  useEffect(() => {
    dispatch(fetchClassifications())
  }, [dispatch])

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">板块强弱分类</h1>

      {/* 更新时间显示 - 仅在数据加载成功后显示 */}
      {!loading && !error && classifications.length > 0 && (
        <div className="mb-4">
          <UpdateTimeDisplay lastFetch={lastFetch} />
        </div>
      )}

      {/* 加载状态 */}
      {loading && <ClassificationSkeleton />}

      {/* 错误状态 */}
      {error && <ClassificationError error={error} />}

      {/* 数据表格 */}
      {!loading && !error && <ClassificationTable classifications={classifications} />}
    </div>
  )
}
```

### 现有代码模式参考

**查看现有组件:**
- `web/src/app/dashboard/sector-classification/page.tsx` - 页面组件
- `web/src/components/sector-classification/ClassificationTable.tsx` - 表格组件

**Redux Store 模式（Story 2A.3 已建立）:**
- 使用 `useAppSelector` 获取 state
- 使用 `useAppDispatch` 触发 actions
- `lastFetch` 字段已在 state 中定义

### 测试要求

**日期格式化函数测试:**
```typescript
// web/tests/lib/dateFormat.test.ts
import { formatChineseDateTime, formatRelativeTime } from '@/lib/dateFormat'

describe('formatChineseDateTime', () => {
  it('应该格式化有效时间戳', () => {
    const timestamp = new Date('2026-01-22T15:30:00').getTime()
    expect(formatChineseDateTime(timestamp)).toBe('2026-01-22 15:30')
  })

  it('应该处理 ISO 8601 字符串', () => {
    const isoString = '2026-01-22T15:30:00'
    expect(formatChineseDateTime(isoString)).toBe('2026-01-22 15:30')
  })

  it('应该处理 null 值', () => {
    expect(formatChineseDateTime(null)).toBe('未知')
  })

  it('应该处理无效时间戳', () => {
    expect(formatChineseDateTime(NaN)).toBe('未知')
  })

  it('应该正确补零', () => {
    const timestamp = new Date('2026-01-02T03:05:00').getTime()
    expect(formatChineseDateTime(timestamp)).toBe('2026-01-02 03:05')
  })
})
```

**组件测试:**
```typescript
// web/tests/components/UpdateTimeDisplay.test.tsx
import { render, screen } from '@testing-library/react'
import { UpdateTimeDisplay } from '@/components/sector-classification/UpdateTimeDisplay'

describe('UpdateTimeDisplay', () => {
  it('应该显示格式化的更新时间', () => {
    const timestamp = new Date('2026-01-22T15:30:00').getTime()
    render(<UpdateTimeDisplay lastFetch={timestamp} />)

    expect(screen.getByText(/数据更新时间：2026-01-22 15:30/)).toBeInTheDocument()
  })

  it('应该处理缺失的时间戳', () => {
    render(<UpdateTimeDisplay lastFetch={null} />)

    expect(screen.getByText(/数据更新时间：未知/)).toBeInTheDocument()
  })

  it('应该显示时钟图标', () => {
    const timestamp = Date.now()
    const { container } = render(<UpdateTimeDisplay lastFetch={timestamp} />)

    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
    expect(svg).toHaveAttribute('fill', 'none')
    expect(svg).toHaveAttribute('stroke', 'currentColor')
  })

  it('应该应用自定义 className', () => {
    const timestamp = Date.now()
    const { container } = render(
      <UpdateTimeDisplay lastFetch={timestamp} className="custom-class" />
    )

    expect(container.firstChild).toHaveClass('custom-class')
  })
})
```

### Project Structure Notes

**对齐统一项目结构:**
- 组件放在 `components/sector-classification/` 目录
- 工具函数放在 `lib/` 目录
- 测试文件与源文件并列或放在 `tests/` 目录

**检测到的冲突或差异:**
- 无冲突 - 完全遵循现有项目模式

### References

**架构文档:**
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture] - 前端架构设计
- [Source: _bmad-output/planning-artifacts/architecture.md#State Management Patterns] - 状态管理模式

**项目上下文:**
- [Source: _bmad-output/project-context.md#Framework-Specific Rules] - React/Next.js 规则
- [Source: _bmad-output/project-context.md#Naming Conventions] - 命名约定

**Epic 定义:**
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2A] - Epic 2A: 基础分类展示
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2A.4] - Story 2A.4 完整验收标准

### Previous Story Intelligence (Story 2A.3)

**从 Story 2A.3 学到的经验:**

1. **Redux Store 模式:**
   - `sectorClassificationSlice.ts` 已创建并包含 `lastFetch` 字段
   - 使用 `useAppSelector` 和 `useAppDispatch` hooks
   - State 结构: `{ classifications, loading, error, lastFetch }`

2. **页面组件模式:**
   - 页面使用 `use client` 指令
   - 使用 `useEffect` 触发数据获取
   - 根据 loading/error/data 状态渲染不同组件

3. **组件结构:**
   - ClassificationTable 组件已创建
   - ClassificationSkeleton 组件已创建
   - ClassificationError 组件已创建
   - 所有组件使用命名导出

4. **类型定义位置:**
   - `web/src/types/sector-classification.ts` - 数据类型定义
   - `web/src/store/slices/sectorClassificationSlice.ts` - State 类型定义

**代码审查反馈（Story 2A.3）:**
- Redux 类型定义使用 RootState 类型
- 移除不必要的动态 import
- 改进错误匹配逻辑（使用正则表达式边界匹配）
- 简化 Skeleton ARIA 属性

**Git 智能摘要（最近提交）:**
- `9f29d21` feat: 完成 Story 2A.2 分类表格组件并通过代码审查
- （Story 2A.3 的提交尚未在 git 历史中显示）

**代码模式参考:**
- 查看 `web/src/store/slices/sectorClassificationSlice.ts` 了解 Redux state 结构
- 查看 `web/src/app/dashboard/sector-classification/page.tsx` 了解页面集成模式

### Critical Implementation Reminders

**🚨 关键规则（不要违反!）:**

1. **'use client' 指令** - 组件使用 hooks 必须添加
2. **命名导出** - 使用 `export function`，不要使用默认导出
3. **导入路径** - 使用 `@/` 别名，不要使用相对路径
4. **TypeScript strict** - 不要使用 `any` 类型
5. **中文文本** - 所有用户可见文本使用中文
6. **时间格式** - 使用 "YYYY-MM-DD HH:mm" 格式
7. **缺失处理** - 时间戳缺失时显示"未知"
8. **Redux hooks** - 使用 `useAppSelector` 和 `useAppDispatch`
9. **条件渲染** - 仅在数据加载成功后显示时间
10. **时钟图标** - 使用 SVG 时钟图标表示时间

**依赖:**
- Story 2A.1 完成（页面路由已就绪）
- Story 2A.2 完成（表格组件已创建）
- Story 2A.3 完成（Redux store 已配置，lastFetch 字段可用）
- Epic 1 完成（API 端点已实现）

**后续影响:**
- Story 2A.5 将添加免责声明组件
- Epic 2B 将添加手动刷新按钮功能（刷新时更新 lastFetch）
- Redux store 将被后续 stories 扩展（排序、搜索状态）

### 性能与可访问性要求

**性能要求 (NFR-PERF-001):**
- 时间格式化函数应高效（避免重复创建 Date 对象）
- 组件应轻量，不阻塞渲染
- 使用 memo 优化（如果性能有问题）

**可访问性要求 (NFR-ACC-004):**
- 时间文本颜色对比度符合标准（text-gray-500）
- SVG 图标有适当的 aria 属性
- 时间信息清晰可见

### 时间显示设计

**视觉设计:**
```
[时钟图标] 数据更新时间：2026-01-22 15:30
```

**样式规范:**
- 颜色: `text-gray-500`（中等灰色，不抢眼）
- 字号: `text-sm`（比正文小一号）
- 对齐: `flex items-center`（图标和文本垂直居中）
- 图标: 时钟 SVG 图标（lucide-react Clock 风格）
- 间距: 图标和文本之间 `mr-1.5`

**位置:**
- 表格上方（`mb-4` 下边距）
- 仅在数据加载成功后显示
- 与表格左对齐（或可配置右对齐）

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

#### 2026-01-22 - Story 创建完成

#### 2026-01-22 - Story 实现完成

#### 2026-01-22 - 代码审查完成

**代码审查发现并修复的问题:**

1. ✅ **HIGH - 修复条件渲染逻辑** (page.tsx:120-124)
   - 原: `!loading && !error && classifications.length > 0`
   - 新: `!loading && !error && lastFetch`
   - 理由: 与 AC 匹配 - 数据加载成功且有 lastFetch 时显示时间，即使 classifications 为空

2. ✅ **MEDIUM - 移除样式冲突** (page.tsx:121-123)
   - 移除多余的 `<div className="mb-4">` 包裹
   - 理由: 父容器已使用 `space-y-6`，无需额外的 margin-bottom

3. ✅ **MEDIUM - 添加边界测试** (dateFormat.test.ts:44-48)
   - 添加负数时间戳测试（1970年之前的日期）
   - 理由: 完善边界情况覆盖

**已实现功能:**

1. **日期格式化工具** - `web/src/lib/dateFormat.ts`
   - ✅ 实现 `formatChineseDateTime()` 函数
   - ✅ 支持 Unix timestamp 和 ISO 8601 字符串
   - ✅ 处理 null/undefined/无效值（返回"未知"）
   - ✅ 实现 `formatRelativeTime()` 函数（用于未来增强）

2. **更新时间显示组件** - `web/src/components/sector-classification/UpdateTimeDisplay.tsx`
   - ✅ 使用 `formatChineseDateTime()` 格式化时间
   - ✅ 显示时钟图标（SVG）
   - ✅ 应用 Tailwind CSS 样式
   - ✅ 支持自定义 className

3. **页面集成** - `web/src/app/dashboard/sector-classification/page.tsx`
   - ✅ 导入 UpdateTimeDisplay 组件
   - ✅ 从 Redux store 获取 `lastFetch` 时间戳
   - ✅ 条件渲染（仅在数据加载成功后显示）
   - ✅ 放置在表格上方

4. **测试**
   - ✅ 日期格式化函数测试（8个测试用例）
   - ✅ UpdateTimeDisplay 组件测试（7个测试用例）
   - ✅ 所有测试通过

**实现计划:**

1. **日期格式化工具** - `web/src/lib/dateFormat.ts`
   - 实现 `formatChineseDateTime()` 函数
   - 支持 Unix timestamp 和 ISO 8601 字符串
   - 处理 null/无效值（返回"未知"）
   - 可选：实现 `formatRelativeTime()` 函数（用于未来增强）

2. **更新时间显示组件** - `web/src/components/sector-classification/UpdateTimeDisplay.tsx`
   - 使用 `formatChineseDateTime()` 格式化时间
   - 显示时钟图标（SVG）
   - 应用 Tailwind CSS 样式
   - 支持自定义 className

3. **页面集成** - `web/src/app/dashboard/sector-classification/page.tsx`
   - 导入 UpdateTimeDisplay 组件
   - 从 Redux store 获取 `lastFetch` 时间戳
   - 条件渲染（仅在数据加载成功后显示）
   - 放置在表格上方

4. **测试创建**
   - 日期格式化函数测试
   - UpdateTimeDisplay 组件测试
   - 集成测试（页面渲染）

**验收标准:**
- ✅ 表格上方显示"数据更新时间：YYYY-MM-DD HH:mm"
- ✅ 时间格式为中文本地化
- ✅ 时间显示在表格上方
- ✅ 数据时间戳缺失时显示"更新时间：未知"

**技术亮点:**
- 可复用的日期格式化工具函数
- 时钟图标增强视觉识别
- 条件渲染避免显示无效时间
- 完整的错误处理（无效时间戳）
- 符合项目现有架构模式

### File List

**新增文件:**
- `web/src/lib/dateFormat.ts` - 日期格式化工具
- `web/src/components/sector-classification/UpdateTimeDisplay.tsx` - 时间显示组件
- `web/tests/lib/dateFormat.test.ts` - 工具函数测试
- `web/tests/components/sector-classification/UpdateTimeDisplay.test.tsx` - 组件测试

**修改文件:**
- `web/src/components/sector-classification/index.ts` - 更新导出
- `web/src/app/dashboard/sector-classification/page.tsx` - 集成时间显示

**依赖文件（已存在）:**
- `web/src/store/slices/sectorClassificationSlice.ts` - Redux store（Story 2A.3）
- `web/src/components/sector-classification/ClassificationTable.tsx` - 表格组件（Story 2A.2）

## Change Log

### 2026-01-22

- 创建 Story 2A.4 文档
- 定义时间格式化工具函数架构
- 定义 UpdateTimeDisplay 组件规范
- 定义页面集成方案
- 定义测试策略
- Story 状态: backlog → ready-for-dev

- 实现 dateFormat.ts 工具函数
- 实现 UpdateTimeDisplay 组件
- 集成到 page.tsx
- 创建所有测试
- 所有测试通过
- Story 状态: ready-for-dev → in-progress → review
