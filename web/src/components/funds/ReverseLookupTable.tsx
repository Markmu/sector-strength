'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { ReverseLookupItem } from '@/lib/api'

export interface ReverseLookupTableProps {
  items: ReverseLookupItem[]
  total?: number
  isLoading?: boolean
  isError?: boolean
  className?: string
}

/**
 * 格式化市值为"X.X 亿"
 */
function formatMarketValue(value: number | null): string {
  if (value === null || value === undefined) return '-'
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
  if (value === null || value === undefined) return '-'
  return `${value.toFixed(2)}%`
}

/**
 * 格式化持股数
 */
function formatAmount(value: number | null): string {
  if (value === null || value === undefined) return '-'
  if (value >= 10000) {
    return `${(value / 10000).toFixed(2)} 万`
  }
  return value.toLocaleString()
}

/**
 * 反查结果表格组件
 *
 * 列：基金代码、基金名称、持仓市值、持股数、占净值比、占流通比
 * 点击基金代码/名称跳转详情页
 */
export default function ReverseLookupTable({
  items,
  isLoading,
  isError,
  className,
}: ReverseLookupTableProps) {
  const router = useRouter()

  const handleNavigate = (tsCode: string) => {
    router.push(`/dashboard/funds/${encodeURIComponent(tsCode)}`)
  }

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
              {['基金代码', '基金名称', '持仓市值', '持股数', '占净值比', '占流通比'].map(
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
          反查数据加载失败，请重试
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
                基金代码
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                基金名称
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
                key={`${item.fundTsCode}-${idx}`}
                className="hover:bg-background/80 transition-colors cursor-pointer"
                onClick={() => handleNavigate(item.fundTsCode)}
              >
                <td className="px-4 py-3 font-mono text-primary hover:underline">
                  {item.fundTsCode}
                </td>
                <td className="px-4 py-3 text-primary hover:underline">
                  {item.fundName || '-'}
                </td>
                <td className="px-4 py-3 text-right text-foreground">
                  {formatMarketValue(item.marketValue)}
                </td>
                <td className="px-4 py-3 text-right text-foreground">
                  {formatAmount(item.amount)}
                </td>
                <td className="px-4 py-3 text-right font-medium text-foreground">
                  {formatRatio(item.stkMkvRatio)}
                </td>
                <td className="px-4 py-3 text-right text-muted-foreground">
                  {formatRatio(item.stkFloatRatio)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
