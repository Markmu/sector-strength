'use client'

import React from 'react'
import { Checkbox } from '@/components/ui/Checkbox'

export interface FundFilterValues {
  market: string[]
  fundType: string[]
}

export interface FundFilterPanelProps {
  value: FundFilterValues
  onChange: (values: FundFilterValues) => void
  className?: string
}

// 市场选项：label -> API 值
export const MARKET_OPTIONS = [
  { label: '场内 ETF', value: 'E' },
  { label: '场外', value: 'O' },
] as const

// 基金类型选项
export const FUND_TYPE_OPTIONS = [
  { label: '股票型', value: '股票型' },
  { label: '混合型', value: '混合型' },
  { label: '债券型', value: '债券型' },
  { label: 'QDII', value: 'QDII' },
] as const

/**
 * 基金过滤面板（水平布局）
 *
 * 复选框组：市场（场内ETF/场外）+ 基金类型（股票型/混合型/债券型/QDII）
 * 状态提升，选中项变化时通知父组件
 * 水平排列，适合放在表格上方
 */
export default function FundFilterPanel({
  value,
  onChange,
  className,
}: FundFilterPanelProps) {
  const handleMarketToggle = (marketValue: string) => {
    const current = value.market
    const next = current.includes(marketValue)
      ? current.filter((v) => v !== marketValue)
      : [...current, marketValue]
    onChange({ ...value, market: next })
  }

  const handleFundTypeToggle = (fundTypeValue: string) => {
    const current = value.fundType
    const next = current.includes(fundTypeValue)
      ? current.filter((v) => v !== fundTypeValue)
      : [...current, fundTypeValue]
    onChange({ ...value, fundType: next })
  }

  return (
    <div className={`flex flex-wrap items-center gap-x-6 gap-y-2 ${className || ''}`}>
      {/* 市场筛选 */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">市场</span>
        <div className="flex items-center gap-3">
          {MARKET_OPTIONS.map((opt) => (
            <Checkbox
              key={opt.value}
              label={opt.label}
              checked={value.market.includes(opt.value)}
              onCheckedChange={() => handleMarketToggle(opt.value)}
            />
          ))}
        </div>
      </div>

      {/* 分隔线 */}
      <div className="hidden sm:block w-px h-5 bg-border" />

      {/* 基金类型筛选 */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">类型</span>
        <div className="flex items-center gap-3">
          {FUND_TYPE_OPTIONS.map((opt) => (
            <Checkbox
              key={opt.value}
              label={opt.label}
              checked={value.fundType.includes(opt.value)}
              onCheckedChange={() => handleFundTypeToggle(opt.value)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
