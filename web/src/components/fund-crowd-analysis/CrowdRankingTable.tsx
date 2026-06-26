'use client'

/**
 * 扎堆度排行榜表格（plan-02，AC-01/03/06/08）
 *
 * 列：排名 / 代码 / 名称 / 行业 / 持有基金数 / 环比变化 / 操作（反查）
 *
 * 环比列三态渲染（AC-03 + AC-06，先 hasPrevPeriod 再 isNew 再数值）：
 * 1. hasPrevPeriod=false → 统一 "—"
 * 2. isNew=true → "★ 新进"
 * 3. 正常 → 基金 ±N（含方向箭头）
 *
 * data-testid 约定（spec 选择器依赖）：
 * - 表格根容器：crowd-ranking-table
 * - 搜索框：crowd-search-input / crowd-search-clear
 * - 环比单元格：crowd-change-cell-{stockSymbol}
 * - 新进标识：crowd-new-badge-{stockSymbol}
 * - 反查按钮：crowd-reverse-lookup-{stockSymbol}
 */
import React from 'react'
import { SearchIcon } from 'lucide-react'
import Pagination from '@/components/ui/Pagination'
import SimpleSelect from '@/components/ui/SimpleSelect'
import type { SimpleSelectOption } from '@/components/ui/SimpleSelect'
import type { CrowdRankingItem } from '@/lib/api'

export interface CrowdRankingTableProps {
  items: CrowdRankingItem[]
  total: number
  page: number
  pageSize: number
  isLoading: boolean
  isError: boolean
  /** AC-06：false 时环比列统一 "—" */
  hasPrevPeriod: boolean
  search: string
  /** 板块分类列标题（随 sector_type 切换：行业/概念/地域） */
  sectorTypeLabel: string
  /** 板块筛选当前值（undefined = 全部） */
  sectorName?: string
  /** 板块筛选下拉选项（随 sector_type 变化） */
  sectorOptions: SimpleSelectOption[]
  onSearchChange: (value: string) => void
  /** 板块筛选变化回调 */
  onSectorNameChange: (value: string) => void
  onPageChange: (page: number) => void
  /** 每页条数变化回调（对齐基金分析页分页器） */
  onPageSizeChange: (size: number) => void
  /** 反查回调：父组件 wire 到 plan-03 的路由跳转；plan-02 仅渲染按钮 + 触发回调 */
  onReverseLookup: (stockSymbol: string) => void
}

/** 环比列渲染（AC-03 + AC-06，先 hasPrevPeriod 再 isNew 再数值） */
function renderChangeColumn(
  item: CrowdRankingItem,
  hasPrevPeriod: boolean
): React.ReactNode {
  // AC-06：上期完全缺失 → 统一 "—"
  if (!hasPrevPeriod) {
    return <span className="text-muted-foreground">—</span>
  }
  // AC-03：新进（is_new=true，上期无记录）→ "新进" 标识
  if (item.isNew === true) {
    return (
      <span
        className="inline-flex items-center gap-1 text-blue-600"
        data-testid={`crowd-new-badge-${item.stockSymbol}`}
      >
        ★ 新进
      </span>
    )
  }
  // AC-03：正常环比（基金数）
  const countChange = item.fundCountChange
  const direction =
    countChange !== null && countChange > 0
      ? 'up'
      : countChange !== null && countChange < 0
        ? 'down'
        : 'flat'
  const arrow = direction === 'up' ? '↑' : direction === 'down' ? '↓' : '→'
  const colorClass =
    direction === 'up'
      ? 'text-green-600'
      : direction === 'down'
        ? 'text-red-600'
        : 'text-muted-foreground'
  const countText =
    countChange !== null
      ? countChange > 0
        ? `+${countChange}`
        : `${countChange}`
      : '—'
  return (
    <span className={`inline-flex items-center gap-2 text-sm ${colorClass}`}>
      <span>
        基金 {countText} {arrow}
      </span>
    </span>
  )
}

export default function CrowdRankingTable({
  items,
  total,
  page,
  pageSize,
  isLoading,
  isError,
  hasPrevPeriod,
  search,
  sectorTypeLabel,
  sectorName,
  sectorOptions,
  onSearchChange,
  onSectorNameChange,
  onPageChange,
  onPageSizeChange,
  onReverseLookup,
}: CrowdRankingTableProps) {
  const totalPages = pageSize > 0 ? Math.max(1, Math.ceil(total / pageSize)) : 1

  return (
    <div data-testid="crowd-ranking-table" className="space-y-3">
      {/* 搜索框 + 板块筛选（AC-08） */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <SearchIcon className="w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="搜索股票代码或名称"
            className="block w-64 text-sm border rounded-lg px-3 py-2 border-border bg-card text-foreground placeholder-muted-foreground/70 focus:outline-none focus:ring-2 focus:ring-primary/40"
            data-testid="crowd-search-input"
          />
          {search && (
            <button
              type="button"
              onClick={() => onSearchChange('')}
              className="text-sm text-muted-foreground hover:text-foreground"
              data-testid="crowd-search-clear"
            >
              清空
            </button>
          )}
        </div>
        <SimpleSelect
          value={sectorName ?? ''}
          options={sectorOptions}
          onChange={onSectorNameChange}
          ariaLabel="板块筛选"
          testId="crowd-sector-filter"
        />
      </div>

      {/* 加载骨架 */}
      {isLoading && (
        <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-background border-b border-border">
              <tr>
                {['排名', '代码', '名称', sectorTypeLabel, '持有基金数', '环比变化', '操作'].map(
                  (h) => (
                    <th
                      key={h}
                      className={`px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left${
                        h === '名称' ? ' min-w-[7rem] whitespace-nowrap' : ''
                      }`}
                    >
                      {h}
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

      {/* 错误态 */}
      {!isLoading && isError && (
        <div className="bg-card rounded-xl border border-border shadow-sm p-8 text-center">
          <p className="text-sm text-muted-foreground">加载失败，请重试</p>
        </div>
      )}

      {/* 搜索无结果（AC-08 边界：items 为空但 search 非空，区别于 AC-07 整页空状态） */}
      {!isLoading && !isError && items.length === 0 && search && (
        <div className="bg-card rounded-xl border border-border shadow-sm p-12 text-center">
          <SearchIcon className="w-12 h-12 mx-auto mb-3 text-muted-foreground/60" />
          <p className="text-lg font-medium text-foreground mb-2">未找到匹配股票</p>
          <p className="text-sm text-muted-foreground">
            请调整搜索词，或清空搜索词恢复完整榜单
          </p>
        </div>
      )}

      {/* 表格 */}
      {!isLoading && !isError && items.length > 0 && (
        <>
          <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-background border-b border-border">
                  <tr>
                    <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                      排名
                    </th>
                    <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                      代码
                    </th>
                    <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left min-w-[7rem] whitespace-nowrap">
                      名称
                    </th>
                    <th
                      data-testid="crowd-ranking-column-sector"
                      className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left"
                    >
                      {sectorTypeLabel}
                    </th>
                    <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-right">
                      持有基金数
                    </th>
                    <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                      环比变化
                    </th>
                    <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary">
                  {items.map((item, idx) => {
                    const rank = (page - 1) * pageSize + idx + 1
                    return (
                      <tr
                        key={item.stockSymbol}
                        className="hover:bg-background/80 transition-colors"
                      >
                        <td className="px-4 py-3 text-muted-foreground">{rank}</td>
                        <td className="px-4 py-3 font-mono text-foreground">
                          {item.stockSymbol}
                        </td>
                        <td className="px-4 py-3 text-foreground min-w-[7rem] whitespace-nowrap">
                          {item.stockName ?? '—'}
                        </td>
                        <td className="px-4 py-3 text-foreground">
                          {item.industries.length > 0
                            ? item.industries.join('、')
                            : '—'}
                        </td>
                        <td className="px-4 py-3 text-right font-medium text-foreground">
                          {item.fundCount}
                        </td>
                        <td
                          className="px-4 py-3 text-foreground"
                          data-testid={`crowd-change-cell-${item.stockSymbol}`}
                        >
                          {renderChangeColumn(item, hasPrevPeriod)}
                        </td>
                        <td className="px-4 py-3">
                          <button
                            type="button"
                            onClick={() => onReverseLookup(item.stockSymbol)}
                            data-testid={`crowd-reverse-lookup-${item.stockSymbol}`}
                            className="text-sm text-primary hover:underline"
                          >
                            反查
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* 分页器 */}
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
        </>
      )}
    </div>
  )
}
