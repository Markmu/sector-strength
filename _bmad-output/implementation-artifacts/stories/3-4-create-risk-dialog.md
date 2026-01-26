# Story 3.4: 创建风险提示弹窗

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 新用户,
I want 首次访问时看到风险提示弹窗,
So that 我理解投资风险并谨慎决策。

## Acceptance Criteria

**Given** 用户首次访问板块分类页面
**When** 页面加载完成
**Then** 显示风险提示弹窗（一次性）
**And** 弹窗标题为"重要提示"
**And** 弹窗内容包括：
  - "本功能提供的板块分类数据仅供参考，不构成任何投资建议。"
  - "股票市场有风险，投资需谨慎。"
  - "过往表现不代表未来收益。"
  - "请根据自己的风险承受能力和投资目标做出独立决策。"
**And** 弹窗底部有"我已知晓并理解"按钮
**And** 点击按钮后关闭弹窗
**And** 使用 localStorage 记录用户已确认（不重复显示）
**And** 弹窗使用 shadcn/ui AlertDialog 组件

## Tasks / Subtasks

- [x] Task 1: 创建风险提示弹窗组件 (AC: #)
  - [x] Subtask 1.1: 创建 `web/src/components/sector-classification/RiskAlertDialog.tsx`
  - [x] Subtask 1.2: 添加 'use client' 指令
  - [x] Subtask 1.3: 使用命名导出 `export function RiskAlertDialog`
  - [x] Subtask 1.4: 定义 TypeScript Props 接口（open, onOpenChange, onConfirm）
  - [x] Subtask 1.5: 实现弹窗内容结构

- [x] Task 2: 实现风险提示内容 (AC: #)
  - [x] Subtask 2.1: 添加弹窗标题"重要提示"
  - [x] Subtask 2.2: 添加四条风险提示内容
  - [x] Subtask 2.3: 使用适当的视觉层次（标题、列表、图标）
  - [x] Subtask 2.4: 添加确认按钮"我已知晓并理解"
  - [x] Subtask 2.5: 使用警告图标（AlertTriangle）增强视觉效果

- [x] Task 3: 集成 AlertDialog 组件 (AC: #)
  - [x] Subtask 3.1: 导入 AlertDialog 组件（shadcn/ui）
  - [x] Subtask 3.2: 配置 AlertDialog 的 open 和 onOpenChange 属性
  - [x] Subtask 3.3: 实现确认按钮点击关闭弹窗
  - [x] Subtask 3.4: 确保弹窗模态显示（阻止背景交互）
  - [x] Subtask 3.5: 实现 ESC 键关闭功能

- [x] Task 4: 实现 localStorage 持久化 (AC: #)
  - [x] Subtask 4.1: 创建 `useRiskAlert` hook 管理状态
  - [x] Subtask 4.2: 使用 localStorage 键 `riskAlertAcknowledged`
  - [x] Subtask 4.3: 页面加载时检查 localStorage 状态
  - [x] Subtask 4.4: 用户确认后保存状态到 localStorage
  - [x] Subtask 4.5: 确认后不再显示弹窗

- [x] Task 5: 集成到页面组件 (AC: #)
  - [x] Subtask 5.1: 在 `page.tsx` 中导入 RiskAlertDialog 和 useRiskAlert hook
  - [x] Subtask 5.2: 在页面组件中调用 hook 获取状态和控制函数
  - [x] Subtask 5.3: 条件渲染弹窗（仅当未确认时显示）
  - [x] Subtask 5.4: 确保弹窗在页面加载后立即显示
  - [x] Subtask 5.5: 处理确认按钮点击事件

- [x] Task 6: 更新组件导出索引 (AC: #)
  - [x] Subtask 6.1: 在 `index.ts` 中添加 RiskAlertDialog 导出
  - [x] Subtask 6.2: 导出 useRiskAlert hook（如果单独文件）
  - [x] Subtask 6.3: 验证导出路径正确

- [x] Task 7: 创建测试 (AC: #)
  - [x] Subtask 7.1: 测试 localStorage 存储和读取
  - [x] Subtask 7.2: 测试弹窗首次访问显示
  - [x] Subtask 7.3: 测试确认后不再显示
  - [x] Subtask 7.4: 测试弹窗内容完整显示
  - [x] Subtask 7.5: 测试可访问性（role、aria 属性）

## Dev Notes

### Epic 3 完整上下文

**Epic 目标:** 提供分类说明文档、风险提示和免责声明，确保用户理解分类含义并满足金融科技合规要求。

**FRs 覆盖:**
- FR12: 系统在所有分类结果页面显示风险提示和免责声明
- FR23: 系统在所有页面显示免责声明

**NFRs 相关:**
- NFR-ACC-001: 系统应确保颜色对比度可接受

**依赖关系:**
- 依赖 Epic 2A 完成（页面已创建）
- 依赖 Story 3.1 完成（帮助弹窗已创建，可参考弹窗模式）
- 依赖 Story 3.3 完成（免责声明已集成，风险提示是补充）

**后续影响:**
- Epic 3 完成后，所有帮助和合规声明组件已就绪
- 其他投资相关页面可能需要相同的风险提示

### 风险提示 vs 免责声明区别

**风险提示弹窗（RiskAlertDialog）:**
- 一次性显示（首次访问）
- 需要用户确认（"我已知晓并理解"按钮）
- 使用 localStorage 记录确认状态
- 模态显示（阻止背景交互）
- 更正式的警告样式
- 位置：屏幕中央

**免责声明（Disclaimer）:**
- 始终显示在页面底部
- 无需用户确认
- 无状态记录
- 非模态（页面的一部分）
- 较低调的样式
- 位置：页面底部

### 架构模式与约束

**shadcn/ui AlertDialog 组件使用:**
- 使用 Radix UI 的 AlertDialog primitive
- AlertDialog 是 Dialog 的变体，专门用于需要用户确认的场景
- 内置 Alert 样式（警告图标、强调边框）
- 支持受控模式（open + onOpenChange）
- 自动处理焦点陷阱和可访问性

**localStorage 状态管理:**
```typescript
// localStorage 键名
const STORAGE_KEY = 'riskAlertAcknowledged'

// 存储值
localStorage.setItem(STORAGE_KEY, 'true')

// 读取值
const hasAcknowledged = localStorage.getItem(STORAGE_KEY) === 'true'
```

**弹窗显示逻辑:**
```typescript
// 页面加载时
useEffect(() => {
  const hasAcknowledged = localStorage.getItem('riskAlertAcknowledged') === 'true'
  if (!hasAcknowledged) {
    setOpen(true) // 显示弹窗
  }
}, [])

// 用户确认后
const handleConfirm = () => {
  localStorage.setItem('riskAlertAcknowledged', 'true')
  setOpen(false) // 关闭弹窗
}
```

### 项目结构规范

**文件结构:**
```
web/src/
├── app/dashboard/sector-classification/
│   └── page.tsx                              # 修改：集成风险提示弹窗
├── components/sector-classification/
│   ├── RiskAlertDialog.tsx                       # 新增：风险提示弹窗组件
│   ├── RiskAlertDialog.types.ts                 # 新增：类型定义
│   ├── useRiskAlert.ts                          # 新增：状态管理 hook
│   ├── RiskAlertDialog.test.tsx                 # 新增：弹窗测试
│   └── index.ts                              # 修改：导出新组件
└── hooks/
    └── useRiskAlert.ts                          # 可选：全局 hook 位置
```

**命名约定:**
- 组件文件: `PascalCase.tsx` (RiskAlertDialog.tsx)
- Hook 文件: `useRiskAlert.ts`
- 测试文件: `*.test.tsx` 或 `*.spec.tsx`

### TypeScript 类型定义

**RiskAlertDialog Props 类型:**
```typescript
// web/src/components/sector-classification/RiskAlertDialog.types.ts
export interface RiskAlertDialogProps {
  /**
   * 弹窗是否打开
   */
  open: boolean
  /**
   * 弹窗开关状态变更回调
   */
  onOpenChange: (open: boolean) => void
  /**
   * 用户确认回调（保存到 localStorage）
   */
  onConfirm: () => void
}
```

### 组件实现

**useRiskAlert Hook:**
```typescript
// web/src/components/sector-classification/useRiskAlert.ts
'use client'

import { useState, useEffect } from 'react'

const STORAGE_KEY = 'riskAlertAcknowledged'

export interface UseRiskAlertReturn {
  open: boolean
  setOpen: (open: boolean) => void
  handleConfirm: () => void
  hasAcknowledged: boolean
}

export function useRiskAlert(): UseRiskAlertReturn {
  const [open, setOpen] = useState(false)
  const [hasAcknowledged, setHasAcknowledged] = useState(false)

  useEffect(() => {
    // 检查用户是否已确认
    const acknowledged = localStorage.getItem(STORAGE_KEY) === 'true'
    setHasAcknowledged(acknowledged)

    // 如果未确认，显示弹窗
    if (!acknowledged) {
      setOpen(true)
    }
  }, [])

  const handleConfirm = () => {
    // 保存确认状态
    localStorage.setItem(STORAGE_KEY, 'true')
    setHasAcknowledged(true)
    // 关闭弹窗
    setOpen(false)
  }

  return {
    open,
    setOpen,
    handleConfirm,
    hasAcknowledged,
  }
}
```

**RiskAlertDialog 组件:**
```typescript
// web/src/components/sector-classification/RiskAlertDialog.tsx
'use client'

import { AlertTriangle } from 'lucide-react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import type { RiskAlertDialogProps } from './RiskAlertDialog.types'

export function RiskAlertDialog({
  open,
  onOpenChange,
  onConfirm,
}: RiskAlertDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            <AlertDialogTitle>重要提示</AlertDialogTitle>
          </div>
          <AlertDialogDescription asChild>
            <div className="space-y-3 py-4">
              <p className="text-sm">
                本功能提供的板块分类数据仅供参考，不构成任何投资建议。
              </p>
              <p className="text-sm">
                股票市场有风险，投资需谨慎。
              </p>
              <p className="text-sm">
                过往表现不代表未来收益。
              </p>
              <p className="text-sm">
                请根据自己的风险承受能力和投资目标做出独立决策。
              </p>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogAction onClick={onConfirm}>
            我已知晓并理解
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
```

**类型定义文件:**
```typescript
// web/src/components/sector-classification/RiskAlertDialog.types.ts
export interface RiskAlertDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
}
```

### 页面集成

**page.tsx 集成:**
```typescript
// web/src/app/dashboard/sector-classification/page.tsx
'use client'

import { DashboardLayout, DashboardHeader } from '@/components/dashboard'
import { useAuth } from '@/contexts/AuthContext'
import {
  ClassificationTable,
  UpdateTimeDisplay,
  Disclaimer,
  HelpDialog,
  HelpButton,
  RiskAlertDialog,
  useRiskAlert,
} from '@/components/sector-classification'
import { PAGE_TEXT } from './page.constants'

export default function SectorClassificationPage() {
  const { isAuthenticated, isLoading } = useAuth()
  const { helpOpen, setHelpOpen } = useHelpDialog() // 如果有
  const { open: riskAlertOpen, setOpen: setRiskAlertOpen, handleConfirm: handleRiskConfirm } = useRiskAlert()

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
        {/* 现有内容 */}
        {/* ... */}
      </div>

      {/* 帮助弹窗 */}
      <HelpDialog open={helpOpen} onOpenChange={setHelpOpen} />

      {/* 风险提示弹窗 */}
      <RiskAlertDialog
        open={riskAlertOpen}
        onOpenChange={setRiskAlertOpen}
        onConfirm={handleRiskConfirm}
      />
    </DashboardLayout>
  )
}
```

### 组件导出更新

**sector-classification/index.ts:**
```typescript
// web/src/components/sector-classification/index.ts

// 风险提示弹窗
export { RiskAlertDialog } from './RiskAlertDialog'
export type { RiskAlertDialogProps } from './RiskAlertDialog.types'
export { useRiskAlert } from './useRiskAlert'

// 其他组件导出...
export { Disclaimer } from '@/components/ui/Disclaimer'
export { HelpDialog } from './HelpDialog'
export { HelpButton } from './HelpButton'
export { ClassificationTable } from './ClassificationTable'
// ...
```

### 测试要求

**useRiskAlert Hook 测试:**
```typescript
// web/tests/components/sector-classification/useRiskAlert.test.ts
import { renderHook, act } from '@testing-library/react'
import { useRiskAlert } from '@/components/sector-classification/useRiskAlert'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString()
    },
    clear: () => {
      store = {}
    },
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

describe('useRiskAlert', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('首次访问应该显示弹窗', () => {
    const { result } = renderHook(() => useRiskAlert())

    expect(result.current.open).toBe(true)
    expect(result.current.hasAcknowledged).toBe(false)
  })

  it('已确认后不应该显示弹窗', () => {
    // 设置已确认状态
    localStorage.setItem('riskAlertAcknowledged', 'true')

    const { result } = renderHook(() => useRiskAlert())

    expect(result.current.open).toBe(false)
    expect(result.current.hasAcknowledged).toBe(true)
  })

  it('确认后应该保存到 localStorage 并关闭弹窗', () => {
    const { result } = renderHook(() => useRiskAlert())

    expect(result.current.open).toBe(true)

    act(() => {
      result.current.handleConfirm()
    })

    expect(result.current.open).toBe(false)
    expect(result.current.hasAcknowledged).toBe(true)
    expect(localStorage.getItem('riskAlertAcknowledged')).toBe('true')
  })

  it('应该允许手动关闭弹窗', () => {
    const { result } = renderHook(() => useRiskAlert())

    act(() => {
      result.current.setOpen(false)
    })

    expect(result.current.open).toBe(false)
  })
})
```

**RiskAlertDialog 组件测试:**
```typescript
// web/tests/components/sector-classification/RiskAlertDialog.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { RiskAlertDialog } from '@/components/sector-classification/RiskAlertDialog'

describe('RiskAlertDialog', () => {
  it('当 open 为 true 时应该显示弹窗', () => {
    const handleClose = jest.fn()
    const handleConfirm = jest.fn()

    render(
      <RiskAlertDialog
        open={true}
        onOpenChange={handleClose}
        onConfirm={handleConfirm}
      />
    )

    expect(screen.getByText('重要提示')).toBeInTheDocument()
    expect(screen.getByText(/板块分类数据仅供参考/)).toBeInTheDocument()
  })

  it('当 open 为 false 时不应该显示弹窗', () => {
    const handleClose = jest.fn()
    const handleConfirm = jest.fn()

    render(
      <RiskAlertDialog
        open={false}
        onOpenChange={handleClose}
        onConfirm={handleConfirm}
      />
    )

    expect(screen.queryByText('重要提示')).not.toBeInTheDocument()
  })

  it('应该显示所有风险提示内容', () => {
    const handleClose = jest.fn()
    const handleConfirm = jest.fn()

    render(
      <RiskAlertDialog
        open={true}
        onOpenChange={handleClose}
        onConfirm={handleConfirm}
      />
    )

    expect(screen.getByText(/板块分类数据仅供参考/)).toBeInTheDocument()
    expect(screen.getByText(/股票市场有风险/)).toBeInTheDocument()
    expect(screen.getByText(/过往表现不代表未来收益/)).toBeInTheDocument()
    expect(screen.getByText(/根据自己的风险承受能力/)).toBeInTheDocument()
  })

  it('应该调用 onConfirm 当点击确认按钮', () => {
    const handleClose = jest.fn()
    const handleConfirm = jest.fn()

    render(
      <RiskAlertDialog
        open={true}
        onOpenChange={handleClose}
        onConfirm={handleConfirm}
      />
    )

    const confirmButton = screen.getByRole('button', { name: '我已知晓并理解' })
    fireEvent.click(confirmButton)

    expect(handleConfirm).toHaveBeenCalledTimes(1)
  })

  it('应该有警告图标', () => {
    const handleClose = jest.fn()
    const handleConfirm = jest.fn()

    render(
      <RiskAlertDialog
        open={true}
        onOpenChange={handleClose}
        onConfirm={handleConfirm}
      />
    )

    // 检查 AlertTriangle 图标（通过 SVG 元素）
    const icon = document.querySelector('svg')
    expect(icon).toBeInTheDocument()
  })

  it('应该有正确的可访问性属性', () => {
    const handleClose = jest.fn()
    const handleConfirm = jest.fn()

    render(
      <RiskAlertDialog
        open={true}
        onOpenChange={handleClose}
        onConfirm={handleConfirm}
      />
    )

    const dialog = screen.getByRole('alertdialog')
    expect(dialog).toBeInTheDocument()
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })
})
```

**集成测试:**
```typescript
// web/tests/app/dashboard/sector-classification/page.risk-alert-int.test.tsx
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

describe('SectorClassificationPage - Risk Alert Integration', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('首次访问应该显示风险提示弹窗', async () => {
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
      expect(screen.getByText('重要提示')).toBeInTheDocument()
    })
  })

  it('已确认后不应该显示风险提示弹窗', async () => {
    // 设置已确认状态
    localStorage.setItem('riskAlertAcknowledged', 'true')

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
      expect(screen.queryByText('重要提示')).not.toBeInTheDocument()
    })
  })

  it('确认后弹窗应该关闭并保存状态', async () => {
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

    // 等待弹窗显示
    await waitFor(() => {
      expect(screen.getByText('重要提示')).toBeInTheDocument()
    })

    // 点击确认按钮
    const confirmButton = screen.getByRole('button', { name: '我已知晓并理解' })
    confirmButton.click()

    // 验证弹窗关闭
    await waitFor(() => {
      expect(screen.queryByText('重要提示')).not.toBeInTheDocument()
    })

    // 验证 localStorage 已保存
    expect(localStorage.getItem('riskAlertAcknowledged')).toBe('true')
  })
})
```

### Project Structure Notes

**对齐统一项目结构:**
- 组件放在 `components/sector-classification/` 目录
- Hook 文件可以放在组件目录或全局 `hooks/` 目录
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
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4] - Story 3.4 完整验收标准

**PRD 参考:**
- [Source: _bmad-output/planning-artifacts/prd.md#FR12] - FR12: 风险提示和免责声明
- [Source: _bmad-output/planning-artifacts/prd.md#FR23] - FR23: 页面免责声明

### Previous Story Intelligence (Epic 3, Story 3.1)

**从 Story 3.1 学到的经验:**

1. **弹窗组件模式:**
   - 使用 'use client' 指令
   - 使用命名导出 `export function`
   - Props 接口定义清晰（open, onOpenChange）
   - 支持受控模式

2. **shadcn/ui Dialog/AlertDialog 使用:**
   - AlertDialog 比 Dialog 更适合警告场景
   - 内置样式和可访问性支持
   - 自动处理焦点陷阱
   - 支持键盘操作

3. **页面集成模式:**
   - 在 `page.tsx` 中导入组件
   - 使用 hook 管理状态
   - 条件渲染弹窗
   - 确保在页面加载后显示

4. **测试模式:**
   - Mock localStorage
   - 测试组件渲染和交互
   - 测试状态持久化
   - 测试可访问性

**代码审查反馈（Story 3.1）:**
- 使用正确的组件选择器（screen.getByRole）
- 确保 localStorage 在测试中正确 mock
- 完整的 TypeScript 类型定义

**代码模式参考:**
- 查看 `web/src/components/sector-classification/HelpDialog.tsx` 了解弹窗组件模式
- 查看 `web/src/app/dashboard/sector-classification/page.tsx` 了解页面集成

### Previous Story Intelligence (Epic 3, Story 3.3)

**从 Story 3.3 学到的经验:**

1. **免责声明 vs 风险提示的区别:**
   - 免责声明：始终显示在页面底部
   - 风险提示：一次性弹窗，需要确认

2. **合规要求:**
   - 金融科技应用需要明确的风险提示
   - 用户确认记录（localStorage）
   - 清晰的警告样式

3. **组件位置:**
   - UI 组件放在 `components/ui/` 目录
   - Feature 组件放在 `components/sector-classification/` 目录

**代码模式参考:**
- 查看 `web/src/components/ui/Disclaimer.tsx` 了解免责声明实现
- 查看 Story 3.3 了解合规要求

### Critical Implementation Reminders

**🚨 关键规则（不要违反!）:**

1. **'use client' 指令** - 组件和 hook 必须添加
2. **命名导出** - 使用 `export function RiskAlertDialog`，不要使用默认导出
3. **导入路径** - 使用 `@/` 别名，不要使用相对路径
4. **TypeScript strict** - 不要使用 `any` 类型，正确定义 Props 接口
5. **中文文本** - 所有用户可见文本使用中文
6. **AlertDialog 组件** - 使用 shadcn/ui AlertDialog，不要用普通 Dialog
7. **localStorage** - 使用正确的键名 `riskAlertAcknowledged`
8. **一次性显示** - 确认后不再显示（通过 localStorage）
9. **可访问性** - AlertDialog 自动处理，确保正确使用
10. **测试覆盖** - 必须测试 localStorage、首次显示、确认后不显示

**依赖:**
- Epic 2A 完成（页面已就绪）
- Story 3.1 完成（帮助弹窗已创建，可参考模式）
- Story 3.3 完成（免责声明已集成）
- shadcn/ui AlertDialog 组件已安装
- lucide-react 图标库已安装

**后续影响:**
- Epic 3 完成后，所有帮助和合规声明组件已就绪
- 其他投资相关页面可能需要相同的风险提示

### 性能与可访问性要求

**性能要求 (NFR-PERF-001):**
- 弹窗打开速度 < 100ms（客户端渲染）
- localStorage 读取在 useEffect 中完成
- 避免不必要的重渲染

**可访问性要求 (NFR-ACC-001, NFR-ACC-002):**
- AlertDialog 组件自动处理焦点陷阱
- 支持 ESC 键关闭
- 正确的 ARIA 属性（role="alertdialog", aria-modal="true"）
- 键盘导航支持（Tab 键在弹窗内导航）
- 颜色对比度符合 WCAG AA 标准

### 风险提示设计

**视觉设计:**
```
┌─────────────────────────────────────────┐
│ ⚠ 重要提示                      [×]     │
├─────────────────────────────────────────┤
│                                         │
│ 本功能提供的板块分类数据仅供参考，      │
│ 不构成任何投资建议。                     │
│                                         │
│ 股票市场有风险，投资需谨慎。             │
│                                         │
│ 过往表现不代表未来收益。                 │
│                                         │
│ 请根据自己的风险承受能力和投资目标     │
│ 做出独立决策。                           │
│                                         │
│                    [我已知晓并理解]     │
│                                         │
└─────────────────────────────────────────┘
```

**样式规范:**
- 警告图标: AlertTriangle (lucide-react)
- 图标颜色: `text-amber-500`
- 标题: `text-lg font-semibold`
- 内容文本: `text-sm`
- 间距: `space-y-3`
- 按钮: AlertDialogAction（shadcn/ui 内置样式）

**内容规范:**
- 标题: "重要提示"
- 内容: 四条风险提示（与 AC 一致）
- 按钮: "我已知晓并理解"

### 合规要求

**金融科技合规 (FR12, FR23):**
- 风险提示必须明确（不构成投资建议）
- 必须提示投资风险
- 用户必须确认（记录确认状态）
- 一次性显示（避免重复打扰用户）

**法律要求:**
- 明确声明数据仅供参考
- 不构成任何投资建议
- 提示投资风险
- 建议独立决策
- 说明过往表现不代表未来收益

### 实现计划

**优先级 1: 创建 useRiskAlert Hook**
1. 创建 `useRiskAlert.ts` hook
2. 实现 localStorage 读取逻辑
3. 实现确认状态保存逻辑
4. 导出类型和 hook

**优先级 2: 创建风险提示弹窗组件**
1. 创建 `RiskAlertDialog.tsx` 组件
2. 创建 `RiskAlertDialog.types.ts` 类型
3. 集成 shadcn/ui AlertDialog
4. 添加警告图标和内容

**优先级 3: 集成到页面**
1. 在 `page.tsx` 中导入组件和 hook
2. 调用 hook 获取状态和控制函数
3. 条件渲染弹窗
4. 处理确认事件

**优先级 4: 更新组件导出**
1. 在 `index.ts` 中添加导出
2. 验证导出路径正确

**优先级 5: 创建测试**
1. 测试 useRiskAlert hook（localStorage）
2. 测试 RiskAlertDialog 组件
3. 测试页面集成
4. 测试可访问性

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

#### 2026-01-26 - Story 创建完成

#### 2026-01-26 - Story 实现完成

**已实现功能:**
- ✅ 创建 RiskAlertDialog 组件（使用 shadcn/ui AlertDialog）
- ✅ 创建 useRiskAlert hook（管理 localStorage 状态）
- ✅ 创建 TypeScript 类型定义（RiskAlertDialogProps, UseRiskAlertReturn）
- ✅ 集成到页面组件（page.tsx）
- ✅ 更新组件导出索引（index.ts）
- ✅ 创建 AlertDialog UI 组件（shadcn/ui）
- ✅ 创建测试文件（useRiskAlert.test.ts, RiskAlertDialog.test.tsx）
- ✅ 安装必要依赖（@radix-ui/react-alert-dialog）

**验收标准实现:**
- ✅ 显示风险提示弹窗（一次性）
- ✅ 弹窗标题为"重要提示"
- ✅ 弹窗包含四条风险提示内容
- ✅ 弹窗底部有"我已知晓并理解"按钮
- ✅ 点击按钮后关闭弹窗
- ✅ 使用 localStorage 记录确认状态
- ✅ 使用 shadcn/ui AlertDialog 组件

**代码质量验证:**
- ✅ TypeScript 类型检查通过（无错误）
- ✅ ESLint 检查通过（无警告）
- ✅ 遵循项目命名规范（命名导出、'use client'）
- ✅ 使用正确的导入路径（@/ 别名）
- ✅ 完整的 TypeScript 类型定义
- ✅ 可访问性支持（ARIA 属性、键盘导航）

**技术实现亮点:**
- 自定义 hook 管理状态（useRiskAlert）
- localStorage 持久化用户确认状态
- 一次性显示逻辑（首次访问显示，确认后不显示）
- shadcn/ui AlertDialog 模式
- 完整的可访问性支持（role="alertdialog", aria-modal="true"）
- 符合金融科技合规要求
- 清晰区分风险提示和免责声明

**实现计划:**
1. 创建 useRiskAlert hook（管理 localStorage 状态）
2. 创建 RiskAlertDialog 组件（使用 shadcn/ui AlertDialog）
3. 集成到页面组件（page.tsx）
4. 更新组件导出索引（index.ts）
5. 创建测试（Hook、组件、集成测试）
6. 验证 localStorage 持久化
7. 验证一次性显示逻辑

**验收标准:**
- ✅ 显示风险提示弹窗（一次性）
- ✅ 弹窗标题为"重要提示"
- ✅ 弹窗包含四条风险提示内容
- ✅ 弹窗底部有"我已知晓并理解"按钮
- ✅ 点击按钮后关闭弹窗
- ✅ 使用 localStorage 记录确认状态
- ✅ 使用 shadcn/ui AlertDialog 组件

**技术亮点:**
- 自定义 hook 管理状态（useRiskAlert）
- localStorage 持久化用户确认状态
- 一次性显示逻辑（首次访问显示，确认后不显示）
- 完整的 TypeScript 类型定义
- 遵循 shadcn/ui AlertDialog 模式
- 完整的可访问性支持（ARIA 属性、键盘导航）
- 符合金融科技合规要求
- 清晰区分风险提示和免责声明

**Epic 3 进度:**
- ✅ Story 3.1: 创建帮助弹窗组件 - done
- ✅ Story 3.2: 添加分类级别图例说明 - done
- ✅ Story 3.3: 集成免责声明到所有页面 - done
- ⏸️ Story 3.4: 创建风险提示弹窗 - ready-for-dev

**Epic 3 完成度:** 75% (3/4 stories done, 1 ready-for-dev)

### File List

**已创建的文件:**
- `web/src/components/sector-classification/RiskAlertDialog.tsx` - 风险提示弹窗组件
- `web/src/components/sector-classification/RiskAlertDialog.types.ts` - 类型定义
- `web/src/components/sector-classification/useRiskAlert.ts` - 状态管理 hook
- `web/src/components/ui/alert-dialog.tsx` - shadcn/ui AlertDialog 组件
- `web/tests/components/sector-classification/useRiskAlert.test.ts` - Hook 测试
- `web/tests/components/sector-classification/RiskAlertDialog.test.tsx` - 组件测试

**已修改的文件:**
- `web/src/components/sector-classification/index.ts` - 添加导出
- `web/src/app/dashboard/sector-classification/page.tsx` - 集成弹窗

**依赖文件（已存在）:**
- `web/src/components/sector-classification/HelpDialog.tsx` - 弹窗模式参考
- `web/src/components/ui/Disclaimer.tsx` - 免责声明参考

## Change Log

### 2026-01-26

- 创建 Story 3.4 文档
- 定义风险提示弹窗组件规范
- 定义 localStorage 持久化逻辑
- 定义一次性显示逻辑
- 定义页面集成方案
- 定义测试策略
- 定义合规要求
- 区分风险提示和免责声明
- Story 状态: backlog → ready-for-dev
- **实现完成:**
  - 创建 RiskAlertDialog 组件
  - 创建 useRiskAlert hook
  - 创建类型定义文件
  - 创建 AlertDialog UI 组件
  - 集成到页面组件
  - 更新组件导出
  - 创建测试文件
  - 安装必要依赖
  - 通过 TypeScript 类型检查
  - 通过 ESLint 检查
  - 所有任务和子任务已完成
- Story 状态: ready-for-dev → review
