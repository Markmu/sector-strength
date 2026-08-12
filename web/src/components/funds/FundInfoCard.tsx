'use client'

import React from 'react'
import { Fund } from '@/lib/api'
import { CalendarIcon, BuildingIcon, TargetIcon, TagIcon } from 'lucide-react'

export interface FundInfoCardProps {
  fund: Fund
  className?: string
}

/**
 * 基金基本信息卡片组件
 *
 * 展示：代码、名称、类型/投资风格、管理人、成立日期、跟踪标的
 * 跟踪标的：被动指数型展示指数名，无则显示"-"
 */
export default function FundInfoCard({ fund, className }: FundInfoCardProps) {
  // 构建类型展示文本
  const typeDisplay = [fund.fundType, fund.investType].filter(Boolean).join(' / ') || '-'

  // 跟踪标的展示：被动指数型展示指数名，无则显示"-"
  const benchmarkDisplay = fund.benchmark || '-'

  return (
    <div
      className={`bg-card rounded-xl border border-border shadow-sm p-6 ${
        className || ''
      }`}
    >
      {/* 标题区：代码 + 名称 */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-foreground">{fund.name}</h2>
          <p className="text-sm font-mono text-muted-foreground mt-1">
            {fund.tsCode}
          </p>
        </div>
        {fund.market && (
          <span className="inline-flex items-center px-2.5 py-1 text-xs font-medium bg-primary/10 text-primary rounded-full">
            {fund.market === 'E' ? '场内' : fund.market === 'O' ? '场外' : fund.market}
          </span>
        )}
      </div>

      {/* 信息网格 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* 类型/投资风格 */}
        <div className="flex items-start gap-2">
          <TagIcon className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-xs text-muted-foreground">类型</p>
            <p className="text-sm font-medium text-foreground">{typeDisplay}</p>
          </div>
        </div>

        {/* 管理人 */}
        <div className="flex items-start gap-2">
          <BuildingIcon className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-xs text-muted-foreground">管理人</p>
            <p className="text-sm font-medium text-foreground">
              {fund.management || '-'}
            </p>
          </div>
        </div>

        {/* 成立日期 */}
        <div className="flex items-start gap-2">
          <CalendarIcon className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-xs text-muted-foreground">成立日期</p>
            <p className="text-sm font-medium text-foreground">
              {fund.foundDate || '-'}
            </p>
          </div>
        </div>

        {/* 跟踪标的 */}
        <div className="flex items-start gap-2 sm:col-span-2 lg:col-span-3">
          <TargetIcon className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-xs text-muted-foreground">跟踪标的</p>
            <p className="text-sm font-medium text-foreground break-all">
              {benchmarkDisplay}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
