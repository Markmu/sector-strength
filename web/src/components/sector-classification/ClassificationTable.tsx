/**
 * 板块强弱分类表格组件
 *
 * 显示所有板块的分类结果，包括：
 * - 板块名称
 * - 分类级别（第 1 类 ~ 第 9 类）
 * - 状态（反弹/调整）
 * - 当前价格
 * - 涨跌幅（%）
 *
 * 支持键盘导航：
 * - Tab 键在搜索框、刷新按钮、表格间切换焦点
 * - 方向键（↑/↓/←/→）在单元格间导航
 * - Enter 键选中行
 * - Escape 键退出焦点
 */

'use client'

import { useMemo, useCallback, useEffect, useRef } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSectorClassificationSort } from '@/stores/useSectorClassificationSort'
import { useSectorClassificationSearch } from '@/stores/useSectorClassificationSearch'
import { useKeyboardNavigation } from '@/stores/useKeyboardNavigation'
import { filterClassifications } from './filterUtils'
import { sortClassifications } from './sortUtils'
import { SortableTableHeader } from './SortableTableHeader'
import { EmptySearchResult } from './EmptySearchResult'
import type {
  SectorClassification,
  ClassificationState,
} from '@/types/sector-classification'
import {
  getLevelColor,
  getChangeColor,
  getStateColor,
} from '@/types/sector-classification'

export interface ClassificationTableProps {
  /** 分类数据列表 */
  data: SectorClassification[]
  /** 是否正在加载 */
  loading?: boolean
  /** 空数据提示文本 */
  emptyText?: string
  /** 行点击回调 */
  onRowClick?: (record: SectorClassification, index: number) => void
  /** 行选中回调（键盘 Enter 键触发） */
  onRowSelect?: (record: SectorClassification) => void
  /** 表格类名 */
  className?: string
}

/**
 * 分类表格组件
 *
 * @description
 * - 支持按分类级别、板块名称、涨跌幅排序
 * - 支持按板块名称搜索过滤
 * - 支持键盘导航（方向键、Enter、Escape）
 * - 使用 Zustand 管理排序、搜索和键盘导航状态
 * - 使用 useMemo 和 useCallback 优化性能
 * - 先搜索过滤，再排序
 * - 使用颜色和图标直观展示板块强弱状态
 * - 焦点单元格高亮显示
 */
export function ClassificationTable({
  data,
  loading = false,
  emptyText = '暂无分类数据',
  onRowClick,
  onRowSelect,
  className,
}: ClassificationTableProps) {
  const tableRef = useRef<HTMLTableElement>(null)
  const { sortBy, sortOrder } = useSectorClassificationSort()
  const { searchQuery } = useSectorClassificationSearch()
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

  // 先过滤，再排序（性能优化）
  const filteredAndSortedData = useMemo(() => {
    // 步骤 1: 搜索过滤
    const filtered = filterClassifications(data, searchQuery)

    // 步骤 2: 排序
    const sorted = sortClassifications(filtered, sortBy, sortOrder)

    return sorted
  }, [data, searchQuery, sortBy, sortOrder])

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
          moveDown(filteredAndSortedData.length)
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
            const selectedSector = filteredAndSortedData[focusedCell.rowIndex]
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
    [focusedCell, filteredAndSortedData, moveUp, moveDown, moveLeft, moveRight, clearFocus, onRowSelect]
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
    (record: SectorClassification, rowIndex: number) => {
      setFocusedCell(rowIndex, 0) // 聚焦到行的第一个单元格
      if (onRowClick) {
        onRowClick(record, rowIndex)
      }
    },
    [setFocusedCell, onRowClick]
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

  // 渲染分类级别徽章
  const renderLevelBadge = (level: number) => {
    const colors = getLevelColor(level)
    return (
      <span
        className={cn(
          'inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold border',
          colors.bg,
          colors.text,
          colors.border
        )}
      >
        第 {level} 类
      </span>
    )
  }

  // 渲染状态图标
  const renderStateIcon = (state: ClassificationState) => {
    const color = getStateColor(state)
    const isBounce = state === '反弹'

    return (
      <span className={cn('inline-flex items-center gap-1.5 font-medium', color)}>
        {isBounce ? (
          <TrendingUp className="w-4 h-4" aria-label="反弹" />
        ) : (
          <TrendingDown className="w-4 h-4" aria-label="调整" />
        )}
        {state}
      </span>
    )
  }

  // 渲染涨跌幅
  const renderChangePercent = (value: number) => {
    const color = getChangeColor(value)
    const sign = value > 0 ? '+' : ''

    return (
      <span className={cn('font-semibold tabular-nums', color)}>
        {sign}{value.toFixed(2)}%
      </span>
    )
  }

  // 获取行 key
  const getRowKey = (record: SectorClassification, index: number): string => {
    return record.id ?? String(index)
  }

  // 空搜索结果处理
  // 注意：使用 searchQuery 而不是 searchQuery.trim()，因为 filterClassifications
  // 已经处理了 trim 逻辑。这里只需要检查是否有搜索关键词存在
  if (!loading && filteredAndSortedData.length === 0 && searchQuery) {
    return <EmptySearchResult />
  }

  return (
    <div className={cn('w-full overflow-auto rounded-xl border border-[#e9ecef] bg-white', className)}>
      <table
        ref={tableRef}
        tabIndex={0}
        role="grid"
        aria-label="板块分类表格"
        onKeyDown={handleKeyDown}
        className="w-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2"
      >
        {/* 表头 */}
        <thead className="bg-[#f8f9fb] border-b border-[#e9ecef]">
          <tr>
            {/* 板块名称 */}
            <SortableTableHeader
              column="sector_name"
              label="板块名称"
              align="left"
              className="border-r border-[#e9ecef]"
            />

            {/* 分类级别 */}
            <SortableTableHeader
              column="classification_level"
              label="分类级别"
              align="center"
              className="border-r border-[#e9ecef]"
            />

            {/* 状态（不可排序） */}
            <th
              className="px-4 py-3 font-semibold text-[#6c757d] text-xs uppercase tracking-wider text-center border-r border-[#e9ecef]"
              scope="col"
            >
              状态
            </th>

            {/* 当前价格（不可排序） */}
            <th
              className="px-4 py-3 font-semibold text-[#6c757d] text-xs uppercase tracking-wider text-right border-r border-[#e9ecef]"
              scope="col"
            >
              当前价格
            </th>

            {/* 涨跌幅 */}
            <SortableTableHeader
              column="change_percent"
              label="涨跌幅(%)"
              align="right"
            />
          </tr>
        </thead>

        {/* 表体 */}
        <tbody className={cn('divide-y divide-[#f1f3f5]')}>
          {loading ? (
            <tr>
              <td
                colSpan={5}
                className="px-4 py-8 text-center text-[#6c757d]"
              >
                <div className="flex items-center justify-center">
                  <svg
                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-cyan-500"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  加载中...
                </div>
              </td>
            </tr>
          ) : filteredAndSortedData.length === 0 ? (
            <tr>
              <td
                colSpan={5}
                className="px-4 py-8 text-center text-[#6c757d]"
              >
                {emptyText}
              </td>
            </tr>
          ) : (
            filteredAndSortedData.map((record, index) => (
              <tr
                key={getRowKey(record, index)}
                role="row"
                aria-rowindex={index + 1}
                aria-selected={focusedCell?.rowIndex === index}
                className={cn(
                  'bg-white even:bg-[#f8f9fb]',
                  focusedCell?.rowIndex === index && 'bg-blue-50',
                  onRowClick && 'hover:bg-[#f8f9fb]/80 transition-colors cursor-pointer'
                )}
                onClick={() => handleRowClick(record, index)}
              >
                {/* 板块名称 */}
                <td
                  role="gridcell"
                  aria-colindex={1}
                  tabIndex={focusedCell?.rowIndex === index && focusedCell?.cellIndex === 0 ? 0 : -1}
                  className={cn(
                    'px-4 py-3 text-[#1a1a2e] border-r border-[#f1f3f5]',
                    focusedCell?.rowIndex === index && focusedCell?.cellIndex === 0 && 'ring-2 ring-blue-500 ring-inset'
                  )}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleCellClick(index, 0)
                  }}
                >
                  <span className="font-medium">{record.sector_name}</span>
                </td>

                {/* 分类级别 */}
                <td
                  role="gridcell"
                  aria-colindex={2}
                  tabIndex={focusedCell?.rowIndex === index && focusedCell?.cellIndex === 1 ? 0 : -1}
                  className={cn(
                    'px-4 py-3 border-r border-[#f1f3f5]',
                    focusedCell?.rowIndex === index && focusedCell?.cellIndex === 1 && 'ring-2 ring-blue-500 ring-inset'
                  )}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleCellClick(index, 1)
                  }}
                >
                  {renderLevelBadge(record.classification_level)}
                </td>

                {/* 状态 */}
                <td
                  role="gridcell"
                  aria-colindex={3}
                  tabIndex={focusedCell?.rowIndex === index && focusedCell?.cellIndex === 2 ? 0 : -1}
                  className={cn(
                    'px-4 py-3 border-r border-[#f1f3f5]',
                    focusedCell?.rowIndex === index && focusedCell?.cellIndex === 2 && 'ring-2 ring-blue-500 ring-inset'
                  )}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleCellClick(index, 2)
                  }}
                >
                  {renderStateIcon(record.state)}
                </td>

                {/* 当前价格 */}
                <td
                  role="gridcell"
                  aria-colindex={4}
                  tabIndex={focusedCell?.rowIndex === index && focusedCell?.cellIndex === 3 ? 0 : -1}
                  className={cn(
                    'px-4 py-3 text-right border-r border-[#f1f3f5]',
                    focusedCell?.rowIndex === index && focusedCell?.cellIndex === 3 && 'ring-2 ring-blue-500 ring-inset'
                  )}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleCellClick(index, 3)
                  }}
                >
                  <span className="tabular-nums text-[#1a1a2e]">
                    {record.current_price.toFixed(2)}
                  </span>
                </td>

                {/* 涨跌幅 */}
                <td
                  role="gridcell"
                  aria-colindex={5}
                  tabIndex={focusedCell?.rowIndex === index && focusedCell?.cellIndex === 4 ? 0 : -1}
                  className={cn(
                    'px-4 py-3 text-right',
                    focusedCell?.rowIndex === index && focusedCell?.cellIndex === 4 && 'ring-2 ring-blue-500 ring-inset'
                  )}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleCellClick(index, 4)
                  }}
                >
                  {renderChangePercent(record.change_percent)}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

export default ClassificationTable
