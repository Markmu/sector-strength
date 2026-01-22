/**
 * 搜索框组件
 *
 * 用于按板块名称搜索过滤表格数据
 */

'use client'

import { memo, useCallback } from 'react'
import { Search, X } from 'lucide-react'
import { useSectorClassificationSearch } from '@/stores/useSectorClassificationSearch'
import { cn } from '@/lib/utils'
import Input from '@/components/ui/Input'

export interface SearchBarProps {
  /** 占位符文本 */
  placeholder?: string
  /** 自定义类名 */
  className?: string
}

/**
 * 搜索框组件
 *
 * @description
 * - 实时搜索（输入时即时过滤）
 * - 左侧搜索图标
 * - 右侧清除按钮（仅在有输入时显示）
 * - 支持 Escape 键清除搜索
 * - 完整的可访问性支持
 */
export const SearchBar = memo(function SearchBar({
  placeholder = '搜索板块名称...',
  className = '',
}: SearchBarProps) {
  const { searchQuery, setSearchQuery, clearSearch } = useSectorClassificationSearch()

  // 处理清除搜索
  const handleClear = useCallback(() => {
    clearSearch()
  }, [clearSearch])

  // 处理键盘事件（Escape 清除搜索）
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape' && searchQuery) {
      clearSearch()
    }
  }, [clearSearch, searchQuery])

  return (
    <div className={cn('relative', className)}>
      {/* 左侧搜索图标 - 绝对定位 */}
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <Search className="w-4 h-4 text-gray-400" aria-hidden="true" />
      </div>

      {/* 输入框 - 左侧留出图标空间，右侧留出清除按钮空间 */}
      <Input
        type="text"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="pl-10"
        aria-label="搜索板块名称"
        fullWidth
      />

      {/* 右侧清除按钮 - 条件渲染，可点击 */}
      {searchQuery && (
        <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
          <button
            type="button"
            onClick={handleClear}
            className="p-1 hover:bg-gray-100 rounded-full transition-colors"
            aria-label="清除搜索"
            tabIndex={0}
          >
            <X className="w-4 h-4 text-gray-400 hover:text-gray-600" aria-hidden="true" />
          </button>
        </div>
      )}
    </div>
  )
})
