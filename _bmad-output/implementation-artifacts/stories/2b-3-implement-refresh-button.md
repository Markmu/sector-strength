# Story 2B.3: 实现手动刷新按钮

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 投资者,
I want 手动刷新分类数据,
So that 我可以获取最新的分类结果。

## Acceptance Criteria

**Given** 用户已查看分类表格
**When** 用户点击"刷新"按钮
**Then** 系统重新调用 GET /api/v1/sector-classifications
**And** 显示加载状态（按钮变为禁用状态，显示旋转图标）
**When** 刷新成功
**Then** 表格数据更新为最新结果
**And** 更新时间显示刷新后的时间
**And** 按钮恢复正常状态
**When** 刷新失败
**Then** 显示错误提示
**And** 按钮恢复正常状态
**And** 提供"重试"选项
**And** 刷新按钮使用 shadcn/ui Button 组件，带有刷新图标

## Tasks / Subtasks

- [x] Task 1: 创建刷新按钮组件 (AC: #)
  - [x] Subtask 1.1: 创建 `web/src/components/sector-classification/RefreshButton.tsx`
  - [x] Subtask 1.2: 使用 shadcn/ui Button 组件
  - [x] Subtask 1.3: 添加刷新图标（RefreshCw from lucide-react）
  - [x] Subtask 1.4: 实现 loading 状态显示（旋转动画）
  - [x] Subtask 1.5: 实现禁用状态（loading 时禁用）

- [x] Task 2: 集成 Redux action (AC: #)
  - [x] Subtask 2.1: 使用现有的 `fetchClassifications` action
  - [x] Subtask 2.2: 连接按钮点击到 Redux dispatch
  - [x] Subtask 2.3: 处理加载状态（从 Redux store 获取）
  - [x] Subtask 2.4: 处理错误状态（从 Redux store 获取）

- [x] Task 3: 实现按钮状态管理 (AC: #)
  - [x] Subtask 3.1: 根据 loading 状态显示旋转图标
  - [x] Subtask 3.2: 根据 loading 状态禁用按钮
  - [x] Subtask 3.3: 根据 error 状态保持按钮可点击（重试）

- [x] Task 4: 集成到页面组件 (AC: #)
  - [x] Subtask 4.1: 在搜索框旁边或表格上方添加刷新按钮
  - [x] Subtask 4.2: 连接 Redux loading 和 error 状态
  - [x] Subtask 4.3: 确保刷新后更新时间显示更新

- [x] Task 5: 处理刷新成功 (AC: #)
  - [x] Subtask 5.1: 验证表格数据更新
  - [x] Subtask 5.2: 验证更新时间显示更新
  - [x] Subtask 5.3: 按钮恢复正常状态

- [x] Task 6: 处理刷新失败 (AC: #)
  - [x] Subtask 6.1: 显示错误提示（由页面组件的 ClassificationError 处理）
  - [x] Subtask 6.2: 按钮恢复正常状态
  - [x] Subtask 6.3: 提供重试选项（按钮再次可点击）

- [x] Task 7: 创建测试 (AC: #)
  - [x] Subtask 7.1: 测试刷新按钮渲染
  - [x] Subtask 7.2: 测试刷新按钮点击触发
  - [x] Subtask 7.3: 测试 loading 状态显示
  - [x] Subtask 7.4: 测试成功后状态恢复
  - [x] Subtask 7.5: 测试失败后状态恢复和重试

## Dev Notes

### Epic 2B 完整上下文

**Epic 目标:** 在基础分类展示之上，添加排序、搜索、刷新等高级交互功能，提升用户体验。

**FRs 覆盖:**
- FR8: 用户可以手动触发数据刷新

**NFRs 相关:**
- FR28: 系统在 API 错误时显示友好的错误消息和重试选项

**依赖关系:**
- 依赖 Epic 2A 完成（基础分类展示已实现）
- 依赖 Story 2A.3 完成（Redux store 和 fetchClassifications action 已实现）
- 依赖 Story 2A.4 完成（更新时间显示已实现）
- 与 Epic 2B 其他功能并行（排序、搜索、键盘导航）

### 架构模式与约束

**前端技术栈:**
- Next.js 16.1.1 (使用 App Router)
- React 19.2.0 (需要 'use client' 指令)
- TypeScript 5 (strict mode)
- Tailwind CSS 4.x
- Redux Toolkit (全局状态管理)
- shadcn/ui 组件库

**状态管理策略:**
| 状态类型 | 使用方案 | 原因 |
|---------|----------|------|
| 分类数据 | Redux Toolkit | 全局共享，异步获取 |
| 加载状态 | Redux Toolkit | 与数据请求相关 |
| 错误状态 | Redux Toolkit | 与数据请求相关 |

**Redux Store (已存在于 Story 2A.3):**
```typescript
// web/src/store/slices/sectorClassificationSlice.ts
interface SectorClassificationState {
  classifications: SectorClassification[]
  loading: boolean
  error: string | null
  lastFetch: string | null
}

// Actions (已存在)
export const fetchClassifications = createAsyncThunk(
  'sectorClassification/fetchAll',
  async () => {
    const response = await sectorClassificationApi.getClassifications()
    return response.data
  }
)
```

### 项目结构规范

**文件结构:**
```
web/src/
├── components/sector-classification/
│   ├── RefreshButton.tsx                      # 新增：刷新按钮组件
│   └── index.ts                               # 修改：导出新组件
├── store/slices/
│   └── sectorClassificationSlice.ts           # 已存在：Redux store
└── tests/
    └── components/
        └── sector-classification/
            └── RefreshButton.test.tsx          # 新增：按钮测试
```

**命名约定:**
- 组件文件: `PascalCase.tsx`
- 测试文件: `*.test.tsx`

### 刷新按钮组件

**RefreshButton 组件:**
```typescript
// web/src/components/sector-classification/RefreshButton.tsx
'use client'

import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useDispatch, useSelector } from 'react-redux'
import { fetchClassifications } from '@/store'
import type { RootState } from '@/store'

interface RefreshButtonProps {
  className?: string
  children?: React.ReactNode
}

const DEFAULT_LABEL = '刷新'

export function RefreshButton({
  className = '',
  children = DEFAULT_LABEL
}: RefreshButtonProps) {
  const dispatch = useDispatch()
  const loading = useSelector((state: RootState) =>
    state.sectorClassification.loading
  )

  const handleRefresh = () => {
    dispatch(fetchClassifications() as any)
  }

  return (
    <Button
      onClick={handleRefresh}
      disabled={loading}
      variant="outline"
      size="sm"
      className={`${className} gap-2`}
      aria-label="刷新数据"
    >
      <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
      <span>{children}</span>
    </Button>
  )
}
```

### 带工具提示的刷新按钮

**增强版本（可选）:**
```typescript
// web/src/components/sector-classification/RefreshButton.tsx
'use client'

import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useDispatch, useSelector } from 'react-redux'
import { fetchClassifications } from '@/store'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/Tooltip'
import type { RootState } from '@/store'

interface RefreshButtonProps {
  className?: string
  showLabel?: boolean
}

export function RefreshButton({
  className = '',
  showLabel = true
}: RefreshButtonProps) {
  const dispatch = useDispatch()
  const loading = useSelector((state: RootState) =>
    state.sectorClassification.loading
  )
  const lastFetch = useSelector((state: RootState) =>
    state.sectorClassification.lastFetch
  )

  const handleRefresh = () => {
    dispatch(fetchClassifications() as any)
  }

  const button = (
    <Button
      onClick={handleRefresh}
      disabled={loading}
      variant="outline"
      size="sm"
      className={`${className} gap-2`}
      aria-label="刷新数据"
    >
      <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
      {showLabel && <span>刷新</span>}
    </Button>
  )

  // 显示上次更新时间的工具提示
  if (lastFetch) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            {button}
          </TooltipTrigger>
          <TooltipContent>
            <p>上次更新: {new Date(lastFetch).toLocaleString('zh-CN')}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return button
}
```

### 页面集成

**页面组件集成:**
```typescript
// web/src/app/dashboard/sector-classification/page.tsx (修改)
import { RefreshButton } from '@/components/sector-classification/RefreshButton'
import { SearchBar } from '@/components/sector-classification/SearchBar'

export default function SectorClassificationPage() {
  // ... 现有代码

  return (
    <DashboardLayout>
      <DashboardHeader
        title={PAGE_TEXT.title}
        subtitle={PAGE_TEXT.subtitle}
      />

      <div className="space-y-6">
        {/* 搜索和刷新工具栏 */}
        <div className="flex items-center justify-between gap-4">
          <SearchBar className="flex-1" />
          <RefreshButton />
        </div>

        {/* 更新时间显示 */}
        {!loading && !error && lastFetch && (
          <UpdateTimeDisplay lastFetch={lastFetch} />
        )}

        {/* 分类表格或错误提示 */}
        {loading && classifications.length === 0 ? (
          <ClassificationSkeleton />
        ) : error ? (
          <ClassificationError
            error={error}
            onRetry={handleRetry}
            isRetrying={loading}
          />
        ) : (
          <ClassificationTable
            data={classifications}
            loading={loading}
            emptyText={PAGE_TEXT.empty}
          />
        )}

        {/* 免责声明 */}
        <Disclaimer showSeparator={true} />
      </div>
    </DashboardLayout>
  )
}
```

### 错误处理

**错误处理策略:**
- 复用现有的 `ClassificationError` 组件
- 该组件已经处理了错误显示和重试功能
- 刷新按钮失败时，按钮恢复正常状态
- 用户可以再次点击刷新按钮重试

**ClassificationError 组件（已存在）:**
```typescript
// web/src/components/sector-classification/ClassificationError.tsx (Story 2A.3)
interface ClassificationErrorProps {
  error: string | null
  onRetry: () => void
  isRetrying: boolean
}

export function ClassificationError({
  error,
  onRetry,
  isRetrying
}: ClassificationErrorProps) {
  // ... 显示错误和重试按钮
}
```

### Testing Standards Summary

**测试要求:**
- 测试刷新按钮渲染
- 测试点击触发 Redux action
- 测试 loading 状态显示（旋转图标）
- 测试禁用状态（loading 时禁用）
- 测试成功后状态恢复
- 测试失败后状态恢复和重试

**组件测试示例:**
```typescript
// web/tests/components/sector-classification/RefreshButton.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import { RefreshButton } from '@/components/sector-classification/RefreshButton'
import sectorClassificationReducer from '@/store/slices/sectorClassificationSlice'

describe('RefreshButton', () => {
  const mockStore = configureStore({
    reducer: {
      sectorClassification: sectorClassificationReducer,
    },
  })

  it('应该渲染刷新按钮', () => {
    render(
      <Provider store={mockStore}>
        <RefreshButton />
      </Provider>
    )

    expect(screen.getByRole('button', { name: /刷新/ })).toBeInTheDocument()
  })

  it('应该显示刷新图标', () => {
    render(
      <Provider store={mockStore}>
        <RefreshButton showLabel={false} />
      </Provider>
    )

    const icon = screen.getByRole('button').querySelector('svg')
    expect(icon).toBeInTheDocument()
  })

  it('loading 状态下应该禁用按钮', () => {
    const store = configureStore({
      reducer: {
        sectorClassification: sectorClassificationReducer,
      },
      preloadedState: {
        sectorClassification: { loading: true }
      }
    })

    render(
      <Provider store={store}>
        <RefreshButton />
      </Provider>
    )

    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
  })

  it('loading 状态下应该显示旋转动画', () => {
    const store = configureStore({
      reducer: {
        sectorClassification: sectorClassificationReducer,
      },
      preloadedState: {
        sectorClassification: { loading: true }
      }
    })

    render(
      <Provider store={store}>
        <RefreshButton showLabel={false} />
      </Provider>
    )

    const icon = screen.getByRole('button').querySelector('svg')
    expect(icon).toHaveClass('animate-spin')
  })
})
```

### Project Structure Notes

**对齐统一项目结构:**
- 组件放在 `components/sector-classification/` 目录
- 测试放在 `tests/components/sector-classification/` 目录
- 使用 Redux Toolkit 管理全局状态
- 复用现有的 Redux store 和 actions

**检测到的冲突或差异:**
- 无冲突 - 复用现有 Redux 架构

### References

**架构文档:**
- [Source: _bmad-output/planning-artifacts/architecture.md#State Management Patterns] - 状态管理模式
- [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns] - 通信模式

**项目上下文:**
- [Source: _bmad-output/planning-artifacts/prd.md#FR8] - FR8: 手动刷新功能需求
- [Source: _bmad-output/planning-artifacts/prd.md#FR28] - FR28: API 错误提示

**Epic 定义:**
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2B] - Epic 2B: 高级交互功能
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2B.3] - Story 2B.3 完整验收标准

### Previous Story Intelligence (Stories 2A.3, 2B.1, 2B.2)

**从之前 Story 学到的经验:**

1. **Redux Store 模式 (Story 2A.3):**
   - Redux store: `sectorClassificationSlice`
   - 异步 action: `fetchClassifications` (createAsyncThunk)
   - 状态: `classifications`, `loading`, `error`, `lastFetch`
   - 使用 `useDispatch` 和 `useSelector` 连接组件

2. **组件创建模式 (Story 2B.1, 2B.2):**
   - 使用 'use client' 指令
   - 使用命名导出 `export function`
   - Props 接口定义清晰
   - 支持可选的 className 自定义

3. **错误处理模式 (Story 2A.3):**
   - ClassificationError 组件处理错误显示
   - 提供 onRetry 回调函数
   - isRetrying 状态控制按钮禁用

4. **按钮模式 (项目现有):**
   - shadcn/ui Button 组件
   - variant="outline" 用于次要操作
   - size="sm" 用于紧凑按钮
   - lucide-react 图标

**代码模式参考:**
- 查看 `web/src/store/slices/sectorClassificationSlice.ts` 了解 Redux store
- 查看 `web/src/components/sector-classification/ClassificationError.tsx` 了解错误处理
- 查看 `web/src/components/sector-classification/SearchBar.tsx` 了解组件集成模式

### Critical Implementation Reminders

**🚨 关键规则（不要违反!）:**

1. **'use client' 指令** - 组件使用 Redux hooks 必须添加
2. **命名导出** - 使用 `export function`，不要使用默认导出
3. **导入路径** - 使用 `@/` 别名，不要使用相对路径
4. **Redux Toolkit** - 复用现有 store 和 actions
5. **TypeScript strict** - 不要使用 `any` 类型
6. **shadcn/ui Button** - 必须使用项目现有的 Button 组件
7. **lucide-react 图标** - 使用 RefreshCw 图标
8. **loading 状态** - 从 Redux store 获取
9. **animate-spin** - 使用 Tailwind 的旋转动画类
10. **错误处理** - 复用现有的 ClassificationError 组件

**依赖:**
- Epic 2A 完成（基础分类展示已实现）
- Story 2A.3 完成（Redux store 和 fetchClassifications action 已实现）
- Story 2A.4 完成（更新时间显示已实现）
- Redux Toolkit 已配置
- shadcn/ui Button 组件已安装

**后续影响:**
- Story 2B.4 将添加键盘导航支持
- Epic 2B 接近完成

### 性能与可访问性要求

**性能要求:**
- 按钮点击响应及时（无阻塞）
- 使用 Redux 的异步 action 处理 API 请求
- 避免不必要的重渲染

**可访问性要求 (NFR-ACC-002):**
- 按钮有清晰的 aria-label
- 旋转图标有适当的 aria 状态
- 键盘导航支持（Tab + Enter）
- 禁用状态明确可感知

**键盘支持:**
- Tab 键聚焦按钮
- Enter 或 Space 键触发刷新
- 禁用状态不响应键盘

### 刷新功能设计

**刷新特性:**
1. **手动触发** - 用户点击按钮触发刷新
2. **加载状态** - 按钮禁用，图标旋转
3. **成功处理** - 数据和更新时间自动更新
4. **失败处理** - 显示错误，按钮恢复可重试
5. **与自动刷新区分** - 这是手动刷新，不影响可能存在的自动刷新逻辑

**按钮 UI:**
- 图标：RefreshCw（lucide-react）
- 标签："刷新"（可选）
- 样式：outline 变体，sm 尺寸
- 位置：搜索框旁边或表格上方

**工具提示（可选增强）:**
- 显示上次更新时间
- 帮助用户了解数据时效性

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

#### 2026-01-22 - Story 实现完成

**实现内容:**
- ✅ 创建 RefreshButton 组件 (`RefreshButton.tsx`)
- ✅ 集成 Redux store 和 fetchClassifications action
- ✅ 实现 loading 状态显示（旋转图标 animate-spin）
- ✅ 实现禁用状态（loading 时禁用）
- ✅ 在页面中添加刷新按钮（与搜索框并排）
- ✅ 创建完整测试覆盖（渲染、交互、loading 状态、可访问性）
- ✅ 所有测试通过
- ✅ ESLint 检查通过

#### 2026-01-22 - 代码审查修复

**修复内容:**
- ✅ 添加工具栏容器语义标记（`role="toolbar"` 和 `aria-label`）
- ✅ 更新 Subtask 6.1 描述以准确反映实现
- ✅ 添加 lastFetch 更新验证测试
- ✅ 添加错误状态和重试场景测试
- ✅ 更新 File List 记录 sprint-status.yaml 修改

**问题修复:**
- HIGH: 添加工具栏容器的语义标记（可访问性改进）
- HIGH: 更新故事描述与实际实现一致
- HIGH: 添加数据更新验证测试
- MEDIUM: 添加失败重试场景测试
- MEDIUM: 记录所有修改的文件

**技术实现:**
- 使用 `useDispatch` 和 `useSelector` 连接 Redux store
- 使用 `fetchClassifications` 异步 action 触发刷新
- loading 状态从 Redux store 的 `selectLoading` 获取
- 旋转动画使用 Tailwind 的 `animate-spin` 类
- 按钮禁用通过 `disabled={loading}` 控制
- aria-busy 属性提供可访问性支持

**测试覆盖:**
- 渲染测试（按钮、图标、标签、aria 属性）
- 交互测试（点击触发、键盘操作）
- loading 状态测试（禁用、旋转动画、阻止重复点击）
- 可访问性测试（Tab 聚焦、aria-hidden）
- 样式测试（类名、变体、尺寸）

**验收标准验证:**
- ✅ 点击按钮触发 fetchClassifications action
- ✅ loading 时按钮禁用
- ✅ loading 时图标旋转（animate-spin）
- ✅ 成功后数据自动更新（Redux store）
- ✅ 成功后更新时间显示自动更新
- ✅ 失败后显示错误提示（复用 ClassificationError）
- ✅ 失败后按钮恢复可重试
- ✅ 使用 shadcn/ui Button 组件和 RefreshCw 图标

**Story 内容:**
- ✅ 完整的用户故事定义
- ✅ BDD 格式的验收标准
- ✅ 详细的任务分解（7个任务，30+子任务）
- ✅ 完整的开发者上下文和实现指南
- ✅ Redux store 复用方案
- ✅ 刷新按钮组件设计
- ✅ 页面集成方案
- ✅ 错误处理策略
- ✅ 测试策略

**实现计划:**
1. 创建 RefreshButton 组件
2. 集成 Redux store 和 fetchClassifications action
3. 实现 loading 状态显示（旋转图标）
4. 实现禁用状态
5. 在页面中添加刷新按钮
6. 处理成功和失败状态
7. 创建测试

**验收标准:**
- ✅ 点击按钮重新调用 GET /api/v1/sector-classifications
- ✅ 显示加载状态（按钮禁用，图标旋转）
- ✅ 刷新成功后表格数据更新
- ✅ 刷新成功后更新时间显示更新
- ✅ 刷新失败显示错误提示
- ✅ 刷新失败按钮恢复并提供重试
- ✅ 使用 shadcn/ui Button 组件和刷新图标

**技术亮点:**
- 复用现有 Redux store 和 actions
- 简洁的实现（无新状态管理）
- 清晰的用户反馈（旋转图标）
- 完整的错误处理和重试机制

**Epic 2B 进度:**
- ✅ Story 2B.1: 表格排序功能 - done
- ✅ Story 2B.2: 搜索功能 - done
- ✅ Story 2B.3: 手动刷新按钮 - review
- ⏳ Story 2B.4: 键盘导航支持 - backlog

**Epic 2B 完成度:** 75% (3/4 stories done, 1 in review)

### File List

**新增文件:**
- `web/src/components/sector-classification/RefreshButton.tsx` - 刷新按钮组件
- `web/tests/components/sector-classification/RefreshButton.test.tsx` - 按钮测试

**修改文件:**
- `web/src/components/sector-classification/index.ts` - 导出新组件
- `web/src/app/dashboard/sector-classification/page.tsx` - 添加刷新按钮和工具栏语义标记
- `_bmad-output/implementation-artifacts/sprint-status.yaml` - 由代码审查工作流更新状态

**依赖文件（已存在）:**
- `web/src/store/slices/sectorClassificationSlice.ts` - Redux store (Story 2A.3)
- `web/src/components/sector-classification/ClassificationError.tsx` - 错误组件 (Story 2A.3)
- `web/src/components/ui/Button.tsx` - shadcn/ui Button 组件
- `web/src/components/sector-classification/UpdateTimeDisplay.tsx` - 更新时间显示 (Story 2A.4)

## Change Log

### 2026-01-22

- 创建 Story 2B.3 文档
- 定义刷新功能需求
- 定义 Redux 集成方案
- 定义刷新按钮组件设计
- 定义加载和错误处理策略
- 定义页面集成方案
- 定义测试策略
- Story 状态: backlog → ready-for-dev

#### 2026-01-22 - Story 实现完成

- 实现 RefreshButton 组件
- 集成到页面组件
- 创建完整测试覆盖
- 所有测试通过
- ESLint 检查通过
- Story 状态: ready-for-dev → review
