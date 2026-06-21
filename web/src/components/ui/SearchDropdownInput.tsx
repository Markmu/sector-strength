'use client'

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Loader2 } from 'lucide-react'

export interface SearchDropdownOption {
  value: string
  label: string
}

interface SearchDropdownInputProps {
  /** 占位文本 */
  placeholder?: string
  /** 搜索函数：传入关键词和页码，返回选项列表和总数 */
  onSearch: (keyword: string, page: number) => Promise<{
    options: SearchDropdownOption[]
    total: number
  }>
  /** 选中回调 */
  onSelect: (option: SearchDropdownOption) => void
  /** 输入变化回调（用于外部 debounce 搜索） */
  onInputChange?: (value: string) => void
  /** 外部受控值 */
  inputValue?: string
  /** 输入框图标 */
  icon?: React.ReactNode
  /** 每页数量，默认 10 */
  pageSize?: number
  /** 搜索延迟，默认 300ms */
  searchDelay?: number
  /** 最小搜索长度，默认 1 */
  minSearchLength?: number
  /** 自定义展示文本（下拉项主文本 + 选中后输入框）；
   * 不传则默认「value - label」（适配基金/股票「代码 - 名称」样式） */
  formatOption?: (option: SearchDropdownOption) => string
  /** 额外 CSS 类名 */
  className?: string
}

/**
 * 通用搜索下拉输入组件
 *
 * 支持：
 * - 输入时实时搜索（防抖）
 * - 下拉列表展示匹配结果（每项 "代码 - 名称"）
 * - 滚动到底部自动加载更多（IntersectionObserver 无限滚动）
 * - 竞态请求处理
 * - 点击外部关闭
 */
export default function SearchDropdownInput({
  placeholder = '搜索...',
  onSearch,
  onSelect,
  onInputChange,
  inputValue,
  icon,
  pageSize = 10,
  searchDelay = 300,
  minSearchLength = 1,
  formatOption,
  className,
}: SearchDropdownInputProps) {
  const [keyword, setKeyword] = useState(inputValue ?? '')
  const [options, setOptions] = useState<SearchDropdownOption[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [hasMore, setHasMore] = useState(false)

  const searchIdRef = useRef(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const sentinelRef = useRef<HTMLDivElement>(null)
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 同步外部 inputValue
  useEffect(() => {
    if (inputValue !== undefined) {
      setKeyword(inputValue)
    }
  }, [inputValue])

  // 执行搜索（第一页）
  const performSearch = useCallback(async (text: string) => {
    if (!text || text.length < minSearchLength) {
      setOptions([])
      setIsOpen(false)
      return
    }

    const searchId = Date.now()
    searchIdRef.current = searchId
    setLoading(true)
    setPage(1)
    setOptions([])
    setIsOpen(true)

    try {
      const result = await onSearch(text, 1)
      // 竞态检查：丢弃过时结果
      if (searchId !== searchIdRef.current) return

      setOptions(result.options)
      setTotal(result.total)
      setHasMore(result.options.length < result.total)
    } catch (error) {
      console.error('[SearchDropdownInput] 搜索失败:', error)
    } finally {
      setLoading(false)
    }
  }, [onSearch, minSearchLength])

  // 防抖输入处理
  const handleChange = useCallback((value: string) => {
    setKeyword(value)

    // 通知外部输入变化
    onInputChange?.(value)

    // 清除旧的定时器
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    // 空输入立即关闭下拉
    if (!value || value.length < minSearchLength) {
      setOptions([])
      setIsOpen(false)
      return
    }

    searchTimeoutRef.current = setTimeout(() => {
      performSearch(value)
    }, searchDelay)
  }, [performSearch, searchDelay, minSearchLength, onInputChange])

  // 加载更多
  const loadMore = useCallback(async () => {
    if (loadingMore || loading || !hasMore) return

    const nextPage = page + 1
    setLoadingMore(true)

    try {
      const result = await onSearch(keyword, nextPage)
      setOptions(prev => [...prev, ...result.options])
      setPage(nextPage)
      setHasMore(nextPage * pageSize < result.total)
    } catch (error) {
      console.error('[SearchDropdownInput] 加载更多失败:', error)
    } finally {
      setLoadingMore(false)
    }
  }, [keyword, page, onSearch, pageSize, hasMore, loadingMore, loading])

  // IntersectionObserver 监听滚动到底部
  useEffect(() => {
    if (!sentinelRef.current || !hasMore || !isOpen) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore && !loading) {
          loadMore()
        }
      },
      { root: scrollContainerRef.current, threshold: 0.1 }
    )

    observer.observe(sentinelRef.current)
    return () => observer.disconnect()
  }, [hasMore, loadingMore, loading, isOpen, loadMore])

  // 点击外部关闭
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 清除定时器
  useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [])

  // 选中处理
  const handleSelect = useCallback((option: SearchDropdownOption) => {
    setKeyword(
      formatOption ? formatOption(option) : `${option.value} - ${option.label}`
    )
    setIsOpen(false)
    setOptions([])
    onSelect(option)
  }, [onSelect, formatOption])

  // 键盘事件：Escape 关闭下拉，回车立即搜索
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      setIsOpen(false)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
      performSearch(keyword)
    }
  }, [keyword, performSearch])

  // 聚焦时如果有内容则重新打开下拉
  const handleFocus = useCallback(() => {
    if (keyword.length >= minSearchLength && options.length > 0) {
      setIsOpen(true)
    }
  }, [keyword, minSearchLength, options.length])

  return (
    <div ref={containerRef} className={`relative ${className || ''}`}>
      {/* 输入框 */}
      <div className="relative">
        {icon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="text-faint">{icon}</span>
          </div>
        )}
        <input
          ref={inputRef}
          type="text"
          placeholder={placeholder}
          value={keyword}
          onChange={(e) => handleChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          className={`
            block w-full text-sm border rounded-lg transition-colors duration-200
            focus:outline-none focus:ring-2 focus:ring-primary-light
            border-border bg-card text-foreground placeholder-faint
            focus:border-primary
            ${icon ? 'pl-10' : 'pl-4'} pr-4 py-2.5
          `}
        />
        {loading && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
            <Loader2 className="w-4 h-4 text-muted-foreground animate-spin" />
          </div>
        )}
      </div>

      {/* 下拉面板 */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-popover/95 backdrop-blur-sm border border-border rounded-lg shadow-xl overflow-hidden">
          <div
            ref={scrollContainerRef}
            className="overflow-y-auto max-h-64"
          >
            {loading && options.length === 0 ? (
              <div className="px-3 py-6 text-center text-muted-foreground text-sm">
                <Loader2 className="w-5 h-5 mx-auto mb-2 animate-spin" />
                <p>搜索中...</p>
              </div>
            ) : options.length > 0 ? (
              <ul className="py-1">
                {options.map((option) => (
                  <li key={option.value}>
                    <button
                      type="button"
                      onClick={() => handleSelect(option)}
                      className="w-full px-3 py-2 text-left text-sm transition-colors hover:bg-secondary flex items-center gap-2"
                    >
                      {formatOption ? (
                        <span className="text-foreground truncate">
                          {formatOption(option)}
                        </span>
                      ) : (
                        <>
                          <span className="font-mono font-medium text-foreground">{option.value}</span>
                          <span className="text-muted-foreground">-</span>
                          <span className="text-foreground truncate">{option.label}</span>
                        </>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="px-3 py-6 text-center text-muted-foreground text-sm">
                无匹配结果
              </div>
            )}

            {/* 滚动加载更多 sentinel */}
            {hasMore && (
              <div ref={sentinelRef} className="py-2 text-center">
                {loadingMore ? (
                  <Loader2 className="w-4 h-4 mx-auto animate-spin text-muted-foreground" />
                ) : (
                  <span className="text-xs text-muted-foreground">滚动加载更多</span>
                )}
              </div>
            )}
          </div>

          {/* 底部统计 */}
          {options.length > 0 && (
            <div className="px-3 py-1.5 bg-secondary/50 border-t border-border text-xs text-muted-foreground">
              共 {total} 条结果{hasMore ? `，已加载 ${options.length} 条` : ''}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
