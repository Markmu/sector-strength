'use client'

/**
 * 股东搜索栏（单股东持仓查询入口）
 *
 * 复用 SearchDropdownInput：
 * - onSearch → shareholderAnalysisApi.searchHolders（全库 DISTINCT holder_name 模糊匹配）
 * - formatOption 只显示股东名称（股东无「代码 - 名称」二元结构，避免「名称 - 名称」重复）
 * - 选中后调 onHolderSelect(holderName)；父组件用受控 value 实现与监控组的互斥切换
 *
 * 参照 components/funds/FundSearchBar.tsx 的命令式搜索写法（onSearch 内直接调 API，
 * 不走 SWR——下拉是临时查询，无需缓存）。
 */
import React, { useCallback } from 'react'
import { SearchIcon, XIcon } from 'lucide-react'
import { shareholderAnalysisApi } from '@/lib/api'
import SearchDropdownInput from '@/components/ui/SearchDropdownInput'
import type { SearchDropdownOption } from '@/components/ui/SearchDropdownInput'

export interface HolderSearchBarProps {
  /** 当前选中的股东名称（受控，null 表示未选） */
  value: string | null
  /** 选中股东回调 */
  onHolderSelect: (holderName: string) => void
  /** 清空回调（点 × 清除当前股东筛选） */
  onClear?: () => void
  className?: string
}

export default function HolderSearchBar({
  value,
  onHolderSelect,
  onClear,
  className,
}: HolderSearchBarProps) {
  // 下拉搜索：keyword + page → {options, total}
  const searchHolders = useCallback(async (keyword: string, page: number) => {
    const res = await shareholderAnalysisApi.searchHolders({
      keyword,
      page,
      pageSize: 10,
    })
    const data = res.data as unknown as {
      data: { holders: Array<{ holderName: string }>; total: number }
    }
    return {
      options: (data.data.holders || []).map((h) => ({
        value: h.holderName,
        label: h.holderName,
      })),
      total: data.data.total || 0,
    }
  }, [])

  const handleSelect = useCallback(
    (option: SearchDropdownOption) => {
      onHolderSelect(option.value)
    },
    [onHolderSelect]
  )

  return (
    <div className={className}>
      <SearchDropdownInput
        placeholder="搜索股东名称，查看该股东持仓"
        icon={<SearchIcon className="w-4 h-4" />}
        inputValue={value ?? ''}
        onSearch={searchHolders}
        onSelect={handleSelect}
        formatOption={(o) => o.value}
      />
      {value && (
        <div
          data-testid="holder-filter-chip"
          className="mt-2 flex items-center gap-2 flex-wrap"
        >
          <span className="text-xs text-muted-foreground">正在查看股东</span>
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-primary/10 text-primary text-sm font-medium">
            <span className="truncate max-w-[20rem]">{value}</span>
            {onClear && (
              <button
                type="button"
                aria-label="清除股东筛选"
                onClick={onClear}
                className="hover:opacity-70"
              >
                <XIcon className="w-3.5 h-3.5" />
              </button>
            )}
          </span>
        </div>
      )}
    </div>
  )
}
