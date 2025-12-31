// 排序控制组件
import React, { useCallback, useEffect, useRef } from 'react'
import type { SortBy, SortOrder } from '@/lib/ranking/types'

interface SortingControlsProps {
  sortBy: SortBy
  sortOrder: SortOrder
  onSortByChange: (sortBy: SortBy) => void
  onSortOrderChange: (sortOrder: SortOrder) => void
}

export const SortingControls: React.FC<SortingControlsProps> = React.memo(({
  sortBy,
  sortOrder,
  onSortByChange,
  onSortOrderChange,
}) => {
  // 防抖处理 - 避免快速点击导致多次 API 调用
  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  const handleSortByChange = useCallback((newSortBy: SortBy) => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(() => {
      onSortByChange(newSortBy)
    }, 300)
  }, [onSortByChange])

  const handleSortOrderChange = useCallback(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(() => {
      onSortOrderChange(sortOrder === 'desc' ? 'asc' : 'desc')
    }, 300)
  }, [sortOrder, onSortOrderChange])

  // 清理定时器
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [])

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-[#6c757d]">排序:</span>

      {/* 排序字段选择 */}
      <div className="flex items-center gap-1">
        <button
          onClick={() => handleSortByChange('strength')}
          className={`px-3 py-1.5 text-sm rounded-lg ${
            sortBy === 'strength'
              ? 'bg-cyan-500 text-white shadow-sm'
              : 'bg-[#f1f3f5] text-[#1a1a2e] hover:bg-[#dee2e6]'
          }`}
        >
          强度
        </button>
        <button
          onClick={() => handleSortByChange('trend')}
          className={`px-3 py-1.5 text-sm rounded-lg ${
            sortBy === 'trend'
              ? 'bg-cyan-500 text-white shadow-sm'
              : 'bg-[#f1f3f5] text-[#1a1a2e] hover:bg-[#dee2e6]'
          }`}
        >
          趋势
        </button>
      </div>

      {/* 排序方向 */}
      <button
        onClick={handleSortOrderChange}
        className="px-3 py-1.5 text-sm rounded-lg bg-[#f1f3f5] text-[#1a1a2e] hover:bg-[#dee2e6]"
      >
        {sortOrder === 'desc' ? '降序' : '升序'}
      </button>
    </div>
  )
})

SortingControls.displayName = 'SortingControls'

export default SortingControls
