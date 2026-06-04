'use client'

import React, { useRef } from 'react'
import { ChevronLeftIcon, ChevronRightIcon } from 'lucide-react'

const DEFAULT_PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const

export interface PaginationProps {
  currentPage: number
  totalPages: number
  total: number
  pageSize: number
  onPageChange: (page: number) => void
  className?: string
  /** 每页条数选项，默认 [10, 20, 50, 100] */
  pageSizeOptions?: number[]
  /** 每页条数变化回调 */
  onPageSizeChange?: (size: number) => void
  /** 是否显示每页条数选择器，默认 false */
  showPageSizeSelector?: boolean
  /** 是否显示跳转到指定页，默认 false */
  showJumpToPage?: boolean
}

/**
 * 通用分页组件
 *
 * 支持上一页/下一页、页码按钮、每页条数选择器、跳转到指定页
 */
export default function Pagination({
  currentPage,
  totalPages,
  total,
  pageSize,
  onPageChange,
  className,
  pageSizeOptions = [...DEFAULT_PAGE_SIZE_OPTIONS],
  onPageSizeChange,
  showPageSizeSelector = false,
  showJumpToPage = false,
}: PaginationProps) {
  const jumpInputRef = useRef<HTMLInputElement>(null)

  if (total <= 0) return null

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages && page !== currentPage) {
      onPageChange(page)
    }
  }

  // 计算显示的页码范围（最多 5 个）
  const getPageNumbers = (): number[] => {
    const maxVisible = 5
    if (totalPages <= maxVisible) {
      return Array.from({ length: totalPages }, (_, i) => i + 1)
    }

    let start = Math.max(1, currentPage - 2)
    const end = Math.min(totalPages, start + maxVisible - 1)

    // 保证显示 5 个
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1)
    }

    return Array.from({ length: end - start + 1 }, (_, i) => start + i)
  }

  // 跳转到指定页
  const handleJumpToPage = () => {
    const input = jumpInputRef.current
    if (!input) return
    const value = input.value.trim()
    if (!value) return
    const pageNum = parseInt(value, 10)
    if (isNaN(pageNum)) return
    const clamped = Math.max(1, Math.min(totalPages, pageNum))
    input.value = ''
    handlePageChange(clamped)
  }

  // 跳转输入框回车
  const handleJumpKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleJumpToPage()
    }
  }

  const pageNumbers = getPageNumbers()
  const showPageButtons = totalPages > 1

  return (
    <div
      className={`flex flex-col sm:flex-row items-center justify-between gap-3 px-1 py-3 ${
        className || ''
      }`}
    >
      {/* 左侧：统计信息 */}
      <div className="text-sm text-muted-foreground">
        第 {currentPage} / {totalPages} 页，共 {total} 条
      </div>

      {/* 中间：分页按钮 + 跳转 */}
      <div className="flex items-center gap-1.5">
        {showPageButtons && (
          <>
            {/* 上一页 */}
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-3 py-2 text-sm font-medium rounded-lg border border-border bg-card hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 transition-colors"
            >
              <ChevronLeftIcon className="w-4 h-4" />
              上一页
            </button>

            {/* 页码 */}
            <div className="flex items-center gap-1">
              {pageNumbers.map((pageNum) => (
                <button
                  key={pageNum}
                  onClick={() => handlePageChange(pageNum)}
                  className={`min-w-[36px] px-3 py-2 text-sm font-medium rounded-lg border transition-colors ${
                    currentPage === pageNum
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-card text-foreground border-border hover:bg-secondary'
                  }`}
                >
                  {pageNum}
                </button>
              ))}
            </div>

            {/* 下一页 */}
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="px-3 py-2 text-sm font-medium rounded-lg border border-border bg-card hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 transition-colors"
            >
              下一页
              <ChevronRightIcon className="w-4 h-4" />
            </button>
          </>
        )}

        {/* 跳转到指定页 */}
        {showJumpToPage && showPageButtons && (
          <div className="flex items-center gap-1.5 ml-2">
            <span className="text-sm text-muted-foreground">跳至</span>
            <input
              ref={jumpInputRef}
              type="number"
              min={1}
              max={totalPages}
              onKeyDown={handleJumpKeyDown}
              className="w-14 px-2 py-1.5 text-sm text-center rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            />
            <span className="text-sm text-muted-foreground">页</span>
            <button
              onClick={handleJumpToPage}
              className="px-2.5 py-1.5 text-sm font-medium rounded-lg border border-border bg-card hover:bg-secondary transition-colors"
            >
              前往
            </button>
          </div>
        )}
      </div>

      {/* 右侧：每页条数选择器 */}
      {showPageSizeSelector && (
        <div className="flex items-center gap-1.5">
          <span className="text-sm text-muted-foreground">每页</span>
          {pageSizeOptions.map((size) => (
            <button
              key={size}
              onClick={() => onPageSizeChange?.(size)}
              className={`min-w-[36px] px-2 py-1.5 text-sm font-medium rounded-lg border transition-colors ${
                pageSize === size
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-card text-foreground border-border hover:bg-secondary'
              }`}
            >
              {size}
            </button>
          ))}
          <span className="text-sm text-muted-foreground">条</span>
        </div>
      )}
    </div>
  )
}
