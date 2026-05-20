/**
 * 空搜索结果组件
 *
 * 当搜索没有匹配结果时显示友好提示
 */

'use client'

import { memo, useCallback } from 'react'
import { SearchX } from 'lucide-react'
import { useSectorClassificationSearch } from '@/stores/useSectorClassificationSearch'
import { cn } from '@/lib/utils'

export interface EmptySearchResultProps {
  /** 自定义类名 */
  className?: string
}

/**
 * 空搜索结果组件
 *
 * @description
 * - 从 Zustand store 获取搜索关键词
 * - 显示 SearchX 图标
 * - 友好的提示消息
 * - 提供清除搜索的快捷方式
 */
export const EmptySearchResult = memo(function EmptySearchResult({
  className = '',
}: EmptySearchResultProps) {
  const { searchQuery, clearSearch } = useSectorClassificationSearch()

  // 处理清除搜索
  const handleClear = useCallback(() => {
    clearSearch()
  }, [clearSearch])

  return (
    <div className={cn(
      'flex flex-col items-center justify-center py-12 px-6 text-center',
      className
    )}>
      {/* 图标 */}
      <div className="mb-4">
        <SearchX className="w-12 h-12 text-muted-foreground" aria-hidden="true" />
      </div>

      {/* 标题 */}
      <h3 className="text-lg font-medium text-foreground mb-2">
        未找到匹配的板块
      </h3>

      {/* 描述 */}
      <p className="text-sm text-muted-foreground mb-4">
        没有找到包含 &quot;{searchQuery}&quot; 的板块
      </p>

      {/* 清除搜索按钮 */}
      <button
        type="button"
        onClick={handleClear}
        className="text-sm text-primary hover:text-primary/80 font-medium transition-colors"
        aria-label="清除搜索并显示所有板块"
      >
        清除搜索
      </button>
    </div>
  )
})
