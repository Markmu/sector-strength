import React from 'react'
import { cn } from '@/lib/utils'

export interface TableColumn<T = any> {
  key: keyof T | string
  title: string
  width?: string | number
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
  render?: (value: any, record: T, index: number) => React.ReactNode
}

export interface TableProps<T = any> {
  columns: TableColumn<T>[]
  data: T[]
  loading?: boolean
  emptyText?: string
  className?: string
  onRowClick?: (record: T, index: number) => void
  onSort?: (column: TableColumn<T>, direction: 'asc' | 'desc') => void
  rowKey?: keyof T | ((record: T) => string)
  striped?: boolean
  bordered?: boolean
  hoverable?: boolean
  compact?: boolean
}

function Table<T extends Record<string, any>>({
  columns,
  data,
  loading = false,
  emptyText = '暂无数据',
  className,
  onRowClick,
  onSort,
  rowKey = 'id',
  striped = false,
  bordered = true,
  hoverable = true,
  compact = false,
}: TableProps<T>) {
  const [sortConfig, setSortConfig] = React.useState<{
    key: string | null
    direction: 'asc' | 'desc'
  }>({ key: null, direction: 'asc' })

  const handleSort = (column: TableColumn<T>) => {
    if (!column.sortable) return

    const key = String(column.key)
    let direction: 'asc' | 'desc' = 'asc'

    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc'
    }

    setSortConfig({ key, direction })
    onSort?.(column, direction)
  }

  const getSortedData = () => {
    if (!sortConfig.key) return data

    return [...data].sort((a, b) => {
      const aValue = a[sortConfig.key as keyof T]
      const bValue = b[sortConfig.key as keyof T]

      if (aValue === null || aValue === undefined) return 1
      if (bValue === null || bValue === undefined) return -1

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue
      }

      const aStr = String(aValue)
      const bStr = String(bValue)

      return sortConfig.direction === 'asc'
        ? aStr.localeCompare(bStr)
        : bStr.localeCompare(aStr)
    })
  }

  const getRowKey = (record: T, index: number): string => {
    if (typeof rowKey === 'function') {
      return rowKey(record)
    }
    return String(record[rowKey as keyof T] ?? index)
  }

  const sortedData = getSortedData()

  return (
    <div className={cn('w-full overflow-auto rounded-xl border border-[#e9ecef] bg-white', className)}>
      <table className={cn(
        'w-full',
        compact ? 'text-sm' : 'text-base'
      )}>
        <thead className={cn(
          'bg-[#f8f9fb] border-b border-[#e9ecef]'
        )}>
          <tr>
            {columns.map((column) => (
              <th
                key={String(column.key)}
                className={cn(
                  'px-4 py-3 font-semibold text-[#6c757d] text-xs uppercase tracking-wider',
                  column.align === 'center' && 'text-center',
                  column.align === 'right' && 'text-right',
                  column.sortable && 'cursor-pointer hover:bg-[#f1f3f5] transition-colors',
                  bordered && 'border-r border-[#e9ecef] last:border-r-0'
                )}
                style={{ width: column.width }}
                onClick={() => handleSort(column)}
              >
                <div className="flex items-center gap-2">
                  <span>{column.title}</span>
                  {column.sortable && sortConfig.key === String(column.key) && (
                    <svg
                      className="w-4 h-4 text-cyan-500"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      {sortConfig.direction === 'asc' ? (
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 15l7-7 7 7"
                        />
                      ) : (
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 9l-7 7-7-7"
                        />
                      )}
                    </svg>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className={cn(
          'divide-y divide-[#f1f3f5]',
          striped && 'bg-white even:bg-[#f8f9fb]'
        )}>
          {loading ? (
            <tr>
              <td
                colSpan={columns.length}
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
          ) : sortedData.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-[#6c757d]"
              >
                {emptyText}
              </td>
            </tr>
          ) : (
            sortedData.map((record, index) => (
              <tr
                key={getRowKey(record, index)}
                className={cn(
                  hoverable && 'hover:bg-[#f8f9fb]/80 transition-colors',
                  onRowClick && 'cursor-pointer'
                )}
                onClick={() => onRowClick?.(record, index)}
              >
                {columns.map((column) => (
                  <td
                    key={String(column.key)}
                    className={cn(
                      'px-4 py-3 text-[#1a1a2e]',
                      column.align === 'center' && 'text-center',
                      column.align === 'right' && 'text-right',
                      bordered && 'border-r border-[#f1f3f5] last:border-r-0'
                    )}
                  >
                    {column.render
                      ? column.render(
                          record[column.key as keyof T],
                          record,
                          index
                        )
                      : String(record[column.key as keyof T] ?? '-')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

export default Table
