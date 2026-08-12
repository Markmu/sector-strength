'use client'

/**
 * ETF 指数排行表格（plan-05，AC-01/02/03/04/05/10/11/13）
 *
 * 仿 FundFlowRankingTable.tsx（src/components/sector-fund-flow/FundFlowRankingTable.tsx）范式：
 * 原生 `<table>`（不用 shadcn Table）+ 四态（loading 骨架/error 重试/empty/数据）+ data-testid 锚点。
 *
 * 列：指数名称 / ETF 数 / 合计份数(亿份) / 合计份额(亿元) / 合计份额变化(亿份) / 合计净流入额(亿元) / 操作。
 *
 * 交互：
 * - AC-03：点击 合计份数/合计份额变化/合计净流入额 表头切换排序 + 三态箭头；不可排序列无反应。
 * - AC-04：行展开。点击 ▶/▼ 展开标记 → 调 useEtfIndexDetail 拉该指数下 ETF 明细，
 *   明细按 netInflow desc，渲染在指数行下方（跟随所在页）。再点收起。
 * - AC-11：每指数行 + 每明细 ETF 行有「趋势」入口，点击回调父组件切视图并定位对象。
 *   **展开标记与趋势入口分离**：点展开只展开（不跳视图），点趋势才跳视图。
 *
 * 涨跌幅容错（plan-05 §3）：明细列 changePercent 首版可能 null（数据源 fund_daily 不可用），
 * 列对 null 容错显示 "-"，E2E 不要求该列有值。
 *
 * data-testid 约定（spec 选择器依赖，命名必须与 etf-monitor.spec.ts 一致）：
 * - 表格根容器：etf-index-ranking-table
 * - 排序按钮：etf-sort-{sortKey}（netInflow / shareChange / share）
 * - 指数行展开标记：etf-expand-{indexName}
 * - 指数行趋势入口：etf-trend-entry-{indexName}
 * - 明细行：etf-detail-row-{tsCode}
 * - 明细行趋势入口：etf-detail-trend-{tsCode}
 * - 错误态：etf-ranking-error / etf-ranking-retry
 * - 空态：etf-ranking-empty
 */
import React from 'react'
import { ChevronRightIcon } from 'lucide-react'
import type {
  EtfIndexRankingItem,
  EtfDetailItem,
  EtfSortBy,
} from '@/types/etfMonitorTypes'
import { useEtfIndexDetail } from '@/hooks/useEtfMonitor'

/** 排序方向（etfMonitorTypes 未单独导出别名，此处沿用内联字面量与 useEtfIndexRankings 一致） */
type EtfOrder = 'desc' | 'asc'
import {
  formatShare,
  formatAmount,
  formatSignedAmount,
  formatPercent,
  formatPrice,
  getAmountColorClass,
} from './helpers'

export interface EtfTrendTarget {
  type: 'index' | 'etf'
  code: string
  /** 对象显示名（指数名 / ETF 简称），用于选择器与定位提示 */
  name?: string
}

export interface EtfIndexRankingTableProps {
  items: EtfIndexRankingItem[]
  total: number
  page: number
  pageSize: number
  sortBy: EtfSortBy
  order: EtfOrder
  loading: boolean
  error: boolean
  hasData: boolean
  /** 当前展开的指数 code（null=全部收起） */
  expandedIndex: string | null
  /** 交易日（透传给明细 hook） */
  tradeDate?: string | null
  onSort: (sortBy: EtfSortBy, order: EtfOrder) => void
  onExpand: (indexCode: string | null) => void
  /** AC-11：趋势入口回调（指数/ETF） */
  onTrend: (target: EtfTrendTarget) => void
  onRetry: () => void
  onPaginate: (page: number) => void
}

export default function EtfIndexRankingTable({
  items,
  total,
  page,
  pageSize,
  sortBy,
  order,
  loading,
  error,
  hasData,
  expandedIndex,
  tradeDate,
  onSort,
  onExpand,
  onTrend,
  onRetry,
  onPaginate,
}: EtfIndexRankingTableProps) {
  // 明细数据：仅当有展开指数时拉取（条件 hook，indexCode=null 不发请求）
  const { detail, isLoading: isDetailLoading, isError: isDetailError } =
    useEtfIndexDetail({
      indexCode: expandedIndex,
      tradeDate,
    })

  // AC-03：当前列切换升降序，其它列切过去默认降序
  const handleSortClick = (column: EtfSortBy) => {
    if (column === sortBy) {
      onSort(column, order === 'asc' ? 'desc' : 'asc')
    } else {
      onSort(column, 'desc')
    }
  }

  // AC-04：展开/收起（点展开标记不跳视图）
  const handleExpand = (indexName: string) => {
    onExpand(expandedIndex === indexName ? null : indexName)
  }

  // 明细行（按 netInflow desc 排序，与表格展开默认一致）
  const detailItems: EtfDetailItem[] = React.useMemo(() => {
    const list = detail?.items ?? []
    return [...list].sort((a, b) => (b.netInflow ?? 0) - (a.netInflow ?? 0))
  }, [detail])

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div data-testid="etf-index-ranking-table" className="space-y-3">
      {/* 加载骨架 */}
      {loading && (
        <div className="overflow-hidden rounded-lg border border-border bg-card">
          <table className="w-full text-sm">
            <thead className="bg-background border-b border-border">
              <tr>
                {['指数名称', 'ETF数', '合计份数', '合计份额', '合计份额变化', '合计净流入额', '操作'].map(
                  (label) => (
                    <th
                      key={label}
                      className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left"
                    >
                      {label}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary">
              {Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 7 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-secondary/60 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 错误态 + 重试（AC-10，独立降级，由父组件提供 mutate） */}
      {!loading && error && (
        <div className="p-8 text-center" data-testid="etf-ranking-error">
          <p className="text-sm text-muted-foreground mb-3">⚠ ETF 数据加载失败</p>
          <button
            type="button"
            onClick={onRetry}
            data-testid="etf-ranking-retry"
            className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
          >
            重试
          </button>
        </div>
      )}

      {/* 空态（AC-05：无数据日期 hasData=false） */}
      {!loading && !error && !hasData && (
        <div className="p-12 text-center" data-testid="etf-ranking-empty">
          <p className="text-lg font-medium text-foreground mb-2">该日期暂无 ETF 数据</p>
          <p className="text-sm text-muted-foreground">
            请切换其他交易日，或等待数据更新
          </p>
        </div>
      )}

      {/* 数据表 */}
      {!loading && !error && hasData && items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <table className="w-full text-sm">
            <thead className="bg-background border-b border-border">
              <tr>
                <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                  指数名称
                </th>
                <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-right">
                  ETF 数
                </th>
                {/* 合计份数（可排序） */}
                <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-right">
                  <SortButton
                    sortKey="share"
                    label="合计份数"
                    activeSort={sortBy}
                    order={order}
                    onClick={handleSortClick}
                  />
                </th>
                {/* 合计份额（亿元，存量指标，不可排序） */}
                <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-right">
                  合计份额
                </th>
                {/* 合计份额变化（可排序） */}
                <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-right">
                  <SortButton
                    sortKey="shareChange"
                    label="合计份额变化"
                    activeSort={sortBy}
                    order={order}
                    onClick={handleSortClick}
                  />
                </th>
                {/* 合计净流入额（可排序，默认） */}
                <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-right">
                  <SortButton
                    sortKey="netInflow"
                    label="合计净流入额"
                    activeSort={sortBy}
                    order={order}
                    onClick={handleSortClick}
                  />
                </th>
                <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary">
              {items.map((item) => {
                const shareColor = getAmountColorClass(item.totalShareChange)
                const inflowColor = getAmountColorClass(item.totalNetInflow)
                const expanded = expandedIndex === item.indexCode
                return (
                  <React.Fragment key={item.indexCode}>
                    <tr className="hover:bg-background/80 transition-colors">
                      <td className="px-4 py-3 min-w-[7rem] whitespace-nowrap font-medium text-foreground">
                        {item.indexName}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-foreground">
                        {item.etfCount}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-foreground">
                        {formatShare(item.totalShare)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-foreground">
                        {formatAmount(item.totalSize)}
                      </td>
                      <td className={`px-4 py-3 text-right tabular-nums font-medium ${shareColor}`}>
                        {formatSignedAmount(item.totalShareChange, '亿份')}
                      </td>
                      <td className={`px-4 py-3 text-right tabular-nums font-medium ${inflowColor}`}>
                        {formatSignedAmount(item.totalNetInflow, '亿元')}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-3">
                          {/* 展开标记（与趋势入口分离，点展开不跳视图） */}
                          <button
                            type="button"
                            onClick={() => handleExpand(item.indexCode)}
                            data-testid={`etf-expand-${item.indexCode}`}
                            className="inline-flex items-center gap-0.5 text-sm text-muted-foreground hover:text-foreground"
                            aria-label={expanded ? `收起 ${item.indexName} 明细` : `展开 ${item.indexName} 明细`}
                            aria-expanded={expanded}
                          >
                            <ChevronRightIcon
                              className={`w-4 h-4 transition-transform ${expanded ? 'rotate-90' : ''}`}
                            />
                            {expanded ? '收起' : '展开'}
                          </button>
                          {/* 趋势入口（指数 → target_type=index，code 用 indexCode） */}
                          <button
                            type="button"
                            onClick={() =>
                              onTrend({
                                type: 'index',
                                code: item.indexCode,
                                name: item.indexName,
                              })
                            }
                            data-testid={`etf-trend-entry-${item.indexCode}`}
                            className="text-sm text-primary hover:underline"
                          >
                            趋势
                          </button>
                        </div>
                      </td>
                    </tr>
                    {/* 展开明细行（跟随指数行渲染） */}
                    {expanded && (
                      <tr key={`${item.indexCode}-detail`}>
                        <td colSpan={7} className="px-4 py-3 bg-background/50">
                          <DetailPanel
                            indexName={item.indexName}
                            items={detailItems}
                            loading={isDetailLoading}
                            error={isDetailError}
                            onTrend={onTrend}
                          />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* 分页（AC-13） */}
      {!loading && !error && hasData && items.length > 0 && (
        <div
          className="flex items-center justify-between gap-3 pt-1"
          data-testid="etf-pagination"
        >
          <div className="text-xs text-muted-foreground" data-testid="etf-page-info">
            第 {page} / {totalPages} 页 · 共 {total} 条
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onPaginate(Math.max(1, page - 1))}
              disabled={page <= 1}
              data-testid="etf-prev-page"
              className="px-3 py-1.5 text-sm font-medium rounded-lg border border-border bg-background hover:bg-secondary text-foreground disabled:opacity-40 disabled:cursor-not-allowed"
            >
              上一页
            </button>
            <button
              type="button"
              onClick={() => onPaginate(Math.min(totalPages, page + 1))}
              disabled={page >= totalPages}
              data-testid="etf-next-page"
              className="px-3 py-1.5 text-sm font-medium rounded-lg border border-border bg-background hover:bg-secondary text-foreground disabled:opacity-40 disabled:cursor-not-allowed"
            >
              下一页
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ---- 排序表头按钮（三态箭头）----
function SortButton({
  sortKey,
  label,
  activeSort,
  order,
  onClick,
}: {
  sortKey: EtfSortBy
  label: string
  activeSort: EtfSortBy
  order: EtfOrder
  onClick: (s: EtfSortBy) => void
}) {
  const active = sortKey === activeSort
  const arrow = active ? (order === 'desc' ? '▼' : '▲') : ''
  return (
    <button
      type="button"
      onClick={() => onClick(sortKey)}
      data-testid={`etf-sort-${sortKey}`}
      className={`inline-flex items-center gap-1 ${
        active ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
      }`}
    >
      {label}
      {arrow && <span aria-hidden>{arrow}</span>}
    </button>
  )
}

// ---- 明细面板（指数展开后渲染）----
function DetailPanel({
  indexName,
  items,
  loading,
  error,
  onTrend,
}: {
  indexName: string
  items: EtfDetailItem[]
  loading: boolean
  error: boolean
  onTrend: (t: EtfTrendTarget) => void
}) {
  if (loading) {
    return (
      <div className="text-sm text-muted-foreground py-3">
        加载 {indexName} ETF 明细...
      </div>
    )
  }
  if (error) {
    return (
      <div className="text-sm text-muted-foreground py-3">
        {indexName} 明细加载失败
      </div>
    )
  }
  if (items.length === 0) {
    return (
      <div className="text-sm text-muted-foreground py-3">
        {indexName} 暂无 ETF 明细
      </div>
    )
  }
  return (
    <div className="overflow-x-auto rounded-md border border-border bg-card">
      <table className="w-full text-sm">
        <thead className="bg-background border-b border-border">
          <tr>
            {['基金代码', '简称', '净值', '份额', '规模', '份额变化', '净流入额', '涨跌幅', '操作'].map(
              (label) => (
                <th
                  key={label}
                  className="px-3 py-2 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left"
                >
                  {label}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-secondary">
          {items.map((d) => {
            const shareColor = getAmountColorClass(d.shareChange)
            const inflowColor = getAmountColorClass(d.netInflow)
            const changeColor = getAmountColorClass(d.changePercent)
            return (
              <tr
                key={d.tsCode}
                data-testid={`etf-detail-row-${d.tsCode}`}
                className="hover:bg-background/80 transition-colors"
              >
                <td className="px-3 py-2 tabular-nums text-foreground whitespace-nowrap">
                  {d.tsCode}
                </td>
                <td className="px-3 py-2 min-w-[8rem] whitespace-nowrap text-foreground">
                  {d.name}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-foreground">
                  {formatPrice(d.unitNav)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-foreground">
                  {formatShare(d.share)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-foreground">
                  {formatAmount(d.totalSize)}
                </td>
                <td className={`px-3 py-2 text-right tabular-nums font-medium ${shareColor}`}>
                  {formatSignedAmount(d.shareChange, '亿份')}
                </td>
                <td className={`px-3 py-2 text-right tabular-nums font-medium ${inflowColor}`}>
                  {formatSignedAmount(d.netInflow, '亿元')}
                </td>
                {/* 涨跌幅容错：changePercent 首版可能 null → 显示 "-" */}
                <td className={`px-3 py-2 text-right tabular-nums ${changeColor}`}>
                  {formatPercent(d.changePercent)}
                </td>
                <td className="px-3 py-2 whitespace-nowrap">
                  {/* 趋势入口（AC-08/11：ETF → target_type=etf） */}
                  <button
                    type="button"
                    onClick={() => onTrend({ type: 'etf', code: d.tsCode, name: d.tsCode })}
                    data-testid={`etf-detail-trend-${d.tsCode}`}
                    className="text-sm text-primary hover:underline"
                  >
                    趋势
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
