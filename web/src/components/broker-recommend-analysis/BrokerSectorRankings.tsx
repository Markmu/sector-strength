'use client'

/**
 * 板块排行榜（行业/概念/地域，各 Top5）（09 期 plan-03 增量）
 *
 * 三列卡片并排，每列展示一种板块类型的 Top5 横向条形条：
 * - 板块名（左）+ 数值 + 占比
 * - 横向进度条（宽度按 stockCount/该列最大值 比例）
 *
 * 跟随当前月份切换联动；空状态（hasNoData）时由父组件隐藏本区块。
 *
 * data-testid：broker-sector-rankings（容器）/ broker-sector-card-{type}（卡片）
 */
import React from 'react'
import { cn } from '@/lib/utils'
import type { BrokerSectorRankingItem } from '@/lib/api'
import {
  THS_SECTOR_TYPE_OPTIONS,
  type ThsSectorType,
} from '@/types/sectorTypes'

export interface BrokerSectorRankingsProps {
  rankings: {
    industry: BrokerSectorRankingItem[]
    concept: BrokerSectorRankingItem[]
    region: BrokerSectorRankingItem[]
  } | null
  isLoading?: boolean
  isError?: boolean
}

function SectorCard({
  sectorType,
  label,
  display,
  items,
  isLoading,
  isError,
}: {
  sectorType: ThsSectorType
  label: string
  display: string
  items: BrokerSectorRankingItem[]
  isLoading?: boolean
  isError?: boolean
}) {
  const maxCount = items.length > 0 ? Math.max(...items.map((i) => i.stockCount)) : 0

  return (
    <div
      className="bg-card rounded-lg border border-border p-4"
      data-testid={`broker-sector-card-${sectorType}`}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-foreground">{display}</h3>
        <span className="text-xs text-muted-foreground">Top {items.length || 5}</span>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="space-y-1">
              <div className="h-3 bg-muted animate-pulse rounded w-1/2" />
              <div className="h-2 bg-muted animate-pulse rounded w-full" />
            </div>
          ))}
        </div>
      )}

      {!isLoading && isError && (
        <div className="py-6 text-center text-xs text-muted-foreground">
          加载失败，请重试
        </div>
      )}

      {!isLoading && !isError && items.length === 0 && (
        <div className="py-6 text-center text-xs text-muted-foreground">
          暂无{label}分布数据
        </div>
      )}

      {!isLoading && !isError && items.length > 0 && (
        <div className="space-y-2.5">
          {items.map((item) => {
            const widthPct = maxCount > 0 ? (item.stockCount / maxCount) * 100 : 0
            return (
              <div key={item.sectorName} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-foreground truncate">{item.sectorName}</span>
                  <span className="text-muted-foreground ml-2 whitespace-nowrap">
                    {item.stockCount} 只
                    <span className="ml-1 text-muted-foreground/70">
                      {item.percentage.toFixed(1)}%
                    </span>
                  </span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'h-full bg-primary/70 rounded-full transition-all'
                    )}
                    style={{ width: `${widthPct}%` }}
                    data-testid={`broker-sector-bar-${sectorType}-${item.sectorName}`}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default function BrokerSectorRankings({
  rankings,
  isLoading,
  isError,
}: BrokerSectorRankingsProps) {
  return (
    <section className="space-y-3" data-testid="broker-sector-rankings">
      <div className="flex items-center gap-2">
        <h2 className="text-base font-semibold text-foreground">板块分布</h2>
        <span className="text-xs text-muted-foreground">
          按被推荐股票数统计（行业 / 概念 / 地域）
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {THS_SECTOR_TYPE_OPTIONS.map((opt) => (
          <SectorCard
            key={opt.value}
            sectorType={opt.value}
            label={opt.label}
            display={opt.display}
            items={rankings?.[opt.value] ?? []}
            isLoading={isLoading}
            isError={isError}
          />
        ))}
      </div>
    </section>
  )
}
