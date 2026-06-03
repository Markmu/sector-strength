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
const MARKET_OPTIONS = [
  { label: '场内 ETF', value: 'E' },
  { label: '场外', value: 'O' },
] as const

// 基金类型选项
const FUND_TYPE_OPTIONS = [
  { label: '股票型', value: '股票型' },
  { label: '混合型', value: '混合型' },
  { label: '债券型', value: '债券型' },
  { label: 'QDII', value: 'QDII' },
] as const

/**
 * 基金过滤面板
 *
 * 复选框组：市场（场内ETF/场外）+ 基金类型（股票型/混合型/债券型/QDII）
 * 状态提升，选中项变化时通知父组件
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
    <div className={`bg-card rounded-xl border border-border shadow-sm p-4 ${className || ''}`}>
      {/* 市场筛选 */}
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-foreground mb-3">市场</h3>
        <div className="space-y-2.5">
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

      {/* 基金类型筛选 */}
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-3">基金类型</h3>
        <div className="space-y-2.5">
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
