'use client'

/**
 * 板块成分股列表（AC-01 ~ AC-06）。
 *
 * 在板块详情页强度/均线图表下方呈现成分股明细：
 * - 六列：代码 / 名称 / 强度分 / 趋势 / 最新价 / 市值
 * - 排序：强度分、市值可切换升降序（白名单），默认强度分降序（AC-01/02/03）
 * - 分页：复用 Pagination（currentPage/totalPages 自算），每页 20/50/100（AC-04）
 * - 三态：加载骨架 / 失败重试 / 空态（AC-05/06）
 * - 行点击：跳转个股分析页（item.id 为数据库主键）（AC-07 入口，落地由 plan-03 承接）
 *
 * 数据完全由后端驱动（ADR-1），独立 SWR hook 与图表互不阻塞（ADR-2）。
 * 复用 CrowdRankingTable 的三态/分页/data-testid 范式（ADR-3）。
 *
 * data-testid 约定（plan-04 E2E 选择器依赖）：
 * - 区块根：sector-stocks-table
 * - 表头排序按钮：sector-stocks-sort-{sortBy}
 * - 重试按钮：sector-stocks-retry
 * - 空态：sector-stocks-empty
 */
import { useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Pagination from '@/components/ui/Pagination'
import { useSectorStocks } from '@/hooks/useSectorStocks'
import {
  formatMarketCap,
  formatPrice,
  formatScore,
  getTrendDisplay,
} from './helpers'
import type { SectorStockItem } from '@/types/sectorTypes'

type SortBy = 'strength_score' | 'market_cap'
type SortOrder = 'asc' | 'desc'
type PageSize = 20 | 50 | 100

const PAGE_SIZE_OPTIONS: PageSize[] = [20, 50, 100]

// 表头列配置：声明列顺序与是否可排序（代码/名称/最新价/趋势 不可排序）
interface ColumnDef {
  key: string
  label: string
  sortable: boolean
  // sortable=true 时，点击使用的排序字段（须为 SortBy）
  sortKey?: SortBy
}
const COLUMNS: ColumnDef[] = [
  { key: 'symbol', label: '代码', sortable: false },
  { key: 'name', label: '名称', sortable: false },
  { key: 'strength_score', label: '强度分', sortable: true, sortKey: 'strength_score' },
  { key: 'trend', label: '趋势', sortable: false },
  { key: 'current_price', label: '最新价', sortable: false },
  { key: 'market_cap', label: '市值', sortable: true, sortKey: 'market_cap' },
]

export interface SectorStocksTableProps {
  sectorId: number
}

export default function SectorStocksTable({ sectorId }: SectorStocksTableProps) {
  const router = useRouter()
  const sectionRef = useRef<HTMLDivElement>(null)

  // 排序/分页 UI 状态（默认强度分降序）
  const [sortBy, setSortBy] = useState<SortBy>('strength_score')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState<PageSize>(20)

  const { data, isLoading, isError, mutate } = useSectorStocks({
    sectorId,
    sortBy,
    sortOrder,
    page,
    pageSize,
  })

  const items: SectorStockItem[] = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = pageSize > 0 ? Math.max(1, Math.ceil(total / pageSize)) : 1

  // 点击可排序表头：当前列切换升降序，其它列切过去并默认降序；同时重置到首页
  const handleSortClick = (column: SortBy) => {
    if (column === sortBy) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(column)
      setSortOrder('desc')
    }
    setPage(1)
  }

  const handlePageChange = (next: number) => {
    setPage(next)
    // 翻页后滚动到区块顶部
    sectionRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handlePageSizeChange = (size: number) => {
    setPageSize(size as PageSize)
    setPage(1) // 切每页条数从第 1 页开始
    sectionRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleRowClick = (item: SectorStockItem) => {
    // 用数据库主键 id（非 symbol），与后端 /stocks/{stock_id} 的 isdigit 校验一致
    router.push(`/dashboard/stock-analysis/${item.id}`)
  }

  return (
    <div
      ref={sectionRef}
      data-testid="sector-stocks-table"
      className="bg-card rounded-xl border border-border shadow-sm p-6 space-y-4"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-foreground">板块成分股</h3>
        {/* 总数始终显示，即使不足一页 */}
        <span className="text-sm text-muted-foreground">共 {total} 只</span>
      </div>

      {/* 加载骨架 */}
      {isLoading && (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-background border-b border-border">
              <tr>
                {['代码', '名称', '强度分', '趋势', '最新价', '市值'].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary">
              {Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 6 }).map((_, j) => (
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

      {/* 错误态 + 重试（AC-05，不影响上方图表） */}
      {!isLoading && isError && (
        <div className="p-8 text-center">
          <p className="text-sm text-muted-foreground mb-3">成分股加载失败</p>
          <button
            type="button"
            onClick={() => mutate()}
            data-testid="sector-stocks-retry"
            className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
          >
            重试
          </button>
        </div>
      )}

      {/* 空态（AC-06） */}
      {!isLoading && !isError && items.length === 0 && (
        <div
          className="p-12 text-center"
          data-testid="sector-stocks-empty"
        >
          <p className="text-lg font-medium text-foreground mb-2">该板块暂无成分股数据</p>
          <p className="text-sm text-muted-foreground">
            请先在数据管理页同步该板块的成分股
          </p>
        </div>
      )}

      {/* 数据表 + 分页器 */}
      {!isLoading && !isError && items.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
            <thead className="bg-background border-b border-border">
              <tr>
                {COLUMNS.map((col) => {
                  const active = col.sortable && col.sortKey === sortBy
                  const arrow = active ? (sortOrder === 'desc' ? '▼' : '▲') : ''
                  const baseClass =
                    'px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left'
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
                        onClick={() => handleSortClick(col.sortKey as SortBy)}
                        data-testid={`sector-stocks-sort-${col.sortKey}`}
                        className={`inline-flex items-center gap-1 ${
                          active ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
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
                  const trend = getTrendDisplay(item.trend_direction)
                  return (
                    <tr
                      key={item.id}
                      onClick={() => handleRowClick(item)}
                      className="hover:bg-background/80 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3 font-mono text-foreground">{item.symbol}</td>
                      <td className="px-4 py-3 text-foreground min-w-[7rem] whitespace-nowrap">
                        {item.name ?? '-'}
                      </td>
                      <td className="px-4 py-3 text-foreground">
                        {formatScore(item.strength_score)}
                      </td>
                      <td className={`px-4 py-3 ${trend.colorClass}`} title={trend.label}>
                        <span className="inline-flex items-center gap-1">
                          <span aria-hidden>{trend.arrow}</span>
                          {trend.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-foreground tabular-nums">
                        {formatPrice(item.current_price)}
                      </td>
                      <td className="px-4 py-3 text-foreground tabular-nums">
                        {formatMarketCap(item.market_cap)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* 分页器：有数据时始终渲染，让用户看到"共 N 只 / 第 X/Y 页"及每页条数选择。
              单页时 Pagination 内部自动隐藏页码按钮，但保留统计信息与每页条数选择器，
              方便用户切换为更大的每页条数（如 100）一次看全成分股。 */}
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            total={total}
            pageSize={pageSize}
            onPageChange={handlePageChange}
            onPageSizeChange={handlePageSizeChange}
            pageSizeOptions={PAGE_SIZE_OPTIONS}
            showPageSizeSelector
            showJumpToPage
          />
        </>
      )}
    </div>
  )
}
