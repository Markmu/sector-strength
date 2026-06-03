'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Input } from '@/components/ui'
import { SearchIcon, ArrowRightLeftIcon } from 'lucide-react'

export interface FundSearchBarProps {
  /** 当前搜索词 */
  searchValue?: string
  /** 搜索回调（300ms debounce） */
  onSearch: (value: string) => void
  className?: string
}

/**
 * 基金搜索栏组件
 *
 * 两个输入框：
 * - 基金搜索：按代码/名称搜索，300ms debounce 后触发 onSearch
 * - 股票反查：输入回车后跳转反查页
 */
export default function FundSearchBar({
  searchValue = '',
  onSearch,
  className,
}: FundSearchBarProps) {
  const router = useRouter()
  const [fundKeyword, setFundKeyword] = useState(searchValue)
  const [reverseKeyword, setReverseKeyword] = useState('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 同步外部 searchValue
  useEffect(() => {
    setFundKeyword(searchValue)
  }, [searchValue])

  // debounce 基金搜索
  const handleFundSearchChange = useCallback(
    (value: string) => {
      setFundKeyword(value)
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
      debounceRef.current = setTimeout(() => {
        onSearch(value)
      }, 300)
    },
    [onSearch]
  )

  // 基金搜索回车立即触发
  const handleFundKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        if (debounceRef.current) {
          clearTimeout(debounceRef.current)
        }
        onSearch(fundKeyword)
      }
    },
    [fundKeyword, onSearch]
  )

  // 股票反查回车跳转
  const handleReverseKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && reverseKeyword.trim()) {
        router.push(
          `/dashboard/funds/reverse-lookup?symbol=${encodeURIComponent(reverseKeyword.trim())}`
        )
      }
    },
    [reverseKeyword, router]
  )

  return (
    <div className={`flex flex-col sm:flex-row gap-3 ${className || ''}`}>
      {/* 基金搜索 */}
      <div className="flex-1">
        <Input
          type="text"
          placeholder="输入基金代码或名称"
          value={fundKeyword}
          onChange={(e) => handleFundSearchChange(e.target.value)}
          onKeyDown={handleFundKeyDown}
          startIcon={<SearchIcon className="w-4 h-4" />}
          fullWidth
        />
      </div>

      {/* 股票反查 */}
      <div className="flex-1">
        <Input
          type="text"
          placeholder="按股票反查"
          value={reverseKeyword}
          onChange={(e) => setReverseKeyword(e.target.value)}
          onKeyDown={handleReverseKeyDown}
          startIcon={<ArrowRightLeftIcon className="w-4 h-4" />}
          fullWidth
        />
      </div>
    </div>
  )
}
