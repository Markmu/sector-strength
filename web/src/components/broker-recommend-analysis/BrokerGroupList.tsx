'use client'

/**
 * 券商维度分组列表（09 期 plan-03，AC-04/06/07/12/13）
 *
 * - 按 stockCount 降序展示券商分组
 * - 展开懒加载：broker-broker-{broker}（分组项）/ broker-detail-content-{broker}（展开内容）
 *   展开只显示该券商本月推荐股票列表（不再显示推荐理由，按用户要求移除）
 * - 懒加载失败显示"加载失败，请重试"+ 重试按钮
 * - 分页 total ≤ 20 隐藏分页器
 * - 样式对齐 CrowdRankingTable（卡片内列表、分页器）
 *
 * data-testid 清单（spec 依赖）：
 * - broker-group-list（列表容器）
 * - broker-broker-{broker}（分组项）
 * - broker-detail-content-{broker}（展开内容）
 */
import React, { useState } from 'react'
import { cn } from '@/lib/utils'
import type { BrokerGroupItem } from '@/lib/api'
import { useBrokerDetail } from '@/hooks/useBrokerRecommend'
import Pagination from '@/components/ui/Pagination'

export interface BrokerGroupListProps {
  items: BrokerGroupItem[]
  month: string | undefined
  total: number
  page: number
  pageSize: number
  isLoading?: boolean
  isError?: boolean
  onPageChange: (page: number) => void
}

export default function BrokerGroupList({
  items,
  month,
  total,
  page,
  pageSize,
  isLoading,
  isError,
  onPageChange,
}: BrokerGroupListProps) {
  const [expandedBroker, setExpandedBroker] = useState<string | null>(null)

  const totalPages = Math.ceil(total / pageSize)
  const showPagination = total > pageSize

  const toggleExpand = (broker: string) => {
    setExpandedBroker((prev) => (prev === broker ? null : broker))
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
      <div className="space-y-2" data-testid="broker-group-list">
        {items.map((item) => (
          <BrokerGroupCard
            key={item.broker}
            item={item}
            month={month}
            expanded={expandedBroker === item.broker}
            onToggle={() => toggleExpand(item.broker)}
          />
        ))}
        {items.length === 0 && (
          <div className="px-3 py-8 text-center text-muted-foreground border border-border rounded-lg bg-card">
            所选月份暂无数据
          </div>
        )}
      </div>

      {showPagination && (
        <div data-testid="broker-group-pagination">
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

interface BrokerGroupCardProps {
  item: BrokerGroupItem
  month: string | undefined
  expanded: boolean
  onToggle: () => void
}

function BrokerGroupCard({ item, month, expanded, onToggle }: BrokerGroupCardProps) {
  // 仅展开时才请求明细（懒加载，AC-13）
  const { detail, isLoading, isError, mutate } = useBrokerDetail(
    expanded ? month ?? null : null,
    expanded ? item.broker : null
  )

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-card">
      <button
        type="button"
        data-testid={`broker-broker-${item.broker}`}
        onClick={onToggle}
        className={cn(
          'w-full flex items-center justify-between px-4 py-3 text-left',
          'hover:bg-muted/30 transition-colors'
        )}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {expanded ? '▼' : '▶'}
          </span>
          <span className="font-medium text-foreground">{item.broker}</span>
        </div>
        <span className="text-sm text-muted-foreground">
          本月推荐 {item.stockCount} 只
        </span>
      </button>

      {expanded && (
        <div
          className="px-4 py-3 bg-muted/20 border-t border-border"
          data-testid={`broker-detail-content-${item.broker}`}
        >
          {isLoading && (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-6 bg-muted animate-pulse rounded" />
              ))}
            </div>
          )}
          {isError && (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <span>加载失败，请重试</span>
              <button
                type="button"
                onClick={() => mutate()}
                className="text-xs px-2 py-0.5 rounded border border-destructive/30 hover:bg-destructive/10"
              >
                重试
              </button>
            </div>
          )}
          {!isLoading && !isError && detail && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {detail.items.map((d) => (
                <div
                  key={d.symbol}
                  className="flex items-center gap-2 px-2 py-1.5 rounded border border-border bg-card text-sm"
                >
                  <span className="font-mono text-foreground">{d.symbol}</span>
                  <span className="text-muted-foreground">
                    {d.name ?? '—'}
                  </span>
                </div>
              ))}
              {detail.items.length === 0 && (
                <div className="text-sm text-muted-foreground">暂无推荐股票</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
