import React from 'react'
import { cn } from '@/lib/utils'
import { ArrowDown, ArrowUp, LoaderCircle } from 'lucide-react'

export interface TableColumn<T extends object = object> {
  key: keyof T | string
  title: string
  width?: string | number
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
  render?: (value: unknown, record: T, index: number) => React.ReactNode
}

export interface TableProps<T extends object = object> {
  columns: TableColumn<T>[]
  data: T[]
  loading?: boolean
  emptyText?: string
  className?: string
  onRowClick?: (record: T, index: number) => void
  onSort?: (column: TableColumn<T>, direction: 'asc' | 'desc') => void
  rowKey?: keyof T | string | ((record: T) => string)
  striped?: boolean
  bordered?: boolean
  hoverable?: boolean
  compact?: boolean
}

function Table<T extends object>({
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
      const aValue = (a as Record<string, unknown>)[sortConfig.key!]
      const bValue = (b as Record<string, unknown>)[sortConfig.key!]

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
    return String((record as Record<string, unknown>)[String(rowKey)] ?? index)
  }

  const sortedData = getSortedData()

  return (
    <div className={cn('custom-scrollbar w-full overflow-auto rounded-xl border border-border bg-card shadow-subtle', className)}>
      <table className={cn(
        'w-full border-collapse tabular-nums',
        compact ? 'text-xs' : 'text-sm'
      )}>
        <thead className={cn(
          'sticky top-0 z-10 bg-muted border-b border-border'
        )}>
          <tr>
            {columns.map((column) => (
              <th
                key={String(column.key)}
                className={cn(
                  'whitespace-nowrap px-3 py-2.5 font-semibold text-muted-foreground text-xs tracking-wide',
                  column.align === 'center' && 'text-center',
                  column.align === 'right' && 'text-right',
                  column.sortable && 'cursor-pointer hover:bg-secondary transition-colors',
                  bordered && 'border-r border-border last:border-r-0'
                )}
                style={{ width: column.width }}
                onClick={() => handleSort(column)}
              >
                <div className="flex items-center gap-2">
                  <span>{column.title}</span>
                  {column.sortable && sortConfig.key === String(column.key) && (
                    sortConfig.direction === 'asc' ? (
                      <ArrowUp className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                    ) : (
                      <ArrowDown className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                    )
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className={cn(
          'divide-y divide-border/70',
          striped && '[&_tr:nth-child(even)]:bg-muted/40'
        )}>
          {loading ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-muted-foreground"
              >
                <div className="flex items-center justify-center">
                  <LoaderCircle className="-ml-1 mr-3 h-5 w-5 animate-spin text-primary" aria-hidden="true" />
                  加载中...
                </div>
              </td>
            </tr>
          ) : sortedData.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-muted-foreground"
              >
                {emptyText}
              </td>
            </tr>
          ) : (
            sortedData.map((record, index) => (
              <tr
                key={getRowKey(record, index)}
                className={cn(
                  hoverable && 'hover:bg-secondary/65 transition-colors',
                  onRowClick && 'cursor-pointer focus-within:bg-secondary/65'
                )}
                onClick={() => onRowClick?.(record, index)}
              >
                {columns.map((column) => (
                  <td
                    key={String(column.key)}
                    className={cn(
                      'px-3 py-2.5 text-foreground',
                      column.align === 'center' && 'text-center',
                      column.align === 'right' && 'text-right',
                      bordered && 'border-r border-border/60 last:border-r-0'
                    )}
                  >
                    {column.render
                      ? column.render(
                          (record as Record<string, unknown>)[String(column.key)],
                          record,
                          index
                        )
                      : String((record as Record<string, unknown>)[String(column.key)] ?? '-')}
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
