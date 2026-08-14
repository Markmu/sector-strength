'use client'

/**
 * 关键指数监控面板容器（第 15 期 plan-04 Task 6）
 *
 * 主页 is_admin=true 时渲染。SWR 拉取 overview + watchlist，向下分发：
 * - IndexOverviewCards：关注指数总览卡片（AC-01/05/12/13）
 * - IndexTrendChart：多指数走势对比（AC-02）
 * - IndexValuationChart：单指数估值水位（AC-03）
 * - IndexWeightTable：成分权重 + 集中度（AC-04/06）
 *
 * 空状态（AC-08）：overview.indices 为空 → 显示"指数数据未初始化"+ 跳转数据管理入口。
 *
 * SWR 解包层级：res.data（ApiResponse.data）= { success, data } 业务包；
 * 组件读 res.data.data 取业务对象（camelCase）。
 */
import React from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import { AlertCircle, Database, RefreshCw, Loader2 } from 'lucide-react'
import { indexMonitorApi } from '@/lib/api'
import type {
  IndexOverviewData,
  IndexWatchlistData,
} from '@/types/indexMonitorTypes'
import IndexOverviewCards from './IndexOverviewCards'
import IndexTrendChart from './IndexTrendChart'
import IndexValuationChart from './IndexValuationChart'
import IndexWeightTable from './IndexWeightTable'
import MarketMetricsPanel from '@/components/market-metrics/MarketMetricsPanel'

const SWR_OPTIONS = {
  revalidateOnFocus: false,
  dedupingInterval: 30000,
} as const

export default function IndexMonitorPage() {
  // overview：关注指数当日行情卡片数据
  const {
    data: overviewRes,
    isLoading: overviewLoading,
    error: overviewError,
    mutate: mutateOverview,
  } = useSWR<{ success: boolean; data: IndexOverviewData }>(
    'indexMonitorOverview',
    () =>
      indexMonitorApi.getOverview().then((res) => res.data as unknown as {
        success: boolean
        data: IndexOverviewData
      }),
    SWR_OPTIONS
  )
  const overview = overviewRes?.data ?? null

  // watchlist：关注指数清单（供走势/估值/权重组件做指数选择候选）
  const {
    data: watchlistRes,
    isLoading: watchlistLoading,
    mutate: mutateWatchlist,
  } = useSWR<{ success: boolean; data: IndexWatchlistData }>(
    'indexMonitorWatchlist',
    () =>
      indexMonitorApi.getWatchlist().then((res) => res.data as unknown as {
        success: boolean
        data: IndexWatchlistData
      }),
    SWR_OPTIONS
  )
  const watchlist = watchlistRes?.data?.watchlist ?? []

  const refreshAll = () => {
    mutateOverview()
    mutateWatchlist()
  }

  const hasIndices = (overview?.indices?.length ?? 0) > 0

  return (
    <div className="space-y-6">
      {/* 标题栏 */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">关键指数监控</h1>
          <p className="text-sm text-muted-foreground mt-1">
            关注指数当日行情 / 走势对比 / 估值水位 / 成分权重
            {overview?.tradeDate && (
              <span className="ml-2">· 数据交易日 {overview.tradeDate}</span>
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={refreshAll}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm border border-border rounded-lg bg-card text-foreground hover:bg-secondary transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          刷新
        </button>
      </header>

      {/* 加载态 */}
      {overviewLoading && !overview && (
        <div className="flex items-center justify-center py-16 text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          加载指数数据中...
        </div>
      )}

      {/* 错误态 */}
      {overviewError && !overview && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-destructive">加载指数数据失败</p>
              <p className="text-sm text-destructive mt-1">
                {(overviewError as Error).message}
              </p>
              <button
                onClick={() => mutateOverview()}
                className="mt-2 inline-flex items-center gap-1 text-sm text-destructive hover:underline"
              >
                <RefreshCw className="w-3 h-3" />
                重试
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 空状态：指数数据未初始化（AC-08） */}
      {overview && !hasIndices && (
        <div className="bg-card rounded-xl border border-border shadow-sm p-8 text-center">
          <Database className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-foreground mb-2">
            指数数据未初始化
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            请先在数据管理页同步指数清单与历史数据。
          </p>
          <Link
            href="/dashboard/admin/data"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary-hover transition-colors"
          >
            <Database className="w-4 h-4" />
            前往数据管理
          </Link>
        </div>
      )}

      {/* 正常渲染：总览 → 市场量价面板 → 走势 → 估值 → 权重 */}
      {overview && hasIndices && (
        <>
          <IndexOverviewCards overview={overview} />

          {/* 市场量价面板（plan-07；FEAT-0003 位置调整）：指数总览之后、走势图之前 */}
          <MarketMetricsPanel />

          {!watchlistLoading && watchlist.length > 0 && (
            <>
              <IndexTrendChart watchlist={watchlist} />
              <IndexValuationChart watchlist={watchlist} />
              <IndexWeightTable watchlist={watchlist} />
            </>
          )}
        </>
      )}
    </div>
  )
}
