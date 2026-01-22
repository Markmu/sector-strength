/**
 * 可排序表头组件
 *
 * 点击表头可切换排序方向，显示排序指示器图标
 */

'use client'

import { memo } from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'
import { useSectorClassificationSort } from '@/stores/useSectorClassificationSort'
import type { SortColumn } from '@/stores/useSectorClassificationSort'

export interface SortableTableHeaderProps {
  /** 排序列 key */
  column: SortColumn
  /** 表头显示文本 */
  label: string
  /** 列对齐方式 */
  align?: 'left' | 'center' | 'right'
  /** 自定义类名 */
  className?: string
}

/**
 * 可排序表头组件
 *
 * @description
 * - 点击表头切换排序方向
 * - 当前排序列显示高亮背景
 * - 排序指示器：↑ 升序，↓ 降序
 * - 支持键盘操作（Tab + Enter/Space）
 */
export const SortableTableHeader = memo(function SortableTableHeader({
  column,
  label,
  align = 'left',
  className = '',
}: SortableTableHeaderProps) {
  const { sortBy, sortOrder, toggleSortBy } = useSectorClassificationSort()

  const isActive = sortBy === column
  const isAscending = sortOrder === 'asc'

  // 对齐方式样式
  const alignClass = align === 'center' ? 'text-center' : align === 'right' ? 'text-right' : 'text-left'

  // 点击处理（支持鼠标和键盘）
  const handleClick = () => {
    toggleSortBy(column)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleClick()
    }
  }

  return (
    <th
      className={`
        cursor-pointer select-none
        px-4 py-3
        font-semibold text-xs
        text-[#1a1a2e]
        transition-colors duration-150
        hover:bg-gray-100
        ${isActive ? 'bg-gray-50' : ''}
        ${alignClass}
        ${className}
      `}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      aria-sort={isActive ? (isAscending ? 'ascending' : 'descending') : 'none'}
      role="columnheader"
      scope="col"
    >
      <div className="flex items-center gap-1.5">
        <span>{label}</span>
        {isActive && (
          <span className="inline-flex items-center" aria-label={`排序：${isAscending ? '升序' : '降序'}`}>
            {isAscending ? (
              <ChevronUp className="w-4 h-4 text-gray-600" aria-hidden="true" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-600" aria-hidden="true" />
            )}
          </span>
        )}
      </div>
    </th>
  )
})
