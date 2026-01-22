# Story 2B.4: 实现键盘导航支持

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 投资者,
I want 使用键盘导航表格,
So that 我可以更高效地浏览数据。

## Acceptance Criteria

**Given** 用户已查看分类表格
**When** 用户按 Tab 键
**Then** 焦点在表格和搜索框之间切换
**When** 焦点在表格上时
**Then** 用户可以使用方向键（↑/↓/←/→）在单元格间导航
**And** 当前聚焦的单元格高亮显示
**When** 用户按 Enter 键选中某行
**Then** 可以查看该板块的详细信息（预留功能）
**And** 符合可访问性要求（NFR-ACC-002）

## Tasks / Subtasks

- [x] Task 1: 创建键盘导航状态管理 (AC: #)
  - [x] Subtask 1.1: 创建 `web/src/stores/useKeyboardNavigation.ts`
  - [x] Subtask 1.2: 定义焦点状态接口（focusedCell, focusedRow）
  - [x] Subtask 1.3: 实现方向键导航动作
  - [x] Subtask 1.4: 实现设置焦点动作

- [x] Task 2: 修改 ClassificationTable 组件支持键盘导航 (AC: #)
  - [x] Subtask 2.1: 添加 `tabIndex={0}` 使表格可聚焦
  - [x] Subtask 2.2: 添加键盘事件监听器（onKeyDown）
  - [x] Subtask 2.3: 处理方向键（↑/↓/←/→）
  - [x] Subtask 2.4: 处理 Enter 键选中行
  - [x] Subtask 2.5: 处理 Escape 键退出焦点

- [x] Task 3: 实现单元格焦点高亮 (AC: #)
  - [x] Subtask 3.1: 创建焦点样式（背景色、边框）
  - [x] Subtask 3.2: 根据 focusedCell 状态应用样式
  - [x] Subtask 3.3: 确保颜色对比度符合可访问性要求

- [x] Task 4: 实现行导航逻辑 (AC: #)
  - [x] Subtask 4.1: 实现上/下键行间导航
  - [x] Subtask 4.2: 实现左/右键单元格导航
  - [x] Subtask 4.3: 处理边界情况（第一行、最后一行）
  - [x] Subtask 4.4: 支持搜索/排序后的数据导航

- [x] Task 5: 实现行选中功能 (AC: #)
  - [x] Subtask 5.1: 定义行选中回调接口
  - [x] Subtask 5.2: 处理 Enter 键触发回调
  - [x] Subtask 5.3: 预留详细信息查看功能（可选实现）

- [x] Task 6: 集成搜索框焦点 (AC: #)
  - [x] Subtask 6.1: 确保 Tab 键在搜索框和表格间切换
  - [x] Subtask 6.2: 确保焦点顺序符合逻辑
  - [x] Subtask 6.3: 验证刷新按钮也在焦点顺序中

- [x] Task 7: 创建测试 (AC: #)
  - [x] Subtask 7.1: 测试键盘导航状态管理
  - [x] Subtask 7.2: 测试方向键导航
  - [x] Subtask 7.3: 测试单元格焦点高亮
  - [x] Subtask 7.4: 测试行选中功能
  - [x] Subtask 7.5: 测试 Tab 键焦点切换

## Dev Notes

### Epic 2B 完整上下文

**Epic 目标:** 在基础分类展示之上，添加排序、搜索、刷新等高级交互功能，提升用户体验。

**FRs 覆盖:**
- 无直接 FR 覆盖（用户体验增强）

**NFRs 相关:**
- NFR-ACC-002: 系统应提供键盘导航支持

**依赖关系:**
- 依赖 Epic 2A 完成（基础分类展示已实现）
- 依赖 Story 2A.2 完成（表格组件已创建）
- 依赖 Story 2B.1 完成（排序功能已实现）
- 依赖 Story 2B.2 完成（搜索功能已实现）
- 依赖 Story 2B.3 完成（刷新按钮已实现）

**Epic 2B 最后一个 Story！**

### 架构模式与约束

**前端技术栈:**
- Next.js 16.1.1 (使用 App Router)
- React 19.2.0 (需要 'use client' 指令)
- TypeScript 5 (strict mode)
- Tailwind CSS 4.x
- Zustand 5.0.9 (状态管理)

**状态管理策略:**
| 状态类型 | 使用方案 | 原因 |
|---------|----------|------|
| 全局状态（分类数据） | Redux Toolkit | 与现有架构一致 |
| 排序状态 | Zustand | Story 2B.1 已实现 |
| 搜索状态 | Zustand | Story 2B.2 已实现 |
| 键盘导航状态 | Zustand | 组件本地 UI 状态 |

**键盘导航状态设计:**
```typescript
interface KeyboardNavigationState {
  focusedCell: { rowIndex: number; cellIndex: number } | null
  focusedRow: number | null
  setFocusedCell: (row: number, cell: number) => void
  clearFocus: () => void
  moveUp: () => void
  moveDown: (maxRows: number) => void
  moveLeft: (maxCells: number) => void
  moveRight: (maxCells: number) => void
}
```

### 项目结构规范

**文件结构:**
```
web/src/
├── stores/
│   ├── useKeyboardNavigation.ts                 # 新增：键盘导航状态管理
│   └── index.ts                                 # 修改：导出 store
├── components/sector-classification/
│   ├── ClassificationTable.tsx                  # 修改：添加键盘导航
│   └── index.ts                                 # 修改：导出类型
└── tests/
    ├── stores/
    │   └── useKeyboardNavigation.test.ts         # 新增：store 测试
    └── components/
        └── sector-classification/
            └── ClassificationTable.test.tsx      # 修改：添加键盘导航测试
```

**命名约定:**
- Store 文件: `usePascalCase.ts` (如 `useKeyboardNavigation.ts`)
- 组件文件: `PascalCase.tsx`
- 测试文件: `*.test.tsx`

### TypeScript 类型定义

**键盘导航状态类型:**
```typescript
// web/src/stores/useKeyboardNavigation.ts
export interface FocusedCell {
  rowIndex: number
  cellIndex: number
}

export interface KeyboardNavigationState {
  focusedCell: FocusedCell | null
  setFocusedCell: (rowIndex: number, cellIndex: number) => void
  clearFocus: () => void
  moveUp: () => void
  moveDown: (maxRows: number) => void
  moveLeft: (maxCells: number) => void
  moveRight: (maxCells: number) => void
}
```

### Zustand Store 实现

**键盘导航 Store 实现:**
```typescript
// web/src/stores/useKeyboardNavigation.ts
import { create } from 'zustand'
import type { KeyboardNavigationState, FocusedCell } from './types'

export const useKeyboardNavigation = create<KeyboardNavigationState>((set, get) => ({
  focusedCell: null,

  setFocusedCell: (rowIndex, cellIndex) =>
    set({ focusedCell: { rowIndex, cellIndex } }),

  clearFocus: () =>
    set({ focusedCell: null }),

  moveUp: () => {
    const { focusedCell } = get()
    if (!focusedCell || focusedCell.rowIndex === 0) return
    set({
      focusedCell: {
        ...focusedCell,
        rowIndex: focusedCell.rowIndex - 1,
      },
    })
  },

  moveDown: (maxRows) => {
    const { focusedCell } = get()
    if (!focusedCell || focusedCell.rowIndex >= maxRows - 1) return
    set({
      focusedCell: {
        ...focusedCell,
        rowIndex: focusedCell.rowIndex + 1,
      },
    })
  },

  moveLeft: (maxCells) => {
    const { focusedCell } = get()
    if (!focusedCell || focusedCell.cellIndex === 0) return
    set({
      focusedCell: {
        ...focusedCell,
        cellIndex: focusedCell.cellIndex - 1,
      },
    })
  },

  moveRight: (maxCells) => {
    const { focusedCell } = get()
    if (!focusedCell || focusedCell.cellIndex >= maxCells - 1) return
    set({
      focusedCell: {
        ...focusedCell,
        cellIndex: focusedCell.cellIndex + 1,
      },
    })
  },
}))
```

### ClassificationTable 组件修改

**键盘导航集成:**
```typescript
// web/src/components/sector-classification/ClassificationTable.tsx (修改)
'use client'

import { useCallback, useEffect, useRef } from 'react'
import { useKeyboardNavigation } from '@/stores/useKeyboardNavigation'
import type { SectorClassification } from '@/types/sector-classification'

interface ClassificationTableProps {
  data: SectorClassification[]
  onRowSelect?: (sector: SectorClassification) => void
  // ... 其他 props
}

export function ClassificationTable({
  data,
  onRowSelect,
  ...props
}: ClassificationTableProps) {
  const tableRef = useRef<HTMLTableElement>(null)
  const {
    focusedCell,
    setFocusedCell,
    clearFocus,
    moveUp,
    moveDown,
    moveLeft,
    moveRight,
  } = useKeyboardNavigation()

  // 列数（固定：板块名称、分类级别、状态、当前价格、涨跌幅）
  const COLUMN_COUNT = 5

  // 键盘事件处理
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTableElement>) => {
      // 只在焦点在表格时处理
      if (!focusedCell) return

      switch (e.key) {
        case 'ArrowUp':
          e.preventDefault()
          moveUp()
          break
        case 'ArrowDown':
          e.preventDefault()
          moveDown(data.length)
          break
        case 'ArrowLeft':
          e.preventDefault()
          moveLeft(COLUMN_COUNT)
          break
        case 'ArrowRight':
          e.preventDefault()
          moveRight(COLUMN_COUNT)
          break
        case 'Enter':
          e.preventDefault()
          // Enter 键选中当前行
          if (focusedCell && onRowSelect) {
            const selectedSector = data[focusedCell.rowIndex]
            if (selectedSector) {
              onRowSelect(selectedSector)
            }
          }
          break
        case 'Escape':
          e.preventDefault()
          clearFocus()
          break
      }
    },
    [focusedCell, data, moveUp, moveDown, moveLeft, moveRight, clearFocus, onRowSelect]
  )

  // 处理单元格点击
  const handleCellClick = useCallback(
    (rowIndex: number, cellIndex: number) => {
      setFocusedCell(rowIndex, cellIndex)
    },
    [setFocusedCell]
  )

  // 处理行点击
  const handleRowClick = useCallback(
    (sector: SectorClassification, rowIndex: number) => {
      setFocusedCell(rowIndex, 0) // 聚焦到行的第一个单元格
      if (onRowSelect) {
        onRowSelect(sector)
      }
    },
    [setFocusedCell, onRowSelect]
  )

  // 处理焦点丢失
  useEffect(() => {
    const handleBlur = (e: FocusEvent) => {
      // 如果焦点移出表格，清除焦点状态
      if (!tableRef.current?.contains(e.relatedTarget as Node)) {
        clearFocus()
      }
    }

    const table = tableRef.current
    if (table) {
      table.addEventListener('blur', handleBlur, { capture: true })
      return () => {
        table.removeEventListener('blur', handleBlur, { capture: true })
      }
    }
  }, [clearFocus])

  return (
    <Table
      ref={tableRef}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      className="focus-visible:outline-none"
    >
      {/* 表头 */}
      <TableHeader>
        <TableRow>
          <TableHead>板块名称</TableHead>
          <TableHead>分类级别</TableHead>
          <TableHead>状态</TableHead>
          <TableHead>当前价格</TableHead>
          <TableHead>涨跌幅(%)</TableHead>
        </TableRow>
      </TableHeader>

      {/* 表体 */}
      <TableBody>
        {data.map((item, rowIndex) => (
          <TableRow
            key={item.id}
            className={
              focusedCell?.rowIndex === rowIndex
                ? 'bg-blue-50 focus:bg-blue-100'
                : ''
            }
            onClick={() => handleRowClick(item, rowIndex)}
          >
            {/* 板块名称 */}
            <TableCell
              className={
                focusedCell?.rowIndex === rowIndex && focusedCell?.cellIndex === 0
                  ? 'ring-2 ring-blue-500 ring-inset'
                  : ''
              }
              onClick={() => handleCellClick(rowIndex, 0)}
            >
              {item.sector_name}
            </TableCell>

            {/* 分类级别 */}
            <TableCell
              className={
                focusedCell?.rowIndex === rowIndex && focusedCell?.cellIndex === 1
                  ? 'ring-2 ring-blue-500 ring-inset'
                  : ''
              }
              onClick={() => handleCellClick(rowIndex, 1)}
            >
              {/* 分类级别徽章 */}
            </TableCell>

            {/* 状态 */}
            <TableCell
              className={
                focusedCell?.rowIndex === rowIndex && focusedCell?.cellIndex === 2
                  ? 'ring-2 ring-blue-500 ring-inset'
                  : ''
              }
              onClick={() => handleCellClick(rowIndex, 2)}
            >
              {/* 状态图标 */}
            </TableCell>

            {/* 当前价格 */}
            <TableCell
              className={
                focusedCell?.rowIndex === rowIndex && focusedCell?.cellIndex === 3
                  ? 'ring-2 ring-blue-500 ring-inset'
                  : ''
              }
              onClick={() => handleCellClick(rowIndex, 3)}
            >
              {item.current_price.toFixed(2)}
            </TableCell>

            {/* 涨跌幅 */}
            <TableCell
              className={
                focusedCell?.rowIndex === rowIndex && focusedCell?.cellIndex === 4
                  ? 'ring-2 ring-blue-500 ring-inset'
                  : ''
              }
              onClick={() => handleCellClick(rowIndex, 4)}
            >
              {/* 涨跌幅显示 */}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
```

### 可访问性增强

**ARIA 属性和语义化:**
```typescript
<Table
  ref={tableRef}
  tabIndex={0}
  role="grid"
  aria-label="板块分类表格"
  onKeyDown={handleKeyDown}
>
  {/* 表头 */}
  <TableHeader>
    <TableRow>
      <TableHead scope="col" aria-label="板块名称">板块名称</TableHead>
      <TableHead scope="col" aria-label="分类级别">分类级别</TableHead>
      {/* ... */}
    </TableRow>
  </TableHeader>

  {/* 表体 */}
  <TableBody>
    {data.map((item, rowIndex) => (
      <TableRow
        key={item.id}
        role="row"
        aria-rowindex={rowIndex + 1}
        aria-selected={focusedCell?.rowIndex === rowIndex}
        className={focusedCell?.rowIndex === rowIndex ? 'bg-blue-50' : ''}
      >
        <TableCell
          role="gridcell"
          aria-colindex={1}
          tabIndex={focusedCell?.rowIndex === rowIndex && focusedCell?.cellIndex === 0 ? 0 : -1}
        >
          {item.sector_name}
        </TableCell>
        {/* ... */}
      </TableRow>
    ))}
  </TableBody>
</Table>
```

### SearchBar 焦点集成

**确保 Tab 键顺序:**
```typescript
// 页面组件中的焦点顺序
<div className="space-y-6">
  {/* 工具栏：搜索和刷新 */}
  <div className="flex items-center justify-between gap-4" role="toolbar" aria-label="搜索和刷新工具栏">
    <SearchBar
      className="flex-1"
      // 确保 SearchBar 有正确的 tabIndex
    />
    <RefreshButton />
  </div>

  {/* 表格 */}
  <ClassificationTable
    data={classifications}
    onRowSelect={handleRowSelect}
    tabIndex={0} // 确保 Table 可聚焦
  />

  {/* 免责声明 */}
  <Disclaimer showSeparator={true} />
</div>
```

**SearchBar 组件调整:**
```typescript
// web/src/components/sector-classification/SearchBar.tsx (确保焦点正确)
export function SearchBar({ placeholder, className }: SearchBarProps) {
  return (
    <div className={`relative ${className}`}>
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
      <Input
        type="text"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        placeholder={placeholder}
        className="pl-10 pr-10"
        aria-label="搜索板块名称"
        tabIndex={0} // 确保可聚焦
      />
      {/* ... */}
    </div>
  )
}
```

### Testing Standards Summary

**测试要求:**
- 测试键盘导航状态管理
- 测试方向键导航（↑/↓/←/→）
- 测试单元格焦点高亮
- 测试行选中功能（Enter 键）
- 测试 Tab 键焦点切换
- 测试 Escape 键清除焦点
- 测试边界情况（第一行、最后一行）
- 测试搜索/排序后的数据导航

**Store 测试示例:**
```typescript
// web/tests/stores/useKeyboardNavigation.test.ts
import { renderHook, act } from '@testing-library/react'
import { useKeyboardNavigation } from '@/stores/useKeyboardNavigation'

describe('useKeyboardNavigation', () => {
  it('应该没有初始焦点', () => {
    const { result } = renderHook(() => useKeyboardNavigation())

    expect(result.current.focusedCell).toBeNull()
  })

  it('应该能够设置焦点', () => {
    const { result } = renderHook(() => useKeyboardNavigation())

    act(() => {
      result.current.setFocusedCell(0, 0)
    })

    expect(result.current.focusedCell).toEqual({ rowIndex: 0, cellIndex: 0 })
  })

  it('应该能够向上移动', () => {
    const { result } = renderHook(() => useKeyboardNavigation())

    act(() => {
      result.current.setFocusedCell(2, 0)
    })
    act(() => {
      result.current.moveUp()
    })

    expect(result.current.focusedCell).toEqual({ rowIndex: 1, cellIndex: 0 })
  })

  it('不应该移动到第一行之上', () => {
    const { result } = renderHook(() => useKeyboardNavigation())

    act(() => {
      result.current.setFocusedCell(0, 0)
    })
    act(() => {
      result.current.moveUp()
    })

    expect(result.current.focusedCell).toEqual({ rowIndex: 0, cellIndex: 0 })
  })

  it('应该能够向下移动', () => {
    const { result } = renderHook(() => useKeyboardNavigation())

    act(() => {
      result.current.setFocusedCell(0, 0)
    })
    act(() => {
      result.current.moveDown(10) // 10 行数据
    })

    expect(result.current.focusedCell).toEqual({ rowIndex: 1, cellIndex: 0 })
  })

  it('不应该移动到最后一行之下', () => {
    const { result } = renderHook(() => useKeyboardNavigation())

    act(() => {
      result.current.setFocusedCell(4, 0)
    })
    act(() => {
      result.current.moveDown(5) // 5 行数据
    })

    expect(result.current.focusedCell).toEqual({ rowIndex: 4, cellIndex: 0 })
  })

  it('应该能够清除焦点', () => {
    const { result } = renderHook(() => useKeyboardNavigation())

    act(() => {
      result.current.setFocusedCell(2, 0)
    })
    expect(result.current.focusedCell).not.toBeNull()

    act(() => {
      result.current.clearFocus()
    })
    expect(result.current.focusedCell).toBeNull()
  })
})
```

### Project Structure Notes

**对齐统一项目结构:**
- Store 放在 `stores/` 目录
- 组件放在 `components/sector-classification/` 目录
- 测试放在 `tests/` 对应目录
- 使用 Zustand 管理组件本地状态
- 遵循 Story 2B.1 和 2B.2 的模式

**检测到的冲突或差异:**
- 无冲突 - 遵循之前 Epic 2B Stories 建立的模式

### References

**架构文档:**
- [Source: _bmad-output/planning-artifacts/architecture.md#State Management Patterns] - 状态管理模式
- [Source: _bmad-output/planning-artifacts/architecture.md#Accessibility Level] - 可访问性要求

**项目上下文:**
- [Source: _bmad-output/planning-artifacts/prd.md#NFR-ACC-002] - 键盘导航支持要求

**Epic 定义:**
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2B] - Epic 2B: 高级交互功能
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2B.4] - Story 2B.4 完整验收标准

### Previous Story Intelligence (Stories 2B.1, 2B.2, 2B.3)

**从之前 Stories 学到的经验:**

1. **Zustand Store 模式 (Story 2B.1, 2B.2):**
   - 使用 `use` 前缀命名 store hook
   - 清晰的状态接口定义
   - 简单的动作函数
   - 易于测试

2. **组件状态集成模式:**
   - 使用 `use` hook 连接 Zustand store
   - 使用 useCallback 优化事件处理
   - 使用 useEffect 处理副作用

3. **可访问性模式 (Story 2B.1, 2B.2, 2B.3):**
   - 添加 aria-label 描述
   - 添加正确的 role 属性
   - 支持键盘操作（Tab, Enter, Escape）
   - 使用焦点样式

**代码模式参考:**
- 查看 `web/src/stores/useSectorClassificationSort.ts` 了解 Zustand store 模式
- 查看 `web/src/stores/useSectorClassificationSearch.ts` 了解 Zustand store 模式
- 查看 `web/src/components/sector-classification/ClassificationTable.tsx` 了解组件结构

### Critical Implementation Reminders

**🚨 关键规则（不要违反!）:**

1. **'use client' 指令** - 组件使用 hooks 必须添加
2. **命名导出** - 使用 `export function`，不要使用默认导出
3. **导入路径** - 使用 `@/` 别名，不要使用相对路径
4. **Zustand store** - 用于键盘导航状态
5. **TypeScript strict** - 不要使用 `any` 类型
6. **可访问性** - 添加正确的 aria 属性和 role
7. **焦点样式** - 清晰的焦点高亮显示
8. **边界处理** - 处理第一行、最后一行边界情况
9. **Tab 键顺序** - 确保正确的焦点顺序
10. **测试覆盖** - 必须测试键盘导航功能

**依赖:**
- Epic 2A 完成（基础分类展示已实现）
- Story 2A.2 完成（表格组件已创建）
- Story 2B.1 完成（排序功能已实现）
- Story 2B.2 完成（搜索功能已实现）
- Story 2B.3 完成（刷新按钮已实现）
- Zustand 5.0.9 已安装

**后续影响:**
- Epic 2B 最后一个 Story！
- 完成后 Epic 2B 可以进行回顾
- 预留行选中回调接口（详细信息查看功能可选实现）

### 性能与可访问性要求

**性能要求:**
- 键盘事件响应及时
- 使用 useCallback 优化事件处理
- 使用 useEffect 正确处理副作用

**可访问性要求 (NFR-ACC-002):**
- Tab 键在搜索框、刷新按钮、表格间切换
- 方向键在单元格间导航
- Enter 键选中行
- Escape 键退出焦点
- 焦点样式清晰可见（颜色对比度符合标准）
- ARIA 属性完整

**键盘支持:**
- Tab: 焦点切换
- Shift + Tab: 反向焦点切换
- ↑/↓: 行间导航
- ←/→: 单元格导航
- Enter: 选中行
- Escape: 退出焦点

### 键盘导航功能设计

**导航特性:**
1. **Tab 键切换** - 在搜索框、刷新按钮、表格间切换
2. **方向键导航** - 在单元格间移动
3. **焦点高亮** - 当前聚焦的单元格清晰显示
4. **行选中** - Enter 键触发行选中回调
5. **边界处理** - 不移出表格范围
6. **焦点丢失** - 失焦时自动清除焦点状态

**焦点样式:**
- 行高亮：`bg-blue-50` (淡蓝色背景)
- 单元格聚焦：`ring-2 ring-blue-500 ring-inset` (蓝色边框)
- 焦点顺序：工具栏 → 表格 → 免责声明

**预留功能:**
- `onRowSelect` 回调接口
- 可用于未来实现详细信息查看
- 可用于导航到详情页面
- 可用于显示详情弹窗

### Epic 2B 完成后

**Epic 2B 包含的 Stories:**
1. ✅ Story 2B.1: 表格排序功能
2. ✅ Story 2B.2: 搜索功能
3. ✅ Story 2B.3: 手动刷新按钮
4. ⏳ Story 2B.4: 键盘导航支持

**Epic 2B 完成度:** 75% (3/4 stories done)

**完成后可执行:**
- 运行 Epic 2B 回顾 (epic-2b-retrospective)
- 将 epic-2b 状态更新为 "done"
- 继续下一个 Epic (Epic 3 或 Epic 4)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

#### 2026-01-22 - Story 创建完成

**Story 内容:**
- ✅ 完整的用户故事定义
- ✅ BDD 格式的验收标准
- ✅ 详细的任务分解（7个任务，30+子任务）
- ✅ 完整的开发者上下文和实现指南
- ✅ Zustand store 设计方案
- ✅ 键盘导航逻辑实现代码
- ✅ 可访问性增强方案
- ✅ 测试策略

**实现计划:**
1. 创建 Zustand store (`useKeyboardNavigation.ts`)
2. 修改 ClassificationTable 组件添加键盘导航
3. 实现方向键导航逻辑
4. 实现单元格焦点高亮
5. 实现行选中功能（预留接口）
6. 确保 Tab 键顺序正确
7. 创建测试

**验收标准:**
- ✅ Tab 键在搜索框、刷新按钮、表格间切换
- ✅ 方向键在单元格间导航（↑/↓/←/→）
- ✅ 当前聚焦的单元格高亮显示
- ✅ Enter 键选中行（预留详细信息查看）
- ✅ 符合可访问性要求（NFR-ACC-002）

**技术亮点:**
- Zustand 轻量级状态管理
- 完整的键盘导航支持
- 清晰的焦点视觉反馈
- 符合 WCAG 可访问性标准
- 预留行选中回调接口
- 边界情况处理完善

**Epic 2B 进度:**
- ✅ Story 2B.1: 表格排序功能 - done
- ✅ Story 2B.2: 搜索功能 - done
- ✅ Story 2B.3: 手动刷新按钮 - done
- ⏳ Story 2B.4: 键盘导航支持 - ready-for-dev

#### 2026-01-22 - Story 实现完成

**实现完成内容:**

**Task 1: 创建键盘导航状态管理** ✅
- 创建 `web/src/stores/useKeyboardNavigation.ts`
- 定义 `FocusedCell` 和 `KeyboardNavigationState` 接口
- 实现方向键导航动作（moveUp, moveDown, moveLeft, moveRight）
- 实现焦点管理动作（setFocusedCell, clearFocus）
- 边界处理：第一行、最后一行、第一列、最后一列

**Task 2: 修改 ClassificationTable 组件支持键盘导航** ✅
- 添加 `tabIndex={0}` 使表格可聚焦
- 添加 `ref={tableRef}` 引用表格 DOM
- 添加 `onKeyDown` 事件监听器
- 处理方向键（↑/↓/←/→）
- 处理 Enter 键选中行
- 处理 Escape 键退出焦点
- 添加焦点丢失监听，失焦时清除焦点状态

**Task 3: 实现单元格焦点高亮** ✅
- 聚焦行样式：`bg-blue-50`（淡蓝色背景）
- 聚焦单元格样式：`ring-2 ring-blue-500 ring-inset`（蓝色边框）
- 根据 `focusedCell` 状态动态应用样式
- 颜色对比度符合 WCAG AA 标准

**Task 4: 实现行导航逻辑** ✅
- 上/下键行间导航（带边界检查）
- 左/右键单元格导航（带边界检查）
- 边界情况处理：不超出表格范围
- 支持搜索/排序后的数据导航（使用 filteredAndSortedData.length）

**Task 5: 实现行选中功能** ✅
- 添加 `onRowSelect` 回调接口
- Enter 键触发回调，传递选中的 SectorClassification 对象
- 预留详细信息查看功能接口（未来可扩展）

**Task 6: 集成搜索框焦点** ✅
- SearchBar 已有正确的 aria-label 和 tabIndex
- RefreshButton 已有正确的 aria-label
- 页面 DOM 顺序：SearchBar → RefreshButton → ClassificationTable
- Tab 键顺序符合逻辑

**Task 7: 创建测试** ✅
- 创建 `web/tests/stores/useKeyboardNavigation.test.ts`
  - 测试初始状态
  - 测试设置和清除焦点
  - 测试四个方向键导航
  - 测试边界情况
  - 测试组合导航
- 创建 `web/tests/components/sector-classification/ClassificationTable.test.tsx`
  - 测试表格可聚焦性
  - 测试方向键导航
  - 测试 Enter 键行选中
  - 测试 Escape 键清除焦点
  - 测试焦点高亮显示
  - 测试单元格点击聚焦
  - 测试 ARIA 属性

**验收标准验证:**
- ✅ Tab 键在搜索框、刷新按钮、表格间切换
- ✅ 方向键在单元格间导航（↑/↓/←/→）
- ✅ 当前聚焦的单元格高亮显示（蓝色背景 + 蓝色边框）
- ✅ Enter 键选中行（通过 onRowSelect 回调）
- ✅ 符合可访问性要求（NFR-ACC-002）：role、aria-label、aria-rowindex、aria-colindex、aria-selected 属性完整

**代码质量:**
- TypeScript strict mode 通过
- 遵循项目命名约定
- 遵循 Zustand store 模式
- 使用 useCallback 优化性能
- 完整的 JSDoc 注释

**Epic 2B 完成！** 🎉
- ✅ Story 2B.1: 表格排序功能 - done
- ✅ Story 2B.2: 搜索功能 - done
- ✅ Story 2B.3: 手动刷新按钮 - done
- ✅ Story 2B.4: 键盘导航支持 - review

**Epic 2B 完成度:** 100% (4/4 stories implemented)
- ⏳ Story 2B.4: 键盘导航支持 - ready-for-dev

**Epic 2B 完成度:** 75% (3/4 stories done)

**这是 Epic 2B 的最后一个 Story！**

### File List

**新增文件:**
- `web/src/stores/useKeyboardNavigation.ts` - 键盘导航状态管理 (Zustand)
- `web/tests/stores/useKeyboardNavigation.test.ts` - store 测试
- `web/tests/components/sector-classification/ClassificationTable.test.tsx` - 键盘导航测试

**修改文件:**
- `web/src/components/sector-classification/ClassificationTable.tsx` - 添加键盘导航支持
- `web/tests/stores/useKeyboardNavigation.test.ts` - 修复 Zustand store 状态重置
- `web/tests/components/sector-classification/ClassificationTable.test.tsx` - 添加 Tab 键焦点切换测试
- `_bmad-output/implementation-artifacts/sprint-status.yaml` - 由代码审查工作流更新状态

**依赖文件（已存在）:**
- `web/src/store/slices/sectorClassificationSlice.ts` - Redux 全局状态
- `web/src/types/sector-classification.ts` - 类型定义 (Story 2A.2)
- `web/src/stores/useSectorClassificationSort.ts` - 排序状态 (Story 2B.1)
- `web/src/stores/useSectorClassificationSearch.ts` - 搜索状态 (Story 2B.2)
- `web/src/components/sector-classification/SearchBar.tsx` - 搜索框 (Story 2B.2)
- `web/src/components/sector-classification/RefreshButton.tsx` - 刷新按钮 (Story 2B.3)

## Change Log

### 2026-01-22

- 创建 Story 2B.4 文档
- 定义键盘导航功能需求
- 定义 Zustand 状态管理方案
- 定义键盘导航逻辑实现方案
- 定义可访问性增强方案
- 定义焦点样式和边界处理
- 定义测试策略
- Story 状态: backlog → ready-for-dev

### 2026-01-22

- 实现键盘导航状态管理 (`useKeyboardNavigation.ts`)
- 修改 ClassificationTable 组件支持键盘导航
- 实现方向键导航（↑/↓/←/→）
- 实现焦点高亮样式（蓝色背景 + 蓝色边框）
- 实现 Enter 键行选中功能
- 实现 Escape 键清除焦点
- 创建键盘导航测试
- Story 状态: ready-for-dev → in-progress → review
- **Epic 2B 全部完成！** 🎉

#### 2026-01-22 - 代码审查修复 #1

**修复内容:**
- ✅ 更新 File List 描述以匹配实际实现
- ✅ ClassificationTable.test.tsx 标注为"新增"而非"修改"
- ✅ 移除不存在的 stores/index.ts 修改记录
- ✅ 移除不需要的组件 index.ts 修改记录
- ✅ 添加 sprint-status.yaml 修改记录

**代码质量:**
- ✅ 所有验收标准已实现
- ✅ TypeScript 编译通过
- ✅ ESLint 检查通过
- ✅ 测试覆盖完整（store + 组件）
- ✅ 可访问性属性完整
- **文档问题已修复，代码实现完整！**

#### 2026-01-22 - 代码审查修复 #2（再次审查）

**修复内容:**
- ✅ 修复 Zustand store 状态重置问题
- ✅ 添加 Tab 键焦点切换测试（3个新测试用例）
- ✅ 验证表格 tabIndex 属性
- ✅ 验证 focus-visible 样式类
- ✅ 验证 Tab 键焦点行为

**测试增强:**
- 添加 `describe('Tab 键焦点切换')` 测试套件
- 测试表格可聚焦性（tabIndex={0}）
- 测试 focus-visible 样式类
- 测试 Tab 键聚焦行为

**代码质量:**
- ✅ TypeScript 编译通过
- ✅ ESLint 检查通过
- ✅ 测试覆盖更完整
- **测试问题已修复！**
