'use client'

import React from 'react'
import { PortfolioItem } from '@/lib/api'
import { ChevronDownIcon } from 'lucide-react'

export interface FundPortfolioTableProps {
  items: PortfolioItem[]
  total: number
  isLoading?: boolean
  isError?: boolean
  onShowAll?: () => void
  className?: string
}

/**
 * 格式化市值为"X.X 亿"
 */
function formatMarketValue(value: number | null): string {
  if (value === null || value === undefined) return '—'
  const yi = value / 1e8
  if (yi >= 1) {
    return `${yi.toFixed(1)} 亿`
  }
  const wan = value / 1e4
  if (wan >= 1) {
    return `${wan.toFixed(1)} 万`
  }
  return `${value.toFixed(2)} 元`
}

/**
 * 格式化占比，保留两位小数
 */
function formatRatio(value: number | null): string {
  if (value === null || value === undefined) return '—'
  return `${value.toFixed(2)}%`
}

/**
 * 格式化持股数
 */
function formatAmount(value: number | null): string {
  if (value === null || value === undefined) return '—'
  if (value >= 10000) {
    return `${(value / 10000).toFixed(2)} 万`
  }
  return value.toLocaleString()
}

/**
 * 格式化环比变化值
 * 返回 { text, className } 或 null（无变化时不显示）
 */
function formatChange(
  value: number | null | undefined,
  formatter?: 'ratio' | 'amount' | 'marketValue'
): { text: string; className: string } | null {
  if (value === null || value === undefined || value === 0) return null

  const isPositive = value > 0
  const arrow = isPositive ? '↑' : '↓'
  const absVal = Math.abs(value)

  let display: string
  if (formatter === 'ratio') {
    // 百分点变化，如 ↑0.35、↓1.20
    display = absVal < 0.01 ? absVal.toFixed(4) : absVal.toFixed(2)
  } else if (formatter === 'amount') {
    // 股数变化，如 ↑12.50 万、↓3.20 万
    if (absVal >= 10000) {
      display = `${(absVal / 10000).toFixed(2)} 万`
    } else {
      display = absVal.toLocaleString(undefined, { maximumFractionDigits: 0 })
    }
  } else if (formatter === 'marketValue') {
    // 市值变化，如 ↑1.2 亿、↓500.0 万
    const yi = absVal / 1e8
    const wan = absVal / 1e4
    if (yi >= 1) {
      display = `${yi.toFixed(1)} 亿`
    } else if (wan >= 1) {
      display = `${wan.toFixed(1)} 万`
    } else {
      display = absVal.toFixed(0)
    }
  } else {
    display = absVal.toFixed(2)
  }

  return {
    text: `${arrow}${display}`,
    className: isPositive ? 'text-rise' : 'text-fall',
  }
}

/**
 * 环比变化指示器组件
 */
function ChangeIndicator({
  value,
  formatter,
}: {
  value: number | null | undefined
  formatter: 'ratio' | 'amount' | 'marketValue'
}) {
  const change = formatChange(value, formatter)
  if (!change) return null
  return (
    <div className={`text-xxs ${change.className}`}>
      {change.text}
    </div>
  )
}

/**
 * 基金持仓明细表格组件
 *
 * 列：股票代码、名称、持仓市值、持股数、占净值比、占流通比
 * 排序：API 已按 stkMkvRatio DESC 排序
 * 分页：默认前 20 条 + "全部持仓"展开按钮
 * 环比：持仓市值、持股数、占净值比列下方显示相较上期变化值
 */
export default function FundPortfolioTable({
  items,
  total,
  isLoading,
  isError,
  onShowAll,
  className,
}: FundPortfolioTableProps) {
  // 骨架加载态
  if (isLoading) {
    return (
      <div
        className={`bg-card rounded-xl border border-border shadow-sm overflow-hidden ${
          className || ''
        }`}
      >
        <table className="w-full text-sm">
          <thead className="bg-background border-b border-border">
            <tr>
              {['股票代码', '名称', '持仓市值', '持股数', '占净值比', '占流通比'].map(
                (h) => (
                  <th
                    key={h}
                    className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left"
                  >
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-secondary">
            {Array.from({ length: 8 }).map((_, i) => (
              <tr key={i}>
                {Array.from({ length: 6 }).map((_, j) => (
                  <td key={j} className="px-4 py-3">
                    <div className="h-4 bg-secondary/60 rounded animate-pulse" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  // 错误态
  if (isError) {
    return (
      <div
        className={`bg-card rounded-xl border border-border shadow-sm p-8 text-center ${
          className || ''
        }`}
      >
        <p className="text-sm text-muted-foreground">
          持仓数据加载失败，请重试
        </p>
      </div>
    )
  }

  // 空数据
  if (items.length === 0) {
    return null
  }

  return (
    <div
      className={`bg-card rounded-xl border border-border shadow-sm overflow-hidden ${
        className || ''
      }`}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-background border-b border-border">
            <tr>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                股票代码
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                名称
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-right">
                持仓市值
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-right">
                持股数
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-right">
                占净值比
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-right">
                占流通比
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-secondary">
            {items.map((item, idx) => (
              <tr
                key={`${item.stockSymbol}-${idx}`}
                className="hover:bg-background/80 transition-colors"
              >
                <td className="px-4 py-3 font-mono text-foreground">
                  {item.stockSymbol}
                </td>
                <td className="px-4 py-3 text-foreground">
                  <div>{item.stockName || '—'}</div>
                  {item.isNew && (
                    <div className="text-xxs text-rise">新增</div>
                  )}
                </td>
                <td className="px-4 py-3 text-right text-foreground">
                  <div>{formatMarketValue(item.marketValue)}</div>
                  <ChangeIndicator value={item.marketValueChange} formatter="marketValue" />
                </td>
                <td className="px-4 py-3 text-right text-foreground">
                  <div>{formatAmount(item.amount)}</div>
                  <ChangeIndicator value={item.amountChange} formatter="amount" />
                </td>
                <td className="px-4 py-3 text-right font-medium text-foreground">
                  <div>{formatRatio(item.stkMkvRatio)}</div>
                  <ChangeIndicator value={item.stkMkvRatioChange} formatter="ratio" />
                </td>
                <td className="px-4 py-3 text-right text-muted-foreground">
                  {formatRatio(item.stkFloatRatio)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* "全部持仓"展开按钮 */}
      {onShowAll && items.length < total && (
        <div className="border-t border-border px-4 py-3 text-center">
          <button
            onClick={onShowAll}
            className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:text-primary/80 transition-colors"
          >
            <ChevronDownIcon className="w-4 h-4" />
            全部持仓（共 {total} 条）
          </button>
        </div>
      )}
    </div>
  )
}
