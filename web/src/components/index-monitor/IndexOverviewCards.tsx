'use client'

/**
 * 指数总览卡片网格（第 15 期 plan-04 Task 7）
 *
 * AC-01：关注指数总览卡片网格，涨跌幅红涨绿跌，成交额亿元，PE 或"暂无估值"
 * AC-05：每张卡片提供"ETF 资金"跳转按钮（带 index_code query）
 * AC-12：非交易日/未更新时显示最近交易日（角标由 overview.tradeDate 标注）
 * AC-13：个别卡片数据异常独立显示"数据获取失败"（对 close/pctChg/amount 全 null 的卡片）
 */
import React from 'react'
import Link from 'next/link'
import { ArrowRight, AlertTriangle } from 'lucide-react'
import type { IndexOverviewData, IndexOverviewItem } from '@/types/indexMonitorTypes'
import {
  getChangeColor,
  formatAmount,
  formatPe,
  formatPercent,
  formatClose,
} from './helpers'

interface Props {
  overview: IndexOverviewData
}

export default function IndexOverviewCards({ overview }: Props) {
  const indices = overview.indices ?? []

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-foreground">
          指数总览
          <span className="ml-2 text-sm text-muted-foreground">
            共 {indices.length} 只
          </span>
        </h2>
        {overview.tradeDate && (
          <span className="text-xs text-muted-foreground">
            数据交易日：{overview.tradeDate}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {indices.map((item) => (
          <IndexCard key={item.tsCode} item={item} />
        ))}
      </div>
    </section>
  )
}

function IndexCard({ item }: { item: IndexOverviewItem }) {
  // AC-13：close/pctChg 全 null 视为该卡片数据异常
  const isCardError =
    item.close === null && item.pctChg === null && item.amount === null

  if (isCardError) {
    return (
      <div className="bg-card rounded-xl border border-destructive/30 p-4">
        <div className="flex items-center gap-2 text-destructive mb-2">
          <AlertTriangle className="w-4 h-4" />
          <span className="font-medium text-sm">{item.name}</span>
        </div>
        <p className="text-xs text-destructive">数据获取失败</p>
        <p className="text-xs text-muted-foreground mt-1">{item.tsCode}</p>
      </div>
    )
  }

  return (
    <div className="bg-card rounded-xl border border-border shadow-sm p-4 hover:shadow-md transition-shadow flex flex-col">
      {/* 头部：名称 + 代码 */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-semibold text-foreground text-sm">{item.name}</h3>
          <p className="text-xs text-muted-foreground">{item.tsCode}</p>
        </div>
      </div>

      {/* 收盘价 */}
      <div className="text-2xl font-bold text-foreground tabular-nums">
        {formatClose(item.close)}
      </div>

      {/* 涨跌幅（红涨绿跌） */}
      <div className={`text-sm font-medium tabular-nums ${getChangeColor(item.pctChg)}`}>
        {formatPercent(item.pctChg)}
      </div>

      {/* 成交额 + PE */}
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div>
          <div className="text-muted-foreground">成交额</div>
          <div className="text-foreground tabular-nums">
            {formatAmount(item.amount)}
          </div>
        </div>
        <div>
          <div className="text-muted-foreground">PE(TTM)</div>
          <div
            className={`tabular-nums ${
              item.peTtm === null ? 'text-muted-foreground' : 'text-foreground'
            }`}
          >
            {formatPe(item.peTtm)}
          </div>
        </div>
      </div>

      {/* ETF 资金跳转按钮（AC-05） */}
      <Link
        href={`/dashboard/etf-monitor?index_code=${encodeURIComponent(item.tsCode)}`}
        className="mt-3 inline-flex items-center justify-center gap-1 text-xs text-primary hover:text-primary-hover border border-primary/30 hover:border-primary/50 rounded-md py-1.5 transition-colors"
      >
        ETF 资金
        <ArrowRight className="w-3 h-3" />
      </Link>
    </div>
  )
}
