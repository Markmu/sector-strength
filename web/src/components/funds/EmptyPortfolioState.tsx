'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { InboxIcon, RefreshCwIcon, ArrowLeftIcon } from 'lucide-react'

export interface EmptyPortfolioStateProps {
  /** 是否有任何持仓记录（历史） */
  hasPortfolio: boolean
  /** 当前持仓是否为空 */
  isPortfolioEmpty: boolean
  className?: string
}

/**
 * 暂无持仓数据空态组件
 *
 * 两种场景（架构 §6.2 修复项）：
 * - 场景 A（isPortfolioEmpty=true, hasPortfolio=false）：数据源未收录该基金
 * - 场景 B（isPortfolioEmpty=true, hasPortfolio=true）：当前报告期尚未披露
 */
export default function EmptyPortfolioState({
  hasPortfolio,
  isPortfolioEmpty,
  className,
}: EmptyPortfolioStateProps) {
  const router = useRouter()

  // 如果不是空持仓，不渲染
  if (!isPortfolioEmpty) return null

  const isScenarioB = hasPortfolio

  return (
    <div
      className={`bg-card rounded-xl border border-border shadow-sm p-12 text-center ${
        className || ''
      }`}
    >
      <InboxIcon className="w-12 h-12 mx-auto mb-3 text-faint" />

      {isScenarioB ? (
        // 场景 B：有旧期但最新期未披露
        <>
          <p className="text-lg font-medium text-foreground mb-2">
            暂无最新一期持仓数据
          </p>
          <p className="text-sm text-muted-foreground mb-6">
            当前报告期尚未披露，请稍后再试
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => router.push('/dashboard/funds')}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg border border-border bg-card hover:bg-secondary text-foreground transition-colors"
            >
              <ArrowLeftIcon className="w-4 h-4" />
              返回列表
            </button>
            <a
              href="/dashboard/admin/fund-init"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <RefreshCwIcon className="w-4 h-4" />
              触发同步
            </a>
          </div>
        </>
      ) : (
        // 场景 A：无任何持仓记录，数据源未收录
        <>
          <p className="text-lg font-medium text-foreground mb-2">
            暂无最新持仓数据
          </p>
          <p className="text-sm text-muted-foreground mb-6">
            数据源未收录该基金
          </p>
          <button
            onClick={() => router.push('/dashboard/funds')}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg border border-border bg-card hover:bg-secondary text-foreground transition-colors"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            返回列表
          </button>
        </>
      )}
    </div>
  )
}
