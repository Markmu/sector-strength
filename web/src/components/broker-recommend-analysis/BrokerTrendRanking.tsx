'use client'

/**
 * 持续推荐排行榜（10 期 plan-02，AC-02/03/05/06/07/08/11）
 *
 * 范式参照 09 BrokerStockRanking：卡片内表格 + 展开机制 + 分页器 + data-testid 命名。
 *
 * - 表头：排名 / 代码 / 名称 / 行业 / 连续月数 / 累计家数 / 最新月家数 / 推荐走势(Sparkline) / 操作
 * - 排序由后端完成（连续月数↓→累计家数↓→最新月家数↓→代码↑），本组件只渲染
 * - 行展开（预加载，无 loading，AC-06）：monthlyBrokers 按月降序（新→旧），每月均展示
 *   月份 + 家数 + 券商（topBrokers 前 3，超 3 显示 "+X 家"，符合 AC-06"每月"要求）；
 *   某月 brokerCount=0 显示家数 0、券商"—"。跨月同名券商通过 data-testid 按月作用域定位，规避 strict mode 冲突
 * - 分页器：total > pageSize 显示，≤ pageSize 隐藏（AC-08）
 *
 * data-testid 清单（spec 依赖）：
 * - broker-trend-table（表格）
 * - broker-trend-expand-{symbol}（展开控件）
 * - broker-trend-expand-content-{symbol}（展开内容）
 * - broker-trend-month-row-{symbol}-{month}（每月明细行，month 为 YYYY-MM，便于按月作用域断言券商）
 * - broker-trend-pagination（分页器，total≤pageSize 隐藏 count=0）
 * - broker-trend-sparkline-{symbol}（折线图）
 */
import React, { useState } from 'react'
import type { TrendRankingItem } from '@/lib/api'
import Pagination from '@/components/ui/Pagination'
import Sparkline from './Sparkline'

const VISIBLE_BROKERS = 3

export interface BrokerTrendRankingProps {
  items: TrendRankingItem[]
  total: number
  page: number
  pageSize: number
  isLoading?: boolean
  isError?: boolean
  onPageChange: (page: number) => void
}

/** 月份字符串降序比较（"2026-06" > "2026-05"，字典序即等价数值序） */
function byMonthDesc(a: { month: string }, b: { month: string }): number {
  if (a.month < b.month) return 1
  if (a.month > b.month) return -1
  return 0
}

export default function BrokerTrendRanking({
  items,
  total,
  page,
  pageSize,
  isLoading,
  isError,
  onPageChange,
}: BrokerTrendRankingProps) {
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
            <table className="w-full text-sm" data-testid="broker-trend-table">
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
                    行业
                  </th>
                  <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-right">
                    连续月数
                  </th>
                  <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-right">
                    累计家数
                  </th>
                  <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-right">
                    最新月家数
                  </th>
                  <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-center">
                    推荐走势
                  </th>
                  <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-center">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-secondary">
                {items.map((item, idx) => {
                  const isExpanded = expandedSymbol === item.symbol
                  // monthlyBrokers 按月降序（新→旧）展示
                  const monthsDesc = [...item.monthlyBrokers].sort(byMonthDesc)
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
                          {item.consecutiveMonths}
                        </td>
                        <td className="px-4 py-3 text-right text-foreground">
                          {item.cumulativeBrokerCount}
                        </td>
                        <td className="px-4 py-3 text-right text-foreground">
                          {item.latestMonthBrokerCount}
                        </td>
                        <td className="px-4 py-3 text-center text-primary">
                          <Sparkline
                            values={item.monthlySeries.map((p) => p.brokerCount)}
                            testId={`broker-trend-sparkline-${item.symbol}`}
                          />
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button
                            type="button"
                            data-testid={`broker-trend-expand-${item.symbol}`}
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
                            colSpan={9}
                            className="px-4 py-3 bg-background/60"
                          >
                            <div
                              data-testid={`broker-trend-expand-content-${item.symbol}`}
                            >
                              <div className="text-xs text-muted-foreground mb-2">
                                月度推荐明细
                              </div>
                              <div className="space-y-1.5">
                                {monthsDesc.map((mb) => {
                                  const visible = mb.topBrokers.slice(
                                    0,
                                    VISIBLE_BROKERS
                                  )
                                  const hidden =
                                    mb.topBrokers.length - VISIBLE_BROKERS
                                  const hasBrokers = mb.topBrokers.length > 0
                                  // AC-06：每月都展示券商（topBrokers 前 3，超 3 显示 "+X 家"）；
                                  // 某月 brokerCount=0 显示家数 0、券商"—"。
                                  // 测试按 broker-trend-month-row-{symbol}-{month} 作用域断言，
                                  // 避免跨月同名券商在全局 getByText 上触发 strict mode 冲突。
                                  return (
                                    <div
                                      key={mb.month}
                                      data-testid={`broker-trend-month-row-${item.symbol}-${mb.month}`}
                                      className="flex flex-wrap items-center gap-2 text-sm"
                                    >
                                      <span className="font-mono text-foreground min-w-[5rem]">
                                        {mb.month}
                                      </span>
                                      <span className="inline-block px-2 py-0.5 text-xs rounded bg-secondary text-secondary-foreground">
                                        {mb.brokerCount} 家
                                      </span>
                                      <span className="text-muted-foreground">
                                        {hasBrokers ? (
                                          <span className="flex flex-wrap gap-1">
                                            {visible.map((b) => (
                                              <span
                                                key={b}
                                                className="inline-block px-1.5 py-0.5 text-xs rounded border border-border bg-card text-foreground"
                                              >
                                                {b}
                                              </span>
                                            ))}
                                            {hidden > 0 && (
                                              <span className="inline-block px-1.5 py-0.5 text-xs rounded bg-secondary text-muted-foreground">
                                                +{hidden} 家
                                              </span>
                                            )}
                                          </span>
                                        ) : (
                                          '—'
                                        )}
                                      </span>
                                    </div>
                                  )
                                })}
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
          <p className="text-sm text-muted-foreground">暂无趋势数据</p>
        </div>
      )}

      {showPagination && (
        <div data-testid="broker-trend-pagination">
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
