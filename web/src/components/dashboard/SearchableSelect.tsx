'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { CheckIcon, ChevronDownIcon, XIcon, SearchIcon, Loader2 } from 'lucide-react'

interface SelectOption {
  value: string
  label: string
  description?: string
}

interface SearchableSelectProps {
  // 初始选项（用于无搜索时显示）
  options?: SelectOption[]
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  loading?: boolean
  searchPlaceholder?: string
  emptyMessage?: string
  // API 搜索函数
  onSearch?: (keyword: string) => Promise<SelectOption[]>
  // 搜索延迟时间（毫秒）
  searchDelay?: number
  // 最小搜索字符数
  minSearchLength?: number
}

export function SearchableSelect({
  options = [],
  value,
  onChange,
  placeholder = '请选择',
  disabled = false,
  loading = false,
  searchPlaceholder = '搜索...',
  emptyMessage = '无匹配项',
  onSearch,
  searchDelay = 300,
  minSearchLength = 1,
}: SearchableSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filteredOptions, setFilteredOptions] = useState<SelectOption[]>(options)
  const [searchLoading, setSearchLoading] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // 获取当前选中项
  const selectedOption = filteredOptions.find(opt => opt.value === value) ||
                         options.find(opt => opt.value === value)

  // API 搜索函数
  const performSearch = useCallback(async (keyword: string) => {
    if (!onSearch) {
      // 无 API 搜索时，使用客户端过滤
      const filtered = options.filter(option => {
        if (!keyword) return true
        const searchLower = keyword.toLowerCase()
        return (
          option.label.toLowerCase().includes(searchLower) ||
          option.description?.toLowerCase().includes(searchLower) ||
          option.value.toLowerCase().includes(searchLower)
        )
      })
      setFilteredOptions(filtered)
      return
    }

    if (!keyword || keyword.length < minSearchLength) {
      setFilteredOptions(options)
      setSearchLoading(false)
      return
    }

    setSearchLoading(true)
    try {
      const results = await onSearch(keyword)
      setFilteredOptions(results)
    } catch (error) {
      console.error('[SearchableSelect] 搜索失败:', error)
      setFilteredOptions([])
    } finally {
      setSearchLoading(false)
    }
  }, [onSearch, options, minSearchLength])

  // 处理搜索输入（带防抖）
  const handleSearchChange = useCallback((keyword: string) => {
    setSearchTerm(keyword)

    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    searchTimeoutRef.current = setTimeout(() => {
      performSearch(keyword)
    }, searchDelay)
  }, [searchDelay, performSearch])

  // 清除定时器
  useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [])

  // 点击外部关闭
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setSearchTerm('')
        // 重置为初始选项
        setFilteredOptions(options)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [options])

  // 处理选择
  const handleSelect = (optionValue: string) => {
    onChange(optionValue)
    setIsOpen(false)
    setSearchTerm('')
    // 重置为初始选项
    setFilteredOptions(options)
  }

  // 处理清除
  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange('')
    setIsOpen(false)
    setFilteredOptions(options)
  }

  // 切换下拉框
  const toggleDropdown = () => {
    if (!disabled && !loading) {
      setIsOpen(!isOpen)
      if (!isOpen) {
        setTimeout(() => inputRef.current?.focus(), 0)
      }
    }
  }

  const isLoading = loading || searchLoading

  return (
    <div ref={containerRef} className="relative">
      {/* 选择按钮 */}
      <button
        type="button"
        onClick={toggleDropdown}
        disabled={disabled || isLoading}
        className={`
          w-full px-3 py-2 pr-10 text-left border rounded-lg text-sm
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
          disabled:opacity-50 disabled:cursor-not-allowed transition-colors
          ${isOpen ? 'ring-2 ring-blue-500 border-blue-500' : 'border-gray-300 hover:border-gray-400'}
          ${disabled || isLoading ? 'bg-gray-50 text-gray-400' : 'bg-white text-gray-900'}
        `}
      >
        <span className="block truncate">
          {isLoading ? (
            '加载中...'
          ) : selectedOption ? (
            <span className="flex items-center gap-2">
              <span>{selectedOption.label}</span>
              {selectedOption.description && (
                <span className="text-xs text-gray-500">({selectedOption.description})</span>
              )}
            </span>
          ) : (
            <span className="text-gray-400">{placeholder}</span>
          )}
        </span>

        {/* 加载图标 */}
        {searchLoading && (
          <span className="absolute right-8 top-1/2 -translate-y-1/2">
            <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
          </span>
        )}

        {/* 清除按钮 */}
        {value && !disabled && !isLoading && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-8 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <XIcon className="w-4 h-4 text-gray-400" />
          </button>
        )}

        {/* 下拉箭头 */}
        <span className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
          <ChevronDownIcon className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </span>
      </button>

      {/* 下拉面板 */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-80 overflow-hidden flex flex-col">
          {/* 搜索框 */}
          <div className="p-2 border-b border-gray-200">
            <div className="relative">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                ref={inputRef}
                type="text"
                value={searchTerm}
                onChange={(e) => handleSearchChange(e.target.value)}
                placeholder={searchPlaceholder}
                className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchTerm('')
                    setFilteredOptions(options)
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 rounded transition-colors"
                >
                  <XIcon className="w-3 h-3 text-gray-400" />
                </button>
              )}
            </div>
          </div>

          {/* 选项列表 */}
          <div className="overflow-y-auto flex-1">
            {searchLoading ? (
              <div className="px-3 py-8 text-center text-gray-500 text-sm">
                <Loader2 className="w-6 h-6 mx-auto mb-2 animate-spin" />
                <p>搜索中...</p>
              </div>
            ) : filteredOptions.length > 0 ? (
              <ul className="py-1">
                {filteredOptions.map((option) => {
                  const isSelected = option.value === value
                  return (
                    <li key={option.value}>
                      <button
                        type="button"
                        onClick={() => handleSelect(option.value)}
                        className={`
                          w-full px-3 py-2 text-left text-sm transition-colors flex items-center justify-between gap-3
                          ${isSelected ? 'bg-blue-50 text-blue-900' : 'text-gray-900 hover:bg-gray-50'}
                        `}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">{option.label}</div>
                          {option.description && (
                            <div className="text-xs text-gray-500 truncate">{option.description}</div>
                          )}
                        </div>
                        {isSelected && (
                          <CheckIcon className="w-4 h-4 text-blue-600 flex-shrink-0" />
                        )}
                      </button>
                    </li>
                  )
                })}
              </ul>
            ) : searchTerm.length >= minSearchLength ? (
              <div className="px-3 py-8 text-center text-gray-500 text-sm">
                <SearchIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>{emptyMessage}</p>
              </div>
            ) : (
              <div className="px-3 py-8 text-center text-gray-500 text-sm">
                <SearchIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>输入关键词搜索</p>
              </div>
            )}
          </div>

          {/* 底部统计 */}
          {filteredOptions.length > 0 && !searchLoading && (
            <div className="px-3 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-600">
              显示 {filteredOptions.length} 个选项
            </div>
          )}
        </div>
      )}
    </div>
  )
}
