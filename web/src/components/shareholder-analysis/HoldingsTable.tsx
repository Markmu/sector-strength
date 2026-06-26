'use client'

/**
 * 持仓股票列表（plan-04）
 *
 * 列：股票代码 | 名称 | 持股数量 | 占流通比 | 较上期（变动方向） | 行业
 * 顶部筛选栏：行业下拉（全部 + 各行业） | 变动方向下拉（全部/增持/减持/新进/退出）
 * 分页：复用 ui/Pagination 组件
 *
 * 变动方向渲染：↑增持(绿) | ↓减持(红) | ★新进(蓝) | ✕退出(灰) | —无数据（无上期或 unchanged 也归为 —）
 *
 * spec 选择器兼容：
 * - 表格用 <table>，表头列文案严格匹配 spec 的 getByText('股票代码'/'名称'/'持股数量'/'占流通比')
 * - 筛选栏 SimpleSelect 的 trigger 为 button，选项为 role=option（spec getByRole('option') 命中）
 * - 行业筛选 testid="industry-filter"，变动方向 testid="change-direction-filter"
 */
import React from 'react'
import Pagination from '@/components/ui/Pagination'
import SimpleSelect from '@/components/ui/SimpleSelect'
import { cn } from '@/lib/utils'
import type { ShareholderHoldingItem, ShareholderChangeDirection } from '@/lib/api'

export interface HoldingsTableFilters {
  industry?: string
  changeDirection?: string
}

export interface HoldingsTableProps {
  holdings: ShareholderHoldingItem[]
  total: number
  page: number
  pageSize: number
  industries: string[]
  filters: HoldingsTableFilters
  onFiltersChange: (filters: HoldingsTableFilters) => void
  onPageChange: (page: number) => void
  /** 每页条数变化回调（对齐基金分析页分页器） */
  onPageSizeChange: (size: number) => void
  hasPrevPeriod: boolean
}

// 变动方向下拉选项（value 对应后端 change_direction Query 值）
export const CHANGE_DIRECTION_OPTIONS = [
  { value: '', label: '全部方向' },
  { value: 'increase', label: '增持' },
  { value: 'decrease', label: '减持' },
  { value: 'new', label: '新进' },
  { value: 'exit', label: '退出' },
] as const

function formatAmount(amount: number): string {
  // 股数：>1万 用万单位
  if (amount >= 10000) {
    return `${(amount / 10000).toFixed(2)}万`
  }
  return amount.toLocaleString('zh-CN')
}

// 后端 hold_float_ratio / total_hold_float_ratio 已是百分数（如 5.23 表示 5.23%），
// 直接格式化即可，不再 ×100（与 FundPortfolioTable 一致）。
function formatRatio(ratio: number): string {
  return `${ratio.toFixed(2)}%`
}

function ChangeDirectionCell({
  direction,
  hasPrevPeriod,
}: {
  direction: ShareholderChangeDirection
  hasPrevPeriod: boolean
}) {
  if (!hasPrevPeriod) {
    return <span className="text-gray-400">—</span>
  }
  switch (direction) {
    case 'increase':
      return <span className="text-emerald-600 font-medium">↑增持</span>
    case 'decrease':
      return <span className="text-red-600 font-medium">↓减持</span>
    case 'new':
      return <span className="text-blue-600 font-medium">★新进</span>
    case 'exit':
      return <span className="text-gray-500 font-medium">✕退出</span>
    case 'unchanged':
    case null:
    default:
      return <span className="text-gray-400">—</span>
  }
}

export default function HoldingsTable({
  holdings,
  total,
  page,
  pageSize,
  industries,
  filters,
  onFiltersChange,
  onPageChange,
  onPageSizeChange,
  hasPrevPeriod,
}: HoldingsTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  const industryOptions = [
    { value: '', label: '全部行业' },
    ...industries.map((ind) => ({ value: ind, label: ind })),
  ]

  return (
    <div className="space-y-3">
      {/* 筛选栏 */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium text-muted-foreground">筛选</span>
        <SimpleSelect
          value={filters.industry ?? ''}
          options={industryOptions}
          onChange={(val) =>
            onFiltersChange({
              ...filters,
              industry: val || undefined,
            })
          }
          placeholder="全部行业"
          testId="industry-filter"
          ariaLabel="行业筛选"
        />
        <SimpleSelect
          value={filters.changeDirection ?? ''}
          options={[...CHANGE_DIRECTION_OPTIONS]}
          onChange={(val) =>
            onFiltersChange({
              ...filters,
              changeDirection: val || undefined,
            })
          }
          placeholder="全部方向"
          testId="change-direction-filter"
          ariaLabel="变动方向筛选"
        />
      </div>

      {/* 数据表格 */}
      <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-background border-b border-border">
              <tr>
                {['股票代码', '名称', '持股数量', '占流通比', '较上期', '行业'].map(
                  (h) => (
                    <th
                      key={h}
                      className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left"
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-secondary">
              {holdings.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-10 text-center text-muted-foreground"
                  >
                    该组暂无持仓数据
                  </td>
                </tr>
              ) : (
                holdings.map((h) => (
                  <tr
                    key={h.symbol}
                    className="hover:bg-background/80 transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-foreground">
                      {h.symbol}
                    </td>
                    <td className="px-4 py-3 text-foreground">{h.stockName}</td>
                    <td className="px-4 py-3 text-foreground">
                      {formatAmount(h.totalHoldAmount)}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatRatio(h.totalHoldFloatRatio)}
                    </td>
                    <td className="px-4 py-3">
                      <ChangeDirectionCell
                        direction={h.changeDirection}
                        hasPrevPeriod={hasPrevPeriod}
                      />
                    </td>
                    <td
                      className={cn(
                        'px-4 py-3 text-muted-foreground max-w-[200px] truncate'
                      )}
                      title={h.industries.join(', ') || undefined}
                    >
                      {h.industries.length > 0 ? h.industries.join(', ') : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 分页 */}
      <Pagination
        currentPage={page}
        totalPages={totalPages}
        total={total}
        pageSize={pageSize}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
        showPageSizeSelector
        showJumpToPage
      />
    </div>
  )
}
