'use client'

/**
 * 持仓详情区容器（plan-04）
 *
 * 整合：汇总统计 + 行业分布条形图 + 变动趋势 + 持仓股票列表（含筛选 + 分页）
 *
 * 状态管理（架构 §6.2 联动逻辑）：
 * - industry 筛选值 → 重发 summary + holdings（industry-distribution 不受影响）
 * - changeDirection 筛选值 → 重发 summary + industry-distribution + holdings
 * - page 翻页 → 仅重发 holdings
 *
 * 边界：
 * - hasPrevPeriod=false → 变动趋势区展示"上期数据不完整，变动趋势暂不可用"
 * - 汇总/列表空 → 各区域展示空态文案
 * - API loading/error → 展示 loading/error 状态
 */
import React, { useMemo, useState } from 'react'
import { AlertTriangleIcon, BarChart3Icon } from 'lucide-react'
import {
  useShareholderSummary,
  useShareholderIndustryDistribution,
  useShareholderHoldings,
  type UseShareholderSummaryParams,
  type UseShareholderIndustryDistributionParams,
  type UseShareholderHoldingsParams,
} from '@/hooks/useShareholderAnalysis'
import IndustryDistribution from './IndustryDistribution'
import HoldingsTable, {
  type HoldingsTableFilters,
} from './HoldingsTable'

const DEFAULT_PAGE_SIZE = 20

export interface HoldingsDetailProps {
  groupIds: number[]
  reportPeriod: string
  hasPrevPeriod: boolean
}

function formatAmount(amount: number): string {
  if (amount >= 100000000) {
    return `${(amount / 100000000).toFixed(2)}亿`
  }
  if (amount >= 10000) {
    return `${(amount / 10000).toFixed(2)}万`
  }
  return amount.toLocaleString('zh-CN')
}

function formatRatio(ratio: number): string {
  return `${(ratio * 100).toFixed(2)}%`
}

export default function HoldingsDetail({
  groupIds,
  reportPeriod,
  hasPrevPeriod,
}: HoldingsDetailProps) {
  const [industry, setIndustry] = useState<string | undefined>(undefined)
  const [changeDirection, setChangeDirection] = useState<string | undefined>(
    undefined
  )
  const [page, setPage] = useState(1)

  const groupIdsStr = useMemo(() => groupIds.join(','), [groupIds])

  // summary params（受 industry + changeDirection 影响）
  const summaryParams: UseShareholderSummaryParams | null = useMemo(
    () => ({
      group_ids: groupIdsStr,
      report_period: reportPeriod,
      industry,
      change_direction: changeDirection,
    }),
    [groupIdsStr, reportPeriod, industry, changeDirection]
  )

  // industry-distribution params（仅受 changeDirection 影响）
  const distParams: UseShareholderIndustryDistributionParams | null = useMemo(
    () => ({
      group_ids: groupIdsStr,
      report_period: reportPeriod,
      change_direction: changeDirection,
    }),
    [groupIdsStr, reportPeriod, changeDirection]
  )

  // holdings params（受 industry + changeDirection + page 影响）
  const holdingsParams: UseShareholderHoldingsParams | null = useMemo(
    () => ({
      group_ids: groupIdsStr,
      report_period: reportPeriod,
      industry,
      change_direction: changeDirection,
      page,
      pageSize: DEFAULT_PAGE_SIZE,
    }),
    [groupIdsStr, reportPeriod, industry, changeDirection, page]
  )

  const { summary: summaryData, isLoading: summaryLoading, isError: summaryError } =
    useShareholderSummary(summaryParams)
  const {
    distribution,
    isLoading: distLoading,
    isError: distError,
  } = useShareholderIndustryDistribution(distParams)
  const {
    holdings,
    total,
    isError: holdingsError,
  } = useShareholderHoldings(holdingsParams)

  // 行业下拉选项（从 distribution 提取）
  const industryOptions = useMemo(() => {
    const set = new Set<string>()
    distribution.forEach((d) => set.add(d.industry))
    return Array.from(set)
  }, [distribution])

  const handleFiltersChange = (next: HoldingsTableFilters) => {
    const newIndustry = next.industry
    const newChangeDir = next.changeDirection
    if (newIndustry !== industry) {
      setIndustry(newIndustry)
      // 切换行业时回到第 1 页
      setPage(1)
    }
    if (newChangeDir !== changeDirection) {
      setChangeDirection(newChangeDir)
      // 切换变动方向时回到第 1 页（同时重置行业联动）
      setPage(1)
    }
  }

  // 行业分布图点击 → 联动行业筛选
  const handleIndustryClick = (ind: string) => {
    // toggle：再点同一个 → 取消
    setIndustry((prev) => (prev === ind ? undefined : ind))
    setPage(1)
  }

  const summary = summaryData?.summary
  const trend = summaryData?.trend
  const summaryHasPrevPeriod = summaryData?.hasPrevPeriod ?? hasPrevPeriod
  const trendUnavailable = !summaryHasPrevPeriod

  return (
    <div
      data-testid="holdings-detail"
      className="space-y-6 bg-card rounded-2xl border border-border shadow-sm p-5"
    >
      {/* 汇总统计 */}
      <section>
        <h3 className="text-base font-semibold text-foreground mb-3">
          持仓汇总
        </h3>
        {summaryError ? (
          <div className="flex items-center gap-2 text-sm text-amber-600">
            <AlertTriangleIcon className="w-4 h-4" />
            加载失败，请重试
          </div>
        ) : summaryLoading || !summary ? (
          <div className="grid grid-cols-3 gap-4">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-16 bg-secondary/40 rounded-lg animate-pulse"
              />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-background rounded-lg border border-border p-3">
              <div className="text-xs text-muted-foreground mb-1">持仓股票数</div>
              <div className="text-xl font-semibold text-foreground">
                {summary.stockCount}
              </div>
            </div>
            <div className="bg-background rounded-lg border border-border p-3">
              <div className="text-xs text-muted-foreground mb-1">总持股数</div>
              <div className="text-xl font-semibold text-foreground">
                {formatAmount(summary.totalHoldAmount)}
              </div>
            </div>
            <div className="bg-background rounded-lg border border-border p-3">
              <div className="text-xs text-muted-foreground mb-1">平均占流通比</div>
              <div className="text-xl font-semibold text-foreground">
                {formatRatio(summary.avgHoldFloatRatio)}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* 变动趋势 */}
      <section>
        <h3 className="text-base font-semibold text-foreground mb-3">
          变动趋势
        </h3>
        {trendUnavailable ? (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-700">
            上期数据不完整，变动趋势暂不可用
          </div>
        ) : summaryError ? (
          <div className="text-sm text-amber-600">加载失败，请重试</div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-background rounded-lg border border-border p-3">
              <div className="text-xs text-emerald-600 mb-1">↑增持</div>
              <div className="text-lg font-semibold text-emerald-600">
                {trend?.increaseCount ?? 0}
              </div>
            </div>
            <div className="bg-background rounded-lg border border-border p-3">
              <div className="text-xs text-red-600 mb-1">↓减持</div>
              <div className="text-lg font-semibold text-red-600">
                {trend?.decreaseCount ?? 0}
              </div>
            </div>
            <div className="bg-background rounded-lg border border-border p-3">
              <div className="text-xs text-blue-600 mb-1">★新进</div>
              <div className="text-lg font-semibold text-blue-600">
                {trend?.newCount ?? 0}
              </div>
            </div>
            <div className="bg-background rounded-lg border border-border p-3">
              <div className="text-xs text-gray-500 mb-1">✕退出</div>
              <div className="text-lg font-semibold text-gray-500">
                {trend?.exitCount ?? 0}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* 行业分布条形图 */}
      <section>
        <h3 className="text-base font-semibold text-foreground mb-3 flex items-center gap-2">
          <BarChart3Icon className="w-4 h-4 text-muted-foreground" />
          行业占比
        </h3>
        {distError ? (
          <div className="text-sm text-amber-600">加载失败，请重试</div>
        ) : distLoading ? (
          <div className="h-48 bg-secondary/30 rounded-lg animate-pulse" />
        ) : (
          <IndustryDistribution
            distribution={distribution}
            selectedIndustry={industry}
            onIndustryClick={handleIndustryClick}
          />
        )}
      </section>

      {/* 持仓股票列表 */}
      <section>
        <h3 className="text-base font-semibold text-foreground mb-3">
          持仓股票
        </h3>
        {holdingsError ? (
          <div className="text-sm text-amber-600">加载失败，请重试</div>
        ) : (
          <HoldingsTable
            holdings={holdings}
            total={total}
            page={page}
            pageSize={DEFAULT_PAGE_SIZE}
            industries={industryOptions}
            filters={{ industry, changeDirection }}
            onFiltersChange={handleFiltersChange}
            onPageChange={setPage}
            hasPrevPeriod={summaryHasPrevPeriod}
          />
        )}
      </section>
    </div>
  )
}
