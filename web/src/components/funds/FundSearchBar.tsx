'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { SearchIcon, ArrowRightLeftIcon } from 'lucide-react'
import { fundsApi } from '@/lib/api'
import type { Fund } from '@/lib/api'
import { stocksApi } from '@/lib/api'
import SearchDropdownInput from '@/components/ui/SearchDropdownInput'
import type { SearchDropdownOption } from '@/components/ui/SearchDropdownInput'

export interface FundSearchBarProps {
  /** 当前搜索词 */
  searchValue?: string
  /** 搜索回调 */
  onSearch: (value: string) => void
  /** 股票反查回调（选中股票后触发） */
  onReverseLookup?: (symbol: string, name: string) => void
  className?: string
}

/**
 * 基金搜索栏组件
 *
 * 两个搜索输入框：
 * - 基金搜索：输入代码/名称，下拉模糊匹配，选中后精确搜索
 * - 股票反查：输入股票代码/名称，下拉模糊匹配，选中后通知父组件进入反查模式
 */
export default function FundSearchBar({
  searchValue = '',
  onSearch,
  onReverseLookup,
  className,
}: FundSearchBarProps) {
  const [fundKeyword, setFundKeyword] = useState(searchValue)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 同步外部 searchValue
  useEffect(() => {
    setFundKeyword(searchValue)
  }, [searchValue])

  // 基金搜索：输入变化时 debounce 通知外部（保留原有列表过滤行为）
  const handleFundInputChange = useCallback((value: string) => {
    setFundKeyword(value)
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }
    debounceRef.current = setTimeout(() => {
      onSearch(value)
    }, 300)
  }, [onSearch])

  // 基金下拉搜索函数
  const searchFunds = useCallback(async (keyword: string, page: number) => {
    const res = await fundsApi.getFunds({ search: keyword, page, pageSize: 10 })
    const data = res.data as { data: { items: Fund[]; total: number } }
    return {
      options: (data.data.items || []).map((f: Fund) => ({
        value: f.tsCode,
        label: f.name,
      })),
      total: data.data.total || 0,
    }
  }, [])

  // 选中基金：精确搜索
  const handleFundSelect = useCallback((option: SearchDropdownOption) => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }
    setFundKeyword(option.value)
    onSearch(option.value)
  }, [onSearch])

  // 股票下拉搜索函数
  const searchStocks = useCallback(async (keyword: string, page: number) => {
    const res = await stocksApi.searchStocks(keyword, { page, pageSize: 10 })
    const data = res.data as { data: { items: Array<{ symbol: string; name: string }>; total: number } }
    return {
      options: (data.data.items || []).map((s) => ({
        value: s.symbol,
        label: s.name,
      })),
      total: data.data.total || 0,
    }
  }, [])

  // 选中股票：通知父组件进入反查模式
  const handleStockSelect = useCallback((option: SearchDropdownOption) => {
    onReverseLookup?.(option.value, option.label)
  }, [onReverseLookup])

  return (
    <div className={`flex flex-col sm:flex-row gap-3 ${className || ''}`}>
      {/* 基金搜索 */}
      <div className="flex-1">
        <SearchDropdownInput
          placeholder="输入基金代码或名称"
          icon={<SearchIcon className="w-4 h-4" />}
          inputValue={fundKeyword}
          onSearch={searchFunds}
          onSelect={handleFundSelect}
          onInputChange={handleFundInputChange}
        />
      </div>

      {/* 股票反查 */}
      <div className="flex-1">
        <SearchDropdownInput
          placeholder="按股票反查"
          icon={<ArrowRightLeftIcon className="w-4 h-4" />}
          onSearch={searchStocks}
          onSelect={handleStockSelect}
        />
      </div>
    </div>
  )
}
