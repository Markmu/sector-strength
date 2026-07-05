'use client'

/**
 * 个股基础信息卡（AC-07 落地页组件）。
 *
 * 展示代码/名称/强度分(含趋势)/最新价/市值。复用 sector-analysis/helpers 的格式化函数。
 *
 * data-testid 约定（plan-04 E2E 选择器）：
 * - 卡片根：stock-info-card
 */
import {
  formatMarketCap,
  formatPrice,
  formatScore,
  getTrendDisplay,
} from '@/components/sector-analysis/helpers'

/** 个股详情最小集（对齐后端 GET /stocks/{id} 返回字段，snake_case） */
export interface StockDetailItem {
  id: string
  symbol: string
  name: string
  current_price: number | null
  market_cap: number | null
  strength_score: number | null
  trend_direction: number | null
}

export interface StockInfoCardProps {
  stock: StockDetailItem | undefined
  isLoading: boolean
  isError: boolean
}

export default function StockInfoCard({ stock, isLoading, isError }: StockInfoCardProps) {
  return (
    <div
      data-testid="stock-info-card"
      className="bg-card rounded-xl border border-border shadow-sm p-6"
    >
      {isLoading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4" aria-busy="true">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <div className="h-3 w-16 bg-secondary/60 rounded animate-pulse" />
              <div className="h-6 w-24 bg-secondary/60 rounded animate-pulse" />
            </div>
          ))}
        </div>
      )}

      {!isLoading && isError && (
        <div className="py-8 text-center">
          <p className="text-sm text-muted-foreground">个股信息加载失败</p>
        </div>
      )}

      {!isLoading && !isError && !stock && (
        <div className="py-8 text-center">
          <p className="text-sm text-muted-foreground">未找到该股票</p>
        </div>
      )}

      {!isLoading && !isError && stock && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground uppercase tracking-wider">代码</div>
            <div className="text-lg font-mono font-semibold text-foreground">{stock.symbol}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground uppercase tracking-wider">名称</div>
            <div className="text-lg font-semibold text-foreground">{stock.name ?? '—'}</div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground uppercase tracking-wider">强度分</div>
            {(() => {
              const trend = getTrendDisplay(stock.trend_direction)
              return (
                <div className={`text-lg font-semibold ${trend.colorClass}`}>
                  <span className="inline-flex items-center gap-1">
                    <span aria-hidden>{trend.arrow}</span>
                    {formatScore(stock.strength_score)}
                  </span>
                </div>
              )
            })()}
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground uppercase tracking-wider">最新价</div>
            <div className="text-lg font-semibold text-foreground tabular-nums">
              {formatPrice(stock.current_price)}
            </div>
          </div>
          <div className="space-y-1 md:col-span-2">
            <div className="text-xs text-muted-foreground uppercase tracking-wider">市值</div>
            <div className="text-lg font-semibold text-foreground tabular-nums">
              {formatMarketCap(stock.market_cap)}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
