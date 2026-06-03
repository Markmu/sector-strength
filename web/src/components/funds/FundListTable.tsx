'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { Fund } from '@/lib/api'
import {
  SearchIcon,
  InboxIcon,
  AlertTriangleIcon,
  ExternalLinkIcon,
} from 'lucide-react'

export interface FundListTableProps {
  funds: Fund[]
  isLoading: boolean
  isError?: boolean
  hasSearch: boolean
  className?: string
}

/**
 * 基金列表表格组件
 *
 * 列：代码、名称、类型、跟踪标的、管理人、成立日期、操作
 * 空状态：加载骨架 / 搜索无结果 / 列表为空
 * hasPortfolio=false 时标注"暂无数据"
 */
export default function FundListTable({
  funds,
  isLoading,
  isError,
  hasSearch,
  className,
}: FundListTableProps) {
  const router = useRouter()

  const handleViewDetail = (tsCode: string) => {
    router.push(`/dashboard/funds/${encodeURIComponent(tsCode)}`)
  }

  // 骨架加载态
  if (isLoading) {
    return (
      <div
        className={`bg-card rounded-xl border border-border shadow-sm overflow-hidden ${
          className || ''
        }`}
      >
        <table className="w-full text-sm">
          <thead className="bg-background border-b border-border">
            <tr>
              {['代码', '名称', '类型', '跟踪标的', '管理人', '成立日期', '操作'].map(
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
    )
  }

  // 错误态
  if (isError) {
    return (
      <div
        className={`bg-card rounded-xl border border-border shadow-sm p-12 text-center ${
          className || ''
        }`}
      >
        <AlertTriangleIcon className="w-12 h-12 mx-auto mb-3 text-amber-500" />
        <p className="text-lg font-medium text-foreground mb-2">加载失败，请重试</p>
        <p className="text-sm text-muted-foreground">
          网络请求异常，请检查网络连接后刷新页面
        </p>
      </div>
    )
  }

  // 空态：搜索无结果
  if (funds.length === 0 && hasSearch) {
    return (
      <div
        className={`bg-card rounded-xl border border-border shadow-sm p-12 text-center ${
          className || ''
        }`}
      >
        <SearchIcon className="w-12 h-12 mx-auto mb-3 text-faint" />
        <p className="text-lg font-medium text-foreground mb-2">未找到匹配基金</p>
        <p className="text-sm text-muted-foreground">
          请调整搜索词或清除过滤项
        </p>
      </div>
    )
  }

  // 空态：列表为空（无数据）
  if (funds.length === 0) {
    return (
      <div
        className={`bg-card rounded-xl border border-border shadow-sm p-12 text-center ${
          className || ''
        }`}
      >
        <InboxIcon className="w-12 h-12 mx-auto mb-3 text-faint" />
        <p className="text-lg font-medium text-foreground mb-2">暂无基金数据</p>
        <p className="text-sm text-muted-foreground">
          请管理员先在管理后台执行同步
        </p>
      </div>
    )
  }

  // 数据表格
  return (
    <div
      className={`bg-card rounded-xl border border-border shadow-sm overflow-hidden ${
        className || ''
      }`}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-background border-b border-border">
            <tr>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                代码
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                名称
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                类型
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                跟踪标的
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                管理人
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-left">
                成立日期
              </th>
              <th className="px-4 py-3 font-semibold text-muted-foreground text-xs uppercase tracking-wider text-center">
                操作
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-secondary">
            {funds.map((fund) => (
              <tr
                key={fund.tsCode}
                className="hover:bg-background/80 transition-colors cursor-pointer"
                onClick={() => handleViewDetail(fund.tsCode)}
              >
                <td className="px-4 py-3 font-mono text-foreground">
                  {fund.tsCode}
                </td>
                <td className="px-4 py-3 text-foreground">
                  <span className="font-medium">{fund.name}</span>
                  {fund.hasPortfolio === false && (
                    <span className="ml-2 inline-flex items-center px-1.5 py-0.5 text-xs bg-amber-100 text-amber-700 rounded">
                      暂无数据
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {fund.fundType || '-'}
                </td>
                <td
                  className="px-4 py-3 text-muted-foreground max-w-[200px] truncate"
                  title={fund.benchmark || undefined}
                >
                  {fund.benchmark || '-'}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {fund.management || '-'}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {fund.foundDate || '-'}
                </td>
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleViewDetail(fund.tsCode)
                    }}
                    className="inline-flex items-center gap-1 text-primary hover:text-primary/80 text-sm font-medium transition-colors"
                  >
                    详情
                    <ExternalLinkIcon className="w-3 h-3" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
