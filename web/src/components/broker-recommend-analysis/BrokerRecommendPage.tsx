'use client'

/**
 * 券商每月荐股分析主页面（09 期 plan-03）
 *
 * 页面状态：view（股票/券商维度）+ month（YYYY-MM-01）+ search + page
 *
 * AC-14 统一重置规则（切视图/切月份/搜索均触发）：
 * - 切视图：清空 search + 回第 1 页（保持月份）
 * - 切月份：清空 search + 回第 1 页（保持视图）
 * - 搜索：回第 1 页（debounce 300ms）
 *
 * AC-09 空状态：months.hasData=false → 整页空状态
 *
 * 样式对齐 fund-crowd-analysis：卡片化分块（bg-card rounded-xl border shadow-sm）、
 * text-2xl 标题、副标题、排行榜在 section 卡片内。
 *
 * data-testid：broker-page / broker-empty-state / broker-search-input
 */
import React, { useState, useEffect, useRef, useMemo } from 'react'
import {
  useBrokerMonths,
  useBrokerStockRanking,
  useBrokerList,
  useBrokerSectorRankings,
  useBrokerTrendRanking,
} from '@/hooks/useBrokerRecommend'
import type { BrokerView } from '@/lib/api'
import {
  SECTOR_TYPE_LABELS,
  type SectorType,
} from '@/types/sectorTypes'
import SimpleSelect, {
  type SimpleSelectOption,
} from '@/components/ui/SimpleSelect'
import ViewSwitcher from './ViewSwitcher'
import MonthSelector from './MonthSelector'
import BrokerStockRanking from './BrokerStockRanking'
import BrokerGroupList from './BrokerGroupList'
import BrokerSectorRankings from './BrokerSectorRankings'
import BrokerSectorTypeSelector from './BrokerSectorTypeSelector'
import BrokerTrendRanking from './BrokerTrendRanking'

const DEFAULT_PAGE_SIZE = 20
const SEARCH_DEBOUNCE_MS = 300

export default function BrokerRecommendPage() {
  // 月份：undefined 时由后端取最新（MAX(month)）
  const [view, setView] = useState<BrokerView>('stock')
  const [month, setMonth] = useState<string | undefined>(undefined)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [page, setPage] = useState(1)
  // 板块筛选（仅股票维度生效）
  const [sectorType, setSectorType] = useState<SectorType>('industry')
  const [sectorName, setSectorName] = useState<string | undefined>(undefined)
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { monthsData, isLoading: monthsLoading } = useBrokerMonths()

  // 搜索 debounce
  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => {
      setDebouncedSearch(search)
      setPage(1) // 搜索回第 1 页（AC-11/12）
    }, SEARCH_DEBOUNCE_MS)
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current)
    }
  }, [search])

  // AC-14：切视图清空 search + 板块筛选 + 回第 1 页（保持月份）
  const handleViewChange = (nextView: BrokerView) => {
    if (nextView === view) return
    setView(nextView)
    setSearch('')
    setDebouncedSearch('')
    setSectorName(undefined)
    setPage(1)
  }

  // AC-14：切月份清空 search + 板块筛选 + 回第 1 页（保持视图）
  const handleMonthChange = (nextMonth: string) => {
    setMonth(nextMonth)
    setSearch('')
    setDebouncedSearch('')
    setSectorName(undefined)
    setPage(1)
  }

  // 切板块类型：清空板块名（不同维度的板块名互不相通）+ 回第 1 页
  const handleSectorTypeChange = (nextSectorType: SectorType) => {
    if (nextSectorType === sectorType) return
    setSectorType(nextSectorType)
    setSectorName(undefined)
    setPage(1)
  }

  // 切板块名：回第 1 页
  const handleSectorNameChange = (nextSectorName: string) => {
    setSectorName(nextSectorName || undefined)
    setPage(1)
  }

  const handlePageChange = (nextPage: number) => {
    setPage(nextPage)
    if (typeof window !== 'undefined') {
      const main = document.querySelector('main')
      if (main) main.scrollTop = 0
    }
  }

  // AC-09：从未同步整页空状态（此时不发起 ranking/list 请求，避免无效请求触发 401）
  const hasNoData = !monthsLoading && monthsData && !monthsData.hasData

  const stockRanking = useBrokerStockRanking({
    month,
    search: debouncedSearch || undefined,
    page,
    pageSize: DEFAULT_PAGE_SIZE,
    sectorType,
    sectorName,
    enabled: !hasNoData && view === 'stock',
  })

  const brokerList = useBrokerList({
    month,
    search: debouncedSearch || undefined,
    page,
    pageSize: DEFAULT_PAGE_SIZE,
    enabled: !hasNoData && view === 'broker',
  })

  // 板块排行榜：跟随月份联动，空状态时禁用（独立于 view 切换，始终展示）
  const sectorRankings = useBrokerSectorRankings(month ?? undefined, !hasNoData)

  // 推荐趋势榜（10 期 plan-02）：仅 trend 视图激活时发起请求，无 month 参数（全窗口）
  const trendRanking = useBrokerTrendRanking({
    search: debouncedSearch || undefined,
    page,
    pageSize: DEFAULT_PAGE_SIZE,
    enabled: !hasNoData && view === 'trend',
  })

  const months = monthsData?.months ?? []
  const searchPlaceholder =
    view === 'broker' ? '搜索券商名称' : '搜索股票代码或名称'

  // 板块名下拉选项：从 sectorRankings[sectorType] 派生（复用板块分布数据，Top5）
  // 范式参照 fund-crowd FundCrowdAnalysisPage 的 sectorOptions useMemo
  const sectorOptions: SimpleSelectOption[] = useMemo(() => {
    const list =
      (sectorRankings.rankings?.[sectorType] as
        | Array<{ sectorName: string }>
        | undefined) ?? []
    return [
      { value: '', label: `全部${SECTOR_TYPE_LABELS[sectorType]}` },
      ...list.map((d) => ({ value: d.sectorName, label: d.sectorName })),
    ]
  }, [sectorRankings.rankings, sectorType])

  const sectorTypeLabel = SECTOR_TYPE_LABELS[sectorType]

  // AC-09：从未同步整页空状态
  if (hasNoData) {
    return (
      <div data-testid="broker-page" className="space-y-6">
        <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-foreground">券商每月荐股</h1>
            <p className="text-sm text-muted-foreground mt-1">
              数据来源：券商研究所月度金股（按月聚合，仅供参考）
            </p>
          </div>
        </header>
        <div
          data-testid="broker-empty-state"
          className="bg-card rounded-xl border border-border shadow-sm p-12 text-center"
        >
          <p className="text-lg font-medium text-foreground mb-2">
            暂无券商金股数据
          </p>
          <p className="text-sm text-muted-foreground">请联系管理员同步券商金股数据</p>
        </div>
      </div>
    )
  }

  return (
    <div data-testid="broker-page" className="space-y-6">
      {/* 标题 + 月份选择 */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">券商每月荐股</h1>
          <p className="text-sm text-muted-foreground mt-1">
            数据来源：券商研究所月度金股（按月聚合，仅供参考）
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* 趋势视图固定全窗口，隐藏月份选择器（AC-01） */}
          {view !== 'trend' && (
            <MonthSelector
              months={months}
              value={month ?? months[0]}
              onChange={handleMonthChange}
            />
          )}
          <ViewSwitcher value={view} onChange={handleViewChange} />
        </div>
      </header>

      {/* 板块分布排行榜（行业/概念/地域，各 Top5）—— 趋势视图不展示（跨月聚合不依赖单月板块分布） */}
      {view !== 'trend' && (
        <BrokerSectorRankings
          rankings={sectorRankings.rankings}
          isLoading={sectorRankings.isLoading}
          isError={!!sectorRankings.isError}
        />
      )}

      {/* 排行榜（AC-02/03/06/07 等） */}
      <section className="bg-card rounded-xl border border-border shadow-sm p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-foreground">
            {view === 'stock'
              ? '卖方共识排行榜'
              : view === 'broker'
                ? '券商推荐清单'
                : '持续推荐排行榜'}
            {view === 'stock' && stockRanking.ranking && stockRanking.ranking.total > 0 && (
              <span className="ml-2 text-sm text-muted-foreground">
                共 {stockRanking.ranking.total} 只
              </span>
            )}
            {view === 'broker' && brokerList.list && brokerList.list.total > 0 && (
              <span className="ml-2 text-sm text-muted-foreground">
                共 {brokerList.list.total} 家
              </span>
            )}
            {view === 'trend' && trendRanking.ranking && trendRanking.ranking.total > 0 && (
              <span className="ml-2 text-sm text-muted-foreground">
                共 {trendRanking.ranking.total} 只
              </span>
            )}
          </h2>
          <input
            type="text"
            value={search}
            data-testid="broker-search-input"
            placeholder={searchPlaceholder}
            onChange={(e) => setSearch(e.target.value)}
            className="block w-64 text-sm border rounded-lg px-3 py-2 border-border bg-card text-foreground placeholder-muted-foreground/70 focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>

        {/* 板块筛选器（仅股票维度生效）：类型选择 + 板块名下拉 */}
        {view === 'stock' && (
          <div className="flex flex-wrap items-center gap-3 pb-2 border-b border-border">
            <BrokerSectorTypeSelector
              value={sectorType}
              onChange={handleSectorTypeChange}
            />
            <SimpleSelect
              value={sectorName ?? ''}
              options={sectorOptions}
              onChange={handleSectorNameChange}
              ariaLabel="板块筛选"
              testId="broker-sector-filter"
            />
          </div>
        )}

        {view === 'stock' ? (
          <BrokerStockRanking
            items={stockRanking.ranking?.items ?? []}
            total={stockRanking.ranking?.total ?? 0}
            page={page}
            pageSize={DEFAULT_PAGE_SIZE}
            sectorTypeLabel={sectorTypeLabel}
            isLoading={stockRanking.isLoading}
            isError={!!stockRanking.isError}
            onPageChange={handlePageChange}
          />
        ) : view === 'broker' ? (
          <BrokerGroupList
            items={brokerList.list?.items ?? []}
            month={month ?? months[0]}
            total={brokerList.list?.total ?? 0}
            page={page}
            pageSize={DEFAULT_PAGE_SIZE}
            isLoading={brokerList.isLoading}
            isError={!!brokerList.isError}
            onPageChange={handlePageChange}
          />
        ) : (
          <BrokerTrendRanking
            items={trendRanking.ranking?.items ?? []}
            total={trendRanking.ranking?.total ?? 0}
            page={page}
            pageSize={DEFAULT_PAGE_SIZE}
            isLoading={trendRanking.isLoading}
            isError={!!trendRanking.isError}
            onPageChange={handlePageChange}
          />
        )}

        {/* 搜索/筛选无结果提示（ranking 有数据但 items 为空 且 有 search/sector） */}
        {(debouncedSearch || sectorName) &&
          view === 'stock' &&
          stockRanking.ranking &&
          stockRanking.ranking.items.length === 0 &&
          stockRanking.ranking.total === 0 && (
            <div className="p-8 text-center text-sm text-muted-foreground">
              未找到匹配结果，请调整搜索词或板块筛选
            </div>
          )}
        {debouncedSearch &&
          view === 'broker' &&
          brokerList.list &&
          brokerList.list.items.length === 0 &&
          brokerList.list.total === 0 && (
            <div className="p-8 text-center text-sm text-muted-foreground">
              未找到匹配结果，请调整搜索词
            </div>
          )}
        {debouncedSearch &&
          view === 'trend' &&
          trendRanking.ranking &&
          trendRanking.ranking.items.length === 0 &&
          trendRanking.ranking.total === 0 && (
            <div className="p-8 text-center text-sm text-muted-foreground">
              未找到匹配结果，请调整搜索词
            </div>
          )}
      </section>
    </div>
  )
}

