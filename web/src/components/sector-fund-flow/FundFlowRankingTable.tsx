'use client'

/**
 * 资金流排行榜表格（plan-03，AC-01/03/10）
 *
 * 列：排名 / 板块名（可跳转）/ 涨跌幅 / 流入 / 流出 / 净额（排序）/ 公司家数 / 领涨股 / 领涨股涨跌幅
 *
 * 交互：
 * - AC-03：点击 流入/流出/净额 表头切换排序 + 箭头；不可排序列无反应
 * - AC-10：板块名可点击跳转 /dashboard/sector-analysis/{id}（点击时单独查 sector_id）
 * - 不分页，全量展示（父组件一次拉取全部板块）
 * - 净额正值红、负值绿（A 股惯例）；流入/流出中性色
 *
 * data-testid 约定（spec 选择器依赖）：
 * - 表格根容器：fund-flow-ranking-table
 * - 排序按钮：fund-flow-sort-{sortBy}
 * - 板块名跳转：fund-flow-sector-link-{sectorName}
 */
import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { sectorsApi } from '@/lib/api'
import type { FundFlowRankingItem, FundFlowSortBy, FundFlowOrder } from '@/types/fundFlowTypes'
import {
  formatAmount,
  formatSignedAmount,
  formatPercent,
  formatPrice,
  getAmountColorClass,
} from './helpers'

// 表头列：声明顺序与是否可排序（仅 流入/流出/净额 可排序）
interface ColumnDef {
  key: string
  label: string
  sortable: boolean
  sortKey?: FundFlowSortBy
  align?: 'left' | 'right'
}
const COLUMNS: ColumnDef[] = [
  { key: 'rank', label: '排名', sortable: false, align: 'left' },
  { key: 'sectorName', label: '板块名称', sortable: false, align: 'left' },
  { key: 'changePercent', label: '涨跌幅', sortable: false, align: 'right' },
  { key: 'inflow', label: '流入', sortable: true, sortKey: 'inflow', align: 'right' },
  { key: 'outflow', label: '流出', sortable: true, sortKey: 'outflow', align: 'right' },
  { key: 'netInflow', label: '净额', sortable: true, sortKey: 'net_inflow', align: 'right' },
  { key: 'companyCount', label: '公司家数', sortable: false, align: 'right' },
  { key: 'leadingStock', label: '领涨股', sortable: false, align: 'left' },
  { key: 'leadingStockChange', label: '领涨涨跌幅', sortable: false, align: 'right' },
]

export interface FundFlowRankingTableProps {
  items: FundFlowRankingItem[]
  isLoading: boolean
  isError: boolean
  hasData: boolean
  sortBy: FundFlowSortBy
  order: FundFlowOrder
  onSortChange: (sortBy: FundFlowSortBy, order: FundFlowOrder) => void
  /** AC-09：失败重试（父组件 wire 到 rankings mutate） */
  onRetry: () => void
}

export default function FundFlowRankingTable({
  items,
  isLoading,
  isError,
  hasData,
  sortBy,
  order,
  onSortChange,
  onRetry,
}: FundFlowRankingTableProps) {
  const router = useRouter()
  // 跳转中正在查询 id 的板块名（防止重复点击 + 给 loading 反馈）
  const [navigatingSector, setNavigatingSector] = useState<string | null>(null)

  // AC-03：当前列切换升降序，其它列切过去默认降序
  const handleSortClick = (column: FundFlowSortBy) => {
    if (column === sortBy) {
      onSortChange(column, order === 'asc' ? 'desc' : 'asc')
    } else {
      onSortChange(column, 'desc')
    }
  }

  // 跳转：rankings 不再 JOIN sectors 取 id，点击时单独按 name+industry 精确查 id。
  // 查到后跳转强度分析页；查不到或失败则不跳转（数据验证 industry 板块名 100% 命中）。
  const handleSectorClick = async (item: FundFlowRankingItem) => {
    if (navigatingSector) return
    setNavigatingSector(item.sectorName)
    try {
      const res = await sectorsApi.lookupSectorByName(item.sectorName, 'industry')
      const sectorId = res.data?.data?.sector_id
      if (sectorId) {
        router.push(`/dashboard/sector-analysis/${sectorId}`)
      }
    } catch {
      // 查询失败静默处理（不阻断其它板块操作）
    } finally {
      setNavigatingSector(null)
    }
  }

  const alignClass = (align?: 'left' | 'right') =>
    align === 'right' ? 'text-right' : 'text-left'

  return (
    <div
      data-testid="fund-flow-ranking-table"
      className="space-y-3"
    >
      {/* 加载骨架 */}
      {isLoading && (
        <div className="overflow-hidden rounded-lg border border-border bg-card">
          <table className="w-full text-sm">
            <thead className="bg-background border-b border-border">
              <tr>
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    className={`px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider ${alignClass(
                      col.align
                    )}`}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary">
              {Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: COLUMNS.length }).map((_, j) => (
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

      {/* 错误态 + 重试（AC-09，独立降级，由父组件提供 mutate） */}
      {!isLoading && isError && (
        <div className="p-8 text-center" data-testid="fund-flow-ranking-error">
          <p className="text-sm text-muted-foreground mb-3">排行榜加载失败</p>
          <button
            type="button"
            onClick={onRetry}
            data-testid="fund-flow-ranking-retry"
            className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
          >
            重试
          </button>
        </div>
      )}

      {/* 空态（AC-04：无数据日期） */}
      {!isLoading && !isError && !hasData && (
        <div className="p-12 text-center" data-testid="fund-flow-ranking-empty">
          <p className="text-lg font-medium text-foreground mb-2">该日期暂无资金流数据</p>
          <p className="text-sm text-muted-foreground">
            请切换其他交易日，或等待盘中数据更新
          </p>
        </div>
      )}

      {/* 数据表（全量展示，不分页） */}
      {!isLoading && !isError && hasData && items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <table className="w-full text-sm">
            <thead className="bg-background border-b border-border">
              <tr>
                {COLUMNS.map((col) => {
                  const active = col.sortable && col.sortKey === sortBy
                  const arrow = active ? (order === 'desc' ? '▼' : '▲') : ''
                  const baseClass = `px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider ${alignClass(
                    col.align
                  )}`
                  if (!col.sortable || !col.sortKey) {
                    return (
                      <th key={col.key} className={baseClass}>
                        {col.label}
                      </th>
                    )
                  }
                  return (
                    <th key={col.key} className={baseClass}>
                      <button
                        type="button"
                        onClick={() => handleSortClick(col.sortKey as FundFlowSortBy)}
                        data-testid={`fund-flow-sort-${col.sortKey}`}
                        className={`inline-flex items-center gap-1 ${
                          active
                            ? 'text-foreground'
                            : 'text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        {col.label}
                        {arrow && <span aria-hidden>{arrow}</span>}
                      </button>
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary">
              {items.map((item) => {
                const netColor = getAmountColorClass(item.netInflow)
                const changeColor = getAmountColorClass(item.changePercent)
                const leadingChangeColor = getAmountColorClass(item.leadingStockChange)
                const isNavigating = navigatingSector === item.sectorName
                return (
                  <tr
                    key={`${item.rank}-${item.sectorName}`}
                    className="hover:bg-background/80 transition-colors"
                  >
                    <td className="px-4 py-3 text-muted-foreground tabular-nums">
                      {item.rank}
                    </td>
                    <td className="px-4 py-3 min-w-[7rem] whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => handleSectorClick(item)}
                        disabled={isNavigating || navigatingSector !== null}
                        data-testid={`fund-flow-sector-link-${item.sectorName}`}
                        className="text-primary hover:underline font-medium disabled:opacity-50 disabled:cursor-wait"
                        title={isNavigating ? '正在查询板块…' : '跳转板块强度分析'}
                      >
                        {item.sectorName}
                      </button>
                    </td>
                    <td className={`px-4 py-3 tabular-nums ${changeColor}`}>
                      {formatPercent(item.changePercent)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-foreground">
                      {formatAmount(item.inflow)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-foreground">
                      {formatAmount(item.outflow)}
                    </td>
                    <td className={`px-4 py-3 text-right tabular-nums font-medium ${netColor}`}>
                      {formatSignedAmount(item.netInflow)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-foreground">
                      {item.companyCount ?? '-'}
                    </td>
                    <td className="px-4 py-3 text-foreground min-w-[6rem] whitespace-nowrap">
                      {item.leadingStock ?? '-'}
                    </td>
                    <td className={`px-4 py-3 text-right tabular-nums ${leadingChangeColor}`}>
                      {formatPercent(item.leadingStockChange)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
