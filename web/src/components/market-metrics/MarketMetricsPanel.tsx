'use client'

/**
 * 全市场量价面板（第 16 期 plan-07；FEAT-0003 双曲线拆分改造）
 *
 * 最新四值卡片 + 左右双折线图（左成交额 / 右平均价）+ 30/90/250 范围切换
 * （双图共享）+ 空/缺口/错误/重试态。
 * 插入两套首页：管理员（IndexMonitorPage 指数总览后、走势图前）与
 * 普通（dashboard 快捷入口后）。
 *
 * 实现：
 * - SWR 范式照抄 IndexMonitorPage.tsx:38-52（fetcher 返回 res.data = {success,data}，
 *   组件再取 .data；as unknown as cast）
 * - ECharts dynamic ssr:false（IndexTrendChart.tsx:28-31 范式），双图各一实例
 * - FEAT-0003：图表区拆分为左右两个折线图——左成交额（amountYuan，line，亿元）、
 *   右平均价（averagePrice，line，元，scale:true）；指标切换按钮与柱状图移除
 *   （左图原为成交量，2026-08-15 用户改定为成交额；成交量保留最新值卡片展示）
 * - 单位换算（显示层）：volumeShares ÷1e8→亿股；卡片平均价 2 位小数；
 *   tooltip 完整精度原始值
 * - 缺口：connectNulls:false + hasMissingDates 提示「部分日期无数据」
 * - 空态（latest===null）：管理员 /dashboard/admin/data 链接；普通用户纯文案
 * - 错误态：错误框 + 重试 → 仅 mutate()（局部刷新，不刷整页）
 * - 测试钩子：onChartReady 把 ECharts 实例挂到各图容器 DOM
 *   （(el as any).__echartsInst__ = chart），供 E2E 读 getOption() 断言
 *   series type（FEAT-0003 用例约定，沿用 17 期 margin-panel 先例）
 */
import React, { useMemo, useRef, useState } from 'react'
import useSWR from 'swr'
import dynamic from 'next/dynamic'
import Link from 'next/link'
import { AlertCircle, Database, RefreshCw, Loader2 } from 'lucide-react'
import { marketMetricsApi } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import type {
  MarketMetricsTrendData,
  MarketMetricsRange,
} from '@/types/marketMetricsTypes'

// 动态导入 ECharts（ssr:false，与 IndexTrendChart.tsx:28-31 一致）
const ReactECharts = dynamic(
  () => import('echarts-for-react').then((mod) => mod.default),
  {
    ssr: false,
    loading: () => (
      <div className="h-72 flex items-center justify-center text-muted-foreground text-sm">
        加载图表中...
      </div>
    ),
  }
)

// 范围切换器：用户显式点 30/90/250 即应发起对应请求。
// dedupingInterval 设 0 避免切回最近拉取过的范围时被去重。
// range 进 SWR key，双图共享同一份 trend 数据，显式切换必须重拉。
const SWR_OPTIONS = { revalidateOnFocus: false, dedupingInterval: 0 } as const

const RANGE_OPTIONS: MarketMetricsRange[] = [30, 90, 250]

/** 成交额/成交量：原始值 ÷1e8 转亿（显示层，2 位小数） */
function formatBillion(val: number | null): string {
  if (val === null || val === undefined) return '—'
  return (val / 1e8).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

/** 平均价：2 位小数 */
function formatPrice(val: number | null): string {
  if (val === null || val === undefined) return '—'
  return val.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export default function MarketMetricsPanel() {
  const { isAdmin } = useAuth()
  const [range, setRange] = useState<MarketMetricsRange>(30)
  const amountWrapRef = useRef<HTMLDivElement>(null)
  const priceWrapRef = useRef<HTMLDivElement>(null)

  // SWR 范式照抄 IndexMonitorPage.tsx:38-52：fetcher 返回 res.data（={success,data}），
  // 组件再取一层 .data 得业务对象；range 进 key，切换自动重拉且不刷新整页。
  // FEAT-0003：双图共用这一份 trend 数据（一次请求全指标）。
  const {
    data: trendRes,
    isLoading,
    error,
    mutate,
  } = useSWR<{ success: boolean; data: MarketMetricsTrendData }>(
    ['marketMetricsTrend', range],
    () =>
      marketMetricsApi.getTrend(range).then(
        (res) =>
          res.data as unknown as {
            success: boolean
            data: MarketMetricsTrendData
          }
      ),
    SWR_OPTIONS
  )
  const trend = trendRes?.data ?? null

  // 轴范围裁剪（FEAT-0003 用户追加）：只保留首个有数据日 ~ 最后有数据日之间的点，
  // 超出数据时间范围的前后空日期不上轴；中间缺口日保留（connectNulls:false 断线）。
  // 有数据判据与 16 期 latest 定义一致（volumeShares 非空）。
  const activePoints = useMemo(() => {
    if (!trend) return []
    const has = (p: (typeof trend.points)[number]) =>
      p.volumeShares !== null && p.volumeShares !== undefined
    const first = trend.points.findIndex(has)
    if (first === -1) return []
    let last = trend.points.length - 1
    while (last > first && !has(trend.points[last])) last--
    return trend.points.slice(first, last + 1)
  }, [trend])

  // 左图：成交额折线（亿元，÷1e8 显示层换算）
  const amountOption = useMemo(() => {
    if (activePoints.length === 0) return null
    return {
      animation: true,
      tooltip: {
        trigger: 'axis',
        // tooltip 显示完整精度原始值（元）+ 亿元换算
        formatter: (params: unknown) => {
          const p = (Array.isArray(params) ? params[0] : params) as
            | { dataIndex?: number; axisValueLabel?: string }
            | undefined
          const idx: number = p?.dataIndex ?? 0
          const pt = activePoints[idx]
          if (!pt) return p?.axisValueLabel ?? ''
          const raw = pt.amountYuan
          if (raw === null || raw === undefined) {
            return `${pt.tradeDate}<br/>成交额：无数据`
          }
          const yi = (raw / 1e8).toLocaleString('zh-CN', {
            maximumFractionDigits: 4,
          })
          return `${pt.tradeDate}<br/>成交额：${raw.toLocaleString('zh-CN')} 元（${yi} 亿元）`
        },
      },
      grid: { left: '3%', right: '6%', bottom: '8%', top: '14%', containLabel: true },
      xAxis: {
        type: 'category',
        data: activePoints.map((p) => p.tradeDate),
        axisLabel: { fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        name: '亿元',
        nameTextStyle: { fontSize: 11 },
        axisLabel: { fontSize: 11 },
        splitLine: { lineStyle: { type: 'dashed' } },
      },
      series: [
        {
          name: '成交额',
          type: 'line' as const,
          data: activePoints.map((p) =>
            p.amountYuan === null || p.amountYuan === undefined
              ? null
              : p.amountYuan / 1e8
          ),
          smooth: true,
          connectNulls: false,
          itemStyle: { color: '#3B82F6' },
          lineStyle: { width: 2, color: '#3B82F6' },
        },
      ],
    }
  }, [activePoints])

  // 右图：平均价折线（元，scale:true 避免 y 轴从 0 起压扁波动）
  const priceOption = useMemo(() => {
    if (activePoints.length === 0) return null
    return {
      animation: true,
      tooltip: {
        trigger: 'axis',
        formatter: (params: unknown) => {
          const p = (Array.isArray(params) ? params[0] : params) as
            | { dataIndex?: number; axisValueLabel?: string }
            | undefined
          const idx: number = p?.dataIndex ?? 0
          const pt = activePoints[idx]
          if (!pt) return p?.axisValueLabel ?? ''
          const raw = pt.averagePrice
          if (raw === null || raw === undefined) {
            return `${pt.tradeDate}<br/>平均价：无数据`
          }
          return `${pt.tradeDate}<br/>平均价：${raw.toLocaleString('zh-CN', {
            maximumFractionDigits: 4,
          })} 元`
        },
      },
      grid: { left: '3%', right: '6%', bottom: '8%', top: '14%', containLabel: true },
      xAxis: {
        type: 'category',
        data: activePoints.map((p) => p.tradeDate),
        axisLabel: { fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        name: '元',
        nameTextStyle: { fontSize: 11 },
        axisLabel: { fontSize: 11 },
        splitLine: { lineStyle: { type: 'dashed' } },
        scale: true,
      },
      series: [
        {
          name: '平均价',
          type: 'line' as const,
          data: activePoints.map((p) =>
            p.averagePrice === null || p.averagePrice === undefined
              ? null
              : p.averagePrice
          ),
          smooth: true,
          connectNulls: false,
          itemStyle: { color: '#10B981' },
          lineStyle: { width: 2, color: '#10B981' },
        },
      ],
    }
  }, [activePoints])

  return (
    <section
      data-testid="market-metrics-panel"
      className="bg-card rounded-xl border border-border shadow-sm p-6"
    >
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-foreground">市场量价总览</h2>
          <p className="text-sm text-muted-foreground mt-1">
            全市场成交额 / 成交量 / 平均价趋势
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          {/* 范围切换：30/90/250 改 state → SWR key 变化自动重拉（双图共享），不刷新整页 */}
          <div
            className="inline-flex rounded-lg border border-border overflow-hidden"
            role="group"
            aria-label="范围切换"
          >
            {RANGE_OPTIONS.map((r) => (
              <button
                key={r}
                type="button"
                data-testid={`market-metrics-range-${r}`}
                aria-pressed={range === r}
                onClick={() => setRange(r)}
                className={`px-3 py-1.5 text-sm transition-colors ${
                  range === r
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-card text-foreground hover:bg-secondary'
                }`}
              >
                {r}日
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* 加载态 */}
      {isLoading && !trend && (
        <div className="flex items-center justify-center py-16 text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          加载市场量价数据中...
        </div>
      )}

      {/* 错误态：错误框 + 重试 → 仅 mutate() 局部刷新 */}
      {error && !trend && (
        <div
          data-testid="market-metrics-error"
          className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 mt-4"
        >
          <div className="flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-destructive">加载市场量价数据失败</p>
              <p className="text-sm text-destructive mt-1">
                {(error as Error).message}
              </p>
              <button
                data-testid="market-metrics-retry"
                onClick={() => mutate()}
                className="mt-2 inline-flex items-center gap-1 text-sm text-destructive hover:underline"
              >
                <RefreshCw className="w-3 h-3" />
                重试
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 空态：latest === null（同步未跑 / 全空） */}
      {trend && trend.latest === null && (
        <div
          data-testid="market-metrics-empty"
          className="rounded-lg border border-dashed border-border p-8 text-center mt-4"
        >
          <Database className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">
            市场量价数据尚未同步，暂无可用数据。
          </p>
          {isAdmin ? (
            <Link
              href="/dashboard/admin/data"
              data-testid="market-metrics-empty-admin-link"
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary-hover transition-colors"
            >
              <Database className="w-4 h-4" />
              前往数据管理
            </Link>
          ) : (
            <p className="text-xs text-muted-foreground mt-3">请联系管理员同步数据。</p>
          )}
        </div>
      )}

      {/* 正常态：latest 有值 */}
      {trend && trend.latest !== null && (
        <div className="mt-4 space-y-4">
          {/* 最新四值卡片（含成交额；成交额不上图，仅卡片展示） */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-lg bg-secondary/50 p-3">
              <p className="text-xs text-muted-foreground">最近结果日</p>
              <p
                data-testid="market-metrics-latest-date"
                className="text-sm font-semibold text-foreground mt-1"
              >
                {trend.latest.tradeDate}
              </p>
            </div>
            <div className="rounded-lg bg-secondary/50 p-3">
              <p className="text-xs text-muted-foreground">成交额（亿元）</p>
              <p className="text-sm font-semibold text-foreground mt-1">
                {formatBillion(trend.latest.amountYuan)}
              </p>
            </div>
            <div className="rounded-lg bg-secondary/50 p-3">
              <p className="text-xs text-muted-foreground">成交量（亿股）</p>
              <p className="text-sm font-semibold text-foreground mt-1">
                {formatBillion(trend.latest.volumeShares)}
              </p>
            </div>
            <div className="rounded-lg bg-secondary/50 p-3">
              <p className="text-xs text-muted-foreground">平均价（元）</p>
              <p className="text-sm font-semibold text-foreground mt-1">
                {formatPrice(trend.latest.averagePrice)}
              </p>
            </div>
          </div>

          {/* 缺口提示 */}
          {trend.hasMissingDates && (
            <p
              data-testid="market-metrics-missing-hint"
              className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1"
            >
              <AlertCircle className="w-3.5 h-3.5" />
              部分日期无数据
            </p>
          )}

          {/* FEAT-0003 双折线图：左成交量 / 右平均价；移动端上下堆叠、桌面并排。
              onChartReady 测试钩子：实例挂各容器 DOM，E2E 读 getOption() 断言
              series type= line（无 bar）。 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-foreground mb-1">
                成交额趋势
              </p>
              <div data-testid="market-metrics-chart-amount" ref={amountWrapRef} className="w-full">
                {amountOption && (
                  <ReactECharts
                    option={amountOption}
                    style={{ height: 280, width: '100%' }}
                    onChartReady={(chart) => {
                      if (amountWrapRef.current) {
                        ;(
                          amountWrapRef.current as HTMLDivElement & {
                            __echartsInst__?: unknown
                          }
                        ).__echartsInst__ = chart
                      }
                    }}
                  />
                )}
              </div>
            </div>
            <div>
              <p className="text-sm font-medium text-foreground mb-1">
                平均价趋势
              </p>
              <div data-testid="market-metrics-chart-price" ref={priceWrapRef} className="w-full">
                {priceOption && (
                  <ReactECharts
                    option={priceOption}
                    style={{ height: 280, width: '100%' }}
                    onChartReady={(chart) => {
                      if (priceWrapRef.current) {
                        ;(
                          priceWrapRef.current as HTMLDivElement & {
                            __echartsInst__?: unknown
                          }
                        ).__echartsInst__ = chart
                      }
                    }}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
