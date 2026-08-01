'use client'

/**
 * ETF 监控主页面
 *
 * 仿 SectorFundFlowPage.tsx 范式：纯 useState/useMemo/useCallback 管理状态，不引入 Redux。
 *
 * 双视图协调：
 * - 指数排行视图（ranking）：EtfIndexRankingTable（展开明细 + 趋势入口 + 排序 + 分页）
 * - 历史趋势视图（trend）：EtfTrendChart（对象/指标/区间切换 + 份额/净流入额曲线）
 *
 * 状态流转：
 * - 视图切换保留日期与趋势对象；
 * - 展开行在切排序/翻页时收起；
 * - 趋势入口跳转：onTrend({type,code}) → setCurrentView('trend') + setTrendTarget。
 *
 * data-testid 约定（spec 选择器依赖）：
 * - 视图切换：etf-view-{ranking|trend}
 * - 日期选择器：etf-trade-date
 */
import React, { useState, useCallback, useMemo } from 'react'
import { BarChart3Icon, LineChartIcon } from 'lucide-react'
import {
  useEtfIndexRankings,
  useEtfLatestDate,
  useEtfIndexDetail,
} from '@/hooks/useEtfMonitor'
import type {
  EtfSortBy,
  EtfTrendMetric,
  EtfTrendDays,
  EtfTargetType,
} from '@/types/etfMonitorTypes'
import { Disclaimer } from '@/components/ui/Disclaimer'

/** 排序方向（与 useEtfIndexRankings 一致） */
type EtfOrder = 'desc' | 'asc'
import EtfIndexRankingTable, {
  type EtfTrendTarget,
} from './EtfIndexRankingTable'
import EtfTrendChart from './EtfTrendChart'

const RANKINGS_PAGE_SIZE = 20

// 历史不足区间测试对象（mock 按 target_code 含 '__short__' 标记返回 3 天 < 所选 days）
const SHORT_HISTORY_OPTION = { code: '__short__不足区间', name: '__short__不足区间' }

export default function EtfMonitorPage() {
  // ---- 视图/排序/分页状态 ----
  const [currentView, setCurrentView] = useState<'ranking' | 'trend'>('ranking')
  // tradeDate 默认 ''（让 latestDate hook 取最新填入 input）
  const [tradeDateInput, setTradeDateInput] = useState<string>('')
  const [sortBy, setSortBy] = useState<EtfSortBy>('netInflow')
  const [order, setOrder] = useState<EtfOrder>('desc')
  const [page, setPage] = useState(1)
  // 展开的指数 code（切排序/翻页时收起）
  const [expandedIndex, setExpandedIndex] = useState<string | null>(null)

  // ---- 趋势状态（视图切换后保留）----
  const [trendTarget, setTrendTarget] = useState<EtfTrendTarget | null>(null)
  // 对象类型独立于 target，切换类型只清空对象（不回退类型）
  const [trendTargetType, setTrendTargetType] = useState<EtfTargetType>('index')
  const [trendMetric, setTrendMetric] = useState<EtfTrendMetric>('netInflow')
  const [trendDays, setTrendDays] = useState<EtfTrendDays>(7)

  // ---- 数据 hooks ----
  // 最新交易日（日期 input 默认值 + 判断是否有数据）
  const { latestDate, isLoading: isLatestLoading } = useEtfLatestDate()

  // 指数排行（按 index_code 聚合）
  const rankingsParams = {
    tradeDate: tradeDateInput || undefined,
    sortBy,
    order,
    page,
    pageSize: RANKINGS_PAGE_SIZE,
  }
  const {
    rankings,
    isLoading: isRankingsLoading,
    isError: isRankingsError,
    mutate: mutateRankings,
  } = useEtfIndexRankings(rankingsParams)

  // ETF 对象下拉候选：取已选指数对象（或第一个指数）的明细作为 ETF 列表，
  // 使趋势视图的"单只 ETF"下拉有数据。排行可能空，故取 items[0] 兜底。
  const etfSourceIndexCode =
    trendTargetType === 'index' && trendTarget?.code
      ? trendTarget.code
      : (rankings?.items[0]?.indexCode ?? null)
  const { detail: etfSourceDetail } = useEtfIndexDetail({
    indexCode: etfSourceIndexCode,
    tradeDate: tradeDateInput || undefined,
  })

  // 指数候选（用于趋势视图指数下拉；code 用 indexCode，name 用 indexName）
  const indexOptions = useMemo(() => {
    const items = (rankings?.items ?? []).map((i) => ({
      code: i.indexCode,
      name: i.indexName,
    }))
    // 加入历史不足区间测试样例
    return [...items, SHORT_HISTORY_OPTION]
  }, [rankings])

  // ETF 候选（来自当前对象指数或第一个指数的明细）
  const etfOptions = useMemo(() => {
    const items = (etfSourceDetail?.items ?? []).map((d) => ({
      code: d.tsCode,
      name: d.tsCode,
    }))
    // 去重
    const seen = new Set<string>()
    return items.filter((i) => {
      if (seen.has(i.code)) return false
      seen.add(i.code)
      return true
    })
  }, [etfSourceDetail])

  const effectiveTradeDate = tradeDateInput || latestDate || ''

  // ---- 控制栏回调 ----
  // 视图切换：保留日期、趋势对象
  const handleViewChange = useCallback((next: 'ranking' | 'trend') => {
    setCurrentView(next)
  }, [])

  // 日期切换
  const handleDateChange = useCallback((value: string) => {
    setTradeDateInput(value)
    setExpandedIndex(null)
  }, [])

  // 排序切换：切排序收起展开行
  const handleSortChange = useCallback(
    (nextSortBy: EtfSortBy, nextOrder: EtfOrder) => {
      setSortBy(nextSortBy)
      setOrder(nextOrder)
      setExpandedIndex(null)
    },
    []
  )

  // 翻页：收起展开行、滚动顶部
  const handlePaginate = useCallback((nextPage: number) => {
    setPage(nextPage)
    setExpandedIndex(null)
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }, [])

  // 展开/收起
  const handleExpand = useCallback((indexCode: string | null) => {
    setExpandedIndex(indexCode)
  }, [])

  // 趋势入口跳转 → 切视图 + 定位对象 + 同步对象类型
  const handleTrend = useCallback((target: EtfTrendTarget) => {
    setTrendTarget(target)
    setTrendTargetType(target.type)
    setCurrentView('trend')
  }, [])

  // 趋势对象切换（来自图表组件选择器）
  const handleTrendTargetChange = useCallback((t: EtfTrendTarget | null) => {
    setTrendTarget(t)
  }, [])

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">ETF 监控</h1>
          <p className="text-sm text-muted-foreground mt-1">
            按跟踪指数汇总的 ETF 份额与资金流监控（指数排行 + 历史趋势）
          </p>
        </div>
      </header>

      {/* 控制面板：视图 + 日期 */}
      <section className="bg-card rounded-xl border border-border shadow-sm p-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
          {/* 视图切换 */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">视图</span>
            <div className="inline-flex rounded-lg border border-border bg-background p-0.5">
              <button
                type="button"
                onClick={() => handleViewChange('ranking')}
                data-testid="etf-view-ranking"
                className={`inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  currentView === 'ranking'
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <BarChart3Icon className="w-4 h-4" />
                指数排行
              </button>
              <button
                type="button"
                onClick={() => handleViewChange('trend')}
                data-testid="etf-view-trend"
                className={`inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  currentView === 'trend'
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <LineChartIcon className="w-4 h-4" />
                历史趋势
              </button>
            </div>
          </div>

          {/* 日期选择 */}
          <div className="flex items-center gap-2">
            <label
              htmlFor="etf-trade-date"
              className="text-sm font-medium text-muted-foreground whitespace-nowrap"
            >
              交易日
            </label>
            <input
              id="etf-trade-date"
              type="date"
              value={effectiveTradeDate}
              onChange={(e) => handleDateChange(e.target.value)}
              data-testid="etf-trade-date"
              disabled={isLatestLoading && !latestDate}
              className="text-sm border border-border rounded-lg px-3 py-1.5 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50"
            />
          </div>
        </div>

        {/* 当前交易日标识 */}
        {rankings?.tradeDate && currentView === 'ranking' && (
          <div className="mt-3 text-xs text-muted-foreground">
            当前数据交易日：{rankings.tradeDate}
            {!tradeDateInput && '（最新）'}
          </div>
        )}
      </section>

      {/* 视图区域 */}
      {currentView === 'ranking' ? (
        <section className="bg-card rounded-xl border border-border shadow-sm p-4 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-foreground">
              指数排行
              {rankings && rankings.total > 0 && (
                <span className="ml-2 text-sm text-muted-foreground">
                  共 {rankings.total} 个指数
                </span>
              )}
            </h2>
            <div className="text-xs text-muted-foreground">
              净额正值<span className="text-rise font-medium">红</span>、负值
              <span className="text-fall font-medium">绿</span>
            </div>
          </div>

          <EtfIndexRankingTable
            items={rankings?.items ?? []}
            total={rankings?.total ?? 0}
            page={rankings?.page ?? page}
            pageSize={rankings?.pageSize ?? RANKINGS_PAGE_SIZE}
            sortBy={sortBy}
            order={order}
            loading={isRankingsLoading}
            error={!!isRankingsError}
            hasData={rankings?.hasData ?? !isRankingsLoading}
            expandedIndex={expandedIndex}
            tradeDate={tradeDateInput || undefined}
            onSort={handleSortChange}
            onExpand={handleExpand}
            onTrend={handleTrend}
            onRetry={() => mutateRankings()}
            onPaginate={handlePaginate}
          />
        </section>
      ) : (
        <section className="bg-card rounded-xl border border-border shadow-sm p-4 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-foreground">历史趋势</h2>
          </div>

          <EtfTrendChart
            target={trendTarget}
            targetType={trendTargetType}
            metric={trendMetric}
            days={trendDays}
            endDate={effectiveTradeDate || undefined}
            indexOptions={indexOptions}
            etfOptions={etfOptions}
            onTargetTypeChange={setTrendTargetType}
            onTargetChange={handleTrendTargetChange}
            onMetricChange={setTrendMetric}
            onDaysChange={setTrendDays}
          />
        </section>
      )}

      {/* 数据说明 */}
      <div className="bg-primary-light rounded-lg border border-primary/30 p-4 text-sm text-muted-foreground">
        <div className="font-semibold mb-2">数据说明</div>
        <ul className="space-y-1 list-disc list-inside">
          <li>
            <strong>指数排行：</strong>
            按跟踪指数汇总的 ETF 份额/份额变化/净流入额排行，正值红色、负值绿色
          </li>
          <li>
            <strong>历史趋势：</strong>
            选定指数或单只 ETF，查看份额或净流入额的 7/30/90 日曲线
          </li>
          <li>
            <strong>明细展开：</strong>
            点击指数行展开标记查看其下 ETF 明细，点击「趋势」入口跳转趋势视图
          </li>
          <li>
            <strong>单位：</strong>
            份额为亿份，净流入额为亿元（份额变化 × 单位净值估算）
          </li>
        </ul>
      </div>

      <Disclaimer showSeparator={true} />
    </div>
  )
}
