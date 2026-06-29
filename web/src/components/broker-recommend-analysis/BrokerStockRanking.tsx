'use client'

/**
 * 股票维度卖方共识排行榜（09 期 plan-03，AC-02/03/06/07）
 *
 * - 按 brokerCount 降序展示
 * - 折叠态：前 3 家券商 + "+X 家"省略
 * - 展开（预加载，无 loading）：broker-expand-{symbol} / broker-expand-content-{symbol}
 *   展开只显示全部推荐券商列表（不再显示推荐理由，按用户要求移除）
 * - 分页 total ≤ 20 隐藏分页器（broker-pagination）
 * - 样式对齐 CrowdRankingTable（卡片内表格、分页器）
 *
 * data-testid 清单（spec 依赖）：
 * - broker-ranking-table（表格）
 * - broker-expand-{symbol}（展开控件）
 * - broker-expand-content-{symbol}（展开内容）
 * - broker-pagination（分页器，total≤20 隐藏 count=0）
 */
import React, { useState } from 'react'
import type { BrokerStockRankingItem } from '@/lib/api'
import Pagination from '@/components/ui/Pagination'

const VISIBLE_BROKERS = 3

export interface BrokerStockRankingProps {
  items: BrokerStockRankingItem[]
  total: number
  page: number
  pageSize: number
  /** 板块分类列标题（随 sectorType 切换：行业/概念/地域） */
  sectorTypeLabel?: string
  isLoading?: boolean
  isError?: boolean
  onPageChange: (page: number) => void
}

export default function BrokerStockRanking({
  items,
  total,
  page,
  pageSize,
  sectorTypeLabel = '行业',
  isLoading,
  isError,
  onPageChange,
}: BrokerStockRankingProps) {
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null)

  const totalPages = Math.ceil(total / pageSize)
  const showPagination = total > pageSize

  const toggleExpand = (symbol: string) => {
    setExpandedSymbol((prev) => (prev === symbol ? null : symbol))
  }

  if (isLoading) {
    return (
      <div className="p-8 text-center text-sm text-muted-foreground">
        加载中…
      </div>
    )
  }
  if (isError) {
    return (
      <div className="p-8 text-center text-sm text-muted-foreground">
        加载失败，请重试
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {items.length > 0 ? (
        <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="broker-ranking-table">
              <thead className="bg-background border-b border-border">
                <tr>
                  <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                    排名
                  </th>
                  <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                    代码
                  </th>
                  <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left min-w-[9rem] whitespace-nowrap">
                    名称
                  </th>
                  <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                    {sectorTypeLabel}
                  </th>
                  <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-right">
                    推荐家数
                  </th>
                  <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                    推荐券商
                  </th>
                  <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-center">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-secondary">
                {items.map((item, idx) => {
                  const isExpanded = expandedSymbol === item.symbol
                  const visibleBrokers = item.brokers.slice(0, VISIBLE_BROKERS)
                  const hiddenCount = item.brokers.length - VISIBLE_BROKERS
                  return (
                    <React.Fragment key={item.symbol}>
                      <tr className="hover:bg-background/80 transition-colors">
                        <td className="px-4 py-3 text-muted-foreground">
                          {(page - 1) * pageSize + idx + 1}
                        </td>
                        <td className="px-4 py-3 font-mono text-foreground">
                          {item.symbol}
                        </td>
                        <td className="px-4 py-3 text-foreground min-w-[9rem] whitespace-nowrap">
                          {item.name ?? '—'}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">
                          {item.industries.length > 0
                            ? item.industries.join('、')
                            : '—'}
                        </td>
                        <td className="px-4 py-3 text-right font-medium text-foreground">
                          {item.brokerCount}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {visibleBrokers.map((b) => (
                              <span
                                key={b.broker}
                                className="inline-block px-2 py-0.5 text-xs rounded bg-secondary text-secondary-foreground"
                              >
                                {b.broker}
                              </span>
                            ))}
                            {hiddenCount > 0 && (
                              <span className="inline-block px-2 py-0.5 text-xs rounded bg-secondary text-muted-foreground">
                                +{hiddenCount} 家
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button
                            type="button"
                            data-testid={`broker-expand-${item.symbol}`}
                            onClick={() => toggleExpand(item.symbol)}
                            className="text-sm text-primary hover:underline"
                          >
                            {isExpanded ? '收起' : '展开'}
                          </button>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr className="hover:bg-transparent">
                          <td
                            colSpan={7}
                            className="px-4 py-3 bg-background/60"
                          >
                            <div
                              data-testid={`broker-expand-content-${item.symbol}`}
                            >
                              <div className="text-xs text-muted-foreground mb-2">
                                全部推荐券商（{item.brokers.length} 家）
                              </div>
                              <div className="flex flex-wrap gap-1.5">
                                {item.brokers.map((b) => (
                                  <span
                                    key={b.broker}
                                    className="inline-block px-2 py-1 text-xs rounded border border-border bg-card text-foreground"
                                  >
                                    {b.broker}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-card rounded-xl border border-border shadow-sm p-12 text-center">
          <p className="text-sm text-muted-foreground">所选月份暂无数据</p>
        </div>
      )}

      {showPagination && (
        <div data-testid="broker-pagination">
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            total={total}
            pageSize={pageSize}
            onPageChange={onPageChange}
          />
        </div>
      )}
    </div>
  )
}
