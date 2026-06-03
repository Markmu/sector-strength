'use client'

import React from 'react'
import { ChevronLeftIcon, ChevronRightIcon } from 'lucide-react'

export interface PaginationProps {
  currentPage: number
  totalPages: number
  total: number
  pageSize: number
  onPageChange: (page: number) => void
  className?: string
}

/**
 * 通用分页组件
 *
 * 支持上一页/下一页和页码按钮，最多显示 5 个页码
 */
export default function Pagination({
  currentPage,
  totalPages,
  total,
  onPageChange,
  className,
}: PaginationProps) {
  if (totalPages <= 1) return null

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

  const pageNumbers = getPageNumbers()

  return (
    <div
      className={`flex items-center justify-between px-1 py-3 ${
        className || ''
      }`}
    >
      {/* 统计信息 */}
      <div className="text-sm text-muted-foreground">
        第 {currentPage} / {totalPages} 页，共 {total} 条
      </div>

      {/* 分页按钮 */}
      <div className="flex items-center gap-1.5">
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
      </div>
    </div>
  )
}
