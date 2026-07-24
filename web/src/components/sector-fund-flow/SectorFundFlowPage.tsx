'use client'

/**
 * 板块资金流主页面（plan-03，AC-01~AC-12）
 *
 * 双视图：资金流排行（表格）+ 盘中变化（曲线）。
 * 页面状态全部用 useState/useMemo 管理，不引入新 Zustand store。
 *
 * 状态：
 * - currentView: 'ranking' | 'chart'
 * - sectorType: 'industry' | 'concept' | 'region'（AC-02）
 * - tradeDate: string | null（默认从 latestDate API 取，AC-04 历史回看）
 * - sortBy / order（AC-03 排序）
 * - page / pageSize（AC-12 分页）
 * - selectedSectors: string[]（AC-06 变化视图自选板块）
 *
 * 状态分支：
 * - AC-09：两视图各自独立加载/失败/空态降级
 * - AC-05：变化视图未选板块 → 引导态不画空坐标系
 * - AC-08：无采样数据 → 空态
 *
 * data-testid 约定：
 * - 视图切换：fund-flow-view-ranking / fund-flow-view-chart
 * - 维度切换：fund-flow-sector-type-{value}
 * - 日期：fund-flow-date-input
 * - 刷新：fund-flow-refresh
 */
import React, { useState, useCallback } from 'react'
import { LineChartIcon, TableIcon, RefreshCwIcon, XIcon } from 'lucide-react'
import {
  useFundFlowRankings,
  useFundFlowTimeseries,
  useFundFlowLatestDate,
  useFundFlowSectorCandidates,
} from '@/hooks/useSectorFundFlow'
import {
  SECTOR_TYPES,
  SECTOR_TYPE_LABELS,
  type SectorType,
} from '@/types/sectorTypes'
import type { FundFlowSortBy, FundFlowOrder } from '@/types/fundFlowTypes'
import { Disclaimer } from '@/components/ui/Disclaimer'
import FundFlowRankingTable from './FundFlowRankingTable'
import FundFlowTimeseriesChart from './FundFlowTimeseriesChart'

type CurrentView = 'ranking' | 'chart'
type PageSize = 20 | 50 | 100
const PAGE_SIZE_OPTIONS: PageSize[] = [20, 50, 100]

// 曲线视图最多叠加板块数（性能 + 可读性权衡）
const MAX_SELECTED_SECTORS = 50

export default function SectorFundFlowPage() {
  const [currentView, setCurrentView] = useState<CurrentView>('ranking')
  const [sectorType, setSectorType] = useState<SectorType>('industry')
  // AC-04：tradeDate 默认 null（让后端取最新），latestDate hook 拿到后填入 input
  const [tradeDateInput, setTradeDateInput] = useState<string>('')
  // 实际传给 API 的 tradeDate：空串 → undefined（后端取最新）
  const [sortBy, setSortBy] = useState<FundFlowSortBy>('net_inflow')
  const [order, setOrder] = useState<FundFlowOrder>('desc')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState<PageSize>(20)
  // AC-06：变化视图自选板块（板块名数组）
  const [selectedSectors, setSelectedSectors] = useState<string[]>([])

  // 最新交易日（AC-04：日期 input 默认值 + 判断全局是否有数据）
  const {
    latestDate,
    isLoading: isLatestLoading,
    isError: isLatestError,
    mutate: mutateLatestDate,
  } = useFundFlowLatestDate({ sectorType })

  // 排行榜数据（AC-01）
  const rankingsParams = {
    sectorType,
    tradeDate: tradeDateInput || undefined,
    sortBy,
    order,
    page,
    pageSize,
  }
  const {
    rankings,
    isLoading: isRankingsLoading,
    isError: isRankingsError,
    mutate: mutateRankings,
  } = useFundFlowRankings(rankingsParams)

  // 盘中变化曲线数据（AC-06）
  const timeseriesParams = {
    sectorNames: selectedSectors,
    sectorType,
    tradeDate: tradeDateInput || undefined,
  }
  const {
    timeseries,
    isLoading: isTimeseriesLoading,
    isError: isTimeseriesError,
    isValidating: isTimeseriesValidating,
    mutate: mutateTimeseries,
  } = useFundFlowTimeseries(timeseriesParams)

  // 变化视图的板块选择候选：独立全量拉取，不受排行分页影响（支持最多叠加 50 个）
  const {
    candidates: sectorCandidates,
    isLoading: isCandidatesLoading,
  } = useFundFlowSectorCandidates(sectorType, tradeDateInput || undefined)

  // 维度切换处理：重置分页 + 清空已选板块（不同维度板块名不通，AC-02）
  const handleSectorTypeChange = useCallback((next: SectorType) => {
    setSectorType(next)
    setPage(1)
    setSelectedSectors([])
    // 维度切换后清空日期 input，让后端按新维度取最新（各维度最新日期可能不同）
    setTradeDateInput('')
  }, [])

  // 日期切换（AC-04）
  const handleDateChange = useCallback(
    (value: string) => {
      setTradeDateInput(value)
      setPage(1)
    },
    []
  )

  // 回到最新（清空日期 input）
  const handleResetDate = useCallback(() => {
    setTradeDateInput('')
    setPage(1)
  }, [])

  // 排序切换（AC-03）
  const handleSortChange = useCallback(
    (nextSortBy: FundFlowSortBy, nextOrder: FundFlowOrder) => {
      setSortBy(nextSortBy)
      setOrder(nextOrder)
      setPage(1)
    },
    []
  )

  const handlePageChange = useCallback((next: number) => {
    setPage(next)
  }, [])

  const handlePageSizeChange = useCallback((size: number) => {
    setPageSize(size as PageSize)
    setPage(1)
  }, [])

  // AC-06：板块选择/移除
  const handleToggleSector = useCallback((name: string) => {
    setSelectedSectors((prev) => {
      if (prev.includes(name)) {
        return prev.filter((s) => s !== name)
      }
      if (prev.length >= MAX_SELECTED_SECTORS) return prev
      return [...prev, name]
    })
  }, [])

  const handleRemoveSector = useCallback((name: string) => {
    setSelectedSectors((prev) => prev.filter((s) => s !== name))
  }, [])

  const handleClearSectors = useCallback(() => {
    setSelectedSectors([])
  }, [])

  // AC-07：刷新（盘中延长）
  const handleRefresh = useCallback(() => {
    if (currentView === 'ranking') {
      mutateRankings()
    } else {
      mutateTimeseries()
    }
  }, [currentView, mutateRankings, mutateTimeseries])

  // 维度切换后已选板块可能失效：过滤掉不在候选清单里的（防御，候选来自排行榜）
  // 注意：候选只覆盖排行榜第一页，可能不全；这里只在维度切换时由 handleSectorTypeChange 清空，
  // 不在 render 期间自动过滤（避免用户翻页时误删选择）。

  const effectiveTradeDate = tradeDateInput || latestDate || ''
  const hasAnyData = latestDate !== null

  return (
    <div className="space-y-6">
      {/* 标题 + 视图切换 */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">板块资金流</h1>
          <p className="text-sm text-muted-foreground mt-1">
            实时追踪板块资金净流入/流出排行与盘中变化（数据来源：同花顺）
          </p>
        </div>
        {/* 视图切换（AC-01/AC-05） */}
        <div
          role="tablist"
          aria-label="视图切换"
          className="inline-flex rounded-lg border border-border bg-card p-1"
        >
          <button
            role="tab"
            aria-selected={currentView === 'ranking'}
            type="button"
            onClick={() => setCurrentView('ranking')}
            data-testid="fund-flow-view-ranking"
            className={`inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              currentView === 'ranking'
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <TableIcon className="w-4 h-4" />
            资金流排行
          </button>
          <button
            role="tab"
            aria-selected={currentView === 'chart'}
            type="button"
            onClick={() => setCurrentView('chart')}
            data-testid="fund-flow-view-chart"
            className={`inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              currentView === 'chart'
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <LineChartIcon className="w-4 h-4" />
            盘中变化
          </button>
        </div>
      </header>

      {/* 控制面板：维度切换 + 日期 + 刷新 */}
      <section className="bg-card rounded-xl border border-border shadow-sm p-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
          {/* 维度切换（AC-02） */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">维度</span>
            <div className="inline-flex rounded-lg border border-border bg-background p-0.5">
              {SECTOR_TYPES.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => handleSectorTypeChange(t)}
                  data-testid={`fund-flow-sector-type-${t}`}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    sectorType === t
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {SECTOR_TYPE_LABELS[t]}
                </button>
              ))}
            </div>
          </div>

          {/* 日期选择 + 刷新 */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <label
                htmlFor="fund-flow-date-input"
                className="text-sm font-medium text-muted-foreground whitespace-nowrap"
              >
                交易日
              </label>
              <input
                id="fund-flow-date-input"
                type="date"
                value={effectiveTradeDate}
                onChange={(e) => handleDateChange(e.target.value)}
                data-testid="fund-flow-date-input"
                className="text-sm border border-border rounded-lg px-3 py-1.5 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
              {tradeDateInput && (
                <button
                  type="button"
                  onClick={handleResetDate}
                  className="text-sm text-muted-foreground hover:text-foreground"
                >
                  回到最新
                </button>
              )}
            </div>
            <button
              type="button"
              onClick={handleRefresh}
              data-testid="fund-flow-refresh"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-border bg-background hover:bg-secondary text-foreground transition-colors"
            >
              <RefreshCwIcon
                className={`w-4 h-4 ${
                  currentView === 'chart' && isTimeseriesValidating ? 'animate-spin' : ''
                }`}
              />
              刷新
            </button>
          </div>
        </div>

        {/* 当前交易日标识 */}
        {rankings?.tradeDate && (
          <div className="mt-3 text-xs text-muted-foreground">
            当前数据交易日：{rankings.tradeDate}
            {!tradeDateInput && '（最新）'}
          </div>
        )}
      </section>

      {/* 视图内容 */}
      {currentView === 'ranking' ? (
        <section className="bg-card rounded-xl border border-border shadow-sm p-4 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-foreground">
              {SECTOR_TYPE_LABELS[sectorType]}资金流排行
              {rankings && rankings.total > 0 && (
                <span className="ml-2 text-sm text-muted-foreground">
                  共 {rankings.total} 个板块
                </span>
              )}
            </h2>
            <div className="text-xs text-muted-foreground">
              净额正值<span className="text-rise font-medium">红</span>、负值
              <span className="text-fall font-medium">绿</span>
            </div>
          </div>

          {isLatestError && !rankings ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              加载最新日期失败，请刷新重试
            </div>
          ) : (
            <FundFlowRankingTable
              items={rankings?.items ?? []}
              total={rankings?.total ?? 0}
              page={rankings?.page ?? page}
              pageSize={rankings?.pageSize ?? pageSize}
              isLoading={isRankingsLoading}
              isError={!!isRankingsError}
              hasData={rankings?.hasData ?? !isRankingsLoading}
              sortBy={sortBy}
              order={order}
              onSortChange={handleSortChange}
              onPageChange={handlePageChange}
              onPageSizeChange={handlePageSizeChange}
              onRetry={() => mutateRankings()}
            />
          )}
        </section>
      ) : (
        <section className="bg-card rounded-xl border border-border shadow-sm p-4 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-foreground">
              {SECTOR_TYPE_LABELS[sectorType]}盘中资金流变化
            </h2>
            {selectedSectors.length > 0 && (
              <button
                type="button"
                onClick={handleClearSectors}
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                清空选择
              </button>
            )}
          </div>

          {/* 板块选择区：已选 chip + 候选清单 */}
          <div className="space-y-3">
            {/* 已选板块 chips（AC-06：可移除） */}
            {selectedSectors.length > 0 && (
              <div
                className="flex flex-wrap gap-2"
                data-testid="fund-flow-selected-sectors"
              >
                {selectedSectors.map((name) => (
                  <span
                    key={name}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-full bg-primary/10 text-primary border border-primary/30"
                  >
                    {name}
                    <button
                      type="button"
                      onClick={() => handleRemoveSector(name)}
                      data-testid={`fund-flow-remove-sector-${name}`}
                      className="hover:bg-primary/20 rounded-full p-0.5"
                      aria-label={`移除 ${name}`}
                    >
                      <XIcon className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}

            {/* 候选板块（来自当前维度排行榜） */}
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground">
                从当前{SECTOR_TYPE_LABELS[sectorType]}排行选择板块叠加（最多 {MAX_SELECTED_SECTORS} 个）
                {selectedSectors.length > 0 &&
                  `，已选 ${selectedSectors.length}/${MAX_SELECTED_SECTORS}`}
              </div>
              {isCandidatesLoading ? (
                <div className="text-xs text-muted-foreground">板块清单加载中...</div>
              ) : sectorCandidates.length === 0 ? (
                <div className="text-xs text-muted-foreground">
                  暂无可用板块，请切换维度或日期
                </div>
              ) : (
                <div className="flex flex-wrap gap-2" data-testid="fund-flow-sector-candidates">
                  {sectorCandidates.map((name) => {
                    const active = selectedSectors.includes(name)
                    const disabled = !active && selectedSectors.length >= MAX_SELECTED_SECTORS
                    return (
                      <button
                        key={name}
                        type="button"
                        onClick={() => handleToggleSector(name)}
                        disabled={disabled}
                        data-testid={`fund-flow-toggle-sector-${name}`}
                        className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                          active
                            ? 'bg-primary text-primary-foreground border-primary'
                            : disabled
                              ? 'bg-background text-muted-foreground/40 border-border cursor-not-allowed'
                              : 'bg-background text-foreground border-border hover:border-muted-foreground'
                        }`}
                      >
                        {name}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* 曲线渲染（含三态） */}
          {isTimeseriesError ? (
            <div
              className="p-8 text-center"
              data-testid="fund-flow-timeseries-error"
            >
              <p className="text-sm text-muted-foreground mb-3">盘中变化数据加载失败</p>
              <button
                type="button"
                onClick={() => mutateTimeseries()}
                data-testid="fund-flow-timeseries-retry"
                className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
              >
                重试
              </button>
            </div>
          ) : selectedSectors.length === 0 ? (
            // AC-05：未选板块 → 引导态不画空坐标系
            <div
              className="p-12 text-center border border-dashed border-border rounded-lg"
              data-testid="fund-flow-timeseries-guide"
            >
              <LineChartIcon className="w-10 h-10 mx-auto mb-3 text-muted-foreground/50" />
              <p className="text-base font-medium text-foreground mb-1">请选择要对比的板块</p>
              <p className="text-sm text-muted-foreground">
                从上方板块清单选择 2-3 个板块，即可叠加查看盘中净额变化曲线
              </p>
            </div>
          ) : isTimeseriesLoading ? (
            <div className="h-80 flex items-center justify-center text-muted-foreground text-sm">
              加载盘中变化数据...
            </div>
          ) : !timeseries?.hasData || (timeseries?.series ?? []).length === 0 ? (
            // AC-08：无采样数据 → 空态
            <div
              className="p-12 text-center border border-dashed border-border rounded-lg"
              data-testid="fund-flow-timeseries-empty"
            >
              <p className="text-base font-medium text-foreground mb-1">暂无盘中采样数据</p>
              <p className="text-sm text-muted-foreground">
                该日期非交易日或尚未产生盘中采样，请切换有数据的交易日回看
              </p>
            </div>
          ) : (
            <FundFlowTimeseriesChart data={timeseries} />
          )}
        </section>
      )}

      {/* 说明 */}
      <div className="bg-primary-light rounded-lg border border-primary/30 p-4 text-sm text-muted-foreground">
        <div className="font-semibold mb-2">数据说明</div>
        <ul className="space-y-1 list-disc list-inside">
          <li><strong>资金流排行：</strong>展示该交易日最新采样点的板块资金净额排行，正值（净流入）红色、负值（净流出）绿色</li>
          <li><strong>盘中变化：</strong>叠加多个板块的盘中净额变化曲线，点击刷新可获取最新采样（盘中延长）</li>
          <li><strong>跳转：</strong>板块名可点击的（已匹配板块库）可跳转强度分析页；未匹配的仅显示文字</li>
          <li><strong>单位：</strong>金额展示为亿/万，净额为 流入 - 流出</li>
        </ul>
      </div>

      <Disclaimer showSeparator={true} />
    </div>
  )
}
