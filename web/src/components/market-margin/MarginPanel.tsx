'use client'

/**
 * 全市场融资融券面板（第 17 期 plan-07 Task 3）
 *
 * 最新值卡片（4 指标 ÷1e8 转亿）+ 双 Y 轴曲线 + 30/90/250 范围切换 +
 * 空/缺口/错误/重试态。仅插入普通用户首页（dashboard 非管理员分支，
 * MarketMetricsPanel 之后）；管理员首页 IndexMonitorPage 不在 spec REQ-7 范围。
 *
 * 实现（plan-07 §实现规格-3，母本 MarketMetricsPanel.tsx）：
 * - SWR 范式照抄 MarketMetricsPanel.tsx:88-105（fetcher 返回 res.data =
 *   {success,data}，组件再取 .data；as unknown as cast）
 * - ECharts dynamic ssr:false，单实例（性能验收 container 数量=1）
 * - 双 Y 轴：左轴（yAxisIndex 0）rzye+rzrqye 万亿级、右轴（1）rqye+rzmre
 *   千亿级（右轴统一元口径；rqmcl 股口径不入图，仅保留数据契约）
 * - 单位换算（显示层）：存储元，前端 ÷1e8 转亿（formatBillion）；
 *   tooltip 显示完整精度原始值（元）
 * - 缺口：connectNulls:false 断线 + hasMissingDates 提示「部分日期无数据」
 * - 空态（latest===null）：管理员 /dashboard/admin/data 链接；普通用户纯文案
 * - 错误态：错误框 + 重试 → 仅 mutate()（局部刷新，不刷整页）
 * - 测试钩子：onChartReady 把 ECharts 实例挂到 margin-chart 容器 DOM
 *   （(el as any).__echartsInst__ = chart），供 E2E 读 getOption() 断言
 *   legend / 双 Y 轴 / 缺口 null（用例文档约定）
 */
import React, { useMemo, useRef, useState } from 'react'
import useSWR from 'swr'
import dynamic from 'next/dynamic'
import Link from 'next/link'
import { AlertCircle, Database, RefreshCw, Loader2 } from 'lucide-react'
import { marginApi } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import type {
  MarginTrendData,
  MarginRange,
  MarginPoint,
} from '@/types/marginTypes'

// 动态导入 ECharts（ssr:false，与 MarketMetricsPanel.tsx:34-44 一致）
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
// dedupingInterval 设 0 避免切回最近拉取过的范围时被去重（range 进 SWR key，
// 显式切换必须重拉，与 MarketMetricsPanel 一致）。
const SWR_OPTIONS = { revalidateOnFocus: false, dedupingInterval: 0 } as const

const RANGE_OPTIONS: MarginRange[] = [30, 90, 250]

/** 最新值卡片配置（AC-6 4 指标；rqmcl 股口径不入卡片） */
const CARD_CONFIG: Array<{
  key: 'rzye' | 'rqye' | 'rzrqye' | 'rzmre'
  label: string
}> = [
  { key: 'rzye', label: '融资余额' },
  { key: 'rqye', label: '融券余额' },
  { key: 'rzrqye', label: '两融合计余额' },
  { key: 'rzmre', label: '融资买入额' },
]

/** 曲线序列配置：legend 4 项顺序即 ECharts option legend.data；
 *  左轴（0）元口径万亿级 rzye+rzrqye、右轴（1）元口径千亿级 rqye+rzmre */
const SERIES_CONFIG: Array<{
  key: 'rzye' | 'rzrqye' | 'rqye' | 'rzmre'
  label: string
  axis: 0 | 1
  color: string
}> = [
  { key: 'rzye', label: '融资余额', axis: 0, color: '#3B82F6' },
  { key: 'rzrqye', label: '两融合计余额', axis: 0, color: '#8B5CF6' },
  { key: 'rqye', label: '融券余额', axis: 1, color: '#F59E0B' },
  { key: 'rzmre', label: '融资买入额', axis: 1, color: '#10B981' },
]

/** 元原始值 ÷1e8 转亿（显示层，2 位小数） */
function formatBillion(val: number | null): string {
  if (val === null || val === undefined) return '—'
  return (val / 1e8).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

/** ECharts axis tooltip 回调参数的最小结构（legend 文案在 canvas 内，不在 DOM） */
interface TooltipParam {
  dataIndex?: number
  axisValueLabel?: string
}

export default function MarginPanel() {
  const { isAdmin } = useAuth()
  const [range, setRange] = useState<MarginRange>(30)
  const chartWrapRef = useRef<HTMLDivElement>(null)

  // SWR 范式照抄 MarketMetricsPanel.tsx:88-105：fetcher 返回 res.data
  // （={success,data}），组件再取一层 .data 得业务对象；range 进 key，
  // 切换自动重拉且不刷新整页。
  const {
    data: trendRes,
    isLoading,
    error,
    mutate,
  } = useSWR<{ success: boolean; data: MarginTrendData }>(
    ['marginTrend', range],
    () =>
      marginApi.getTrend(range).then(
        (res) =>
          res.data as unknown as {
            success: boolean
            data: MarginTrendData
          }
      ),
    SWR_OPTIONS
  )
  const trend = trendRes?.data ?? null

  const option = useMemo(() => {
    if (!trend || trend.points.length === 0) return null
    const dates = trend.points.map((p) => p.tradeDate)

    return {
      animation: true,
      tooltip: {
        trigger: 'axis',
        // tooltip 显示完整精度原始值（元）+ 亿换算；缺失日显示「无数据」
        formatter: (params: TooltipParam | TooltipParam[]) => {
          const arr = Array.isArray(params) ? params : [params]
          const idx: number = arr[0]?.dataIndex ?? 0
          const pt: MarginPoint | undefined = trend.points[idx]
          if (!pt) return arr[0]?.axisValueLabel ?? ''
          const lines = [pt.tradeDate]
          for (const cfg of SERIES_CONFIG) {
            const raw = pt[cfg.key]
            if (raw === null || raw === undefined) {
              lines.push(`${cfg.label}：无数据`)
            } else {
              const yi = (raw / 1e8).toLocaleString('zh-CN', {
                maximumFractionDigits: 4,
              })
              lines.push(
                `${cfg.label}：${raw.toLocaleString('zh-CN')} 元（${yi} 亿元）`
              )
            }
          }
          return lines.join('<br/>')
        },
      },
      legend: {
        data: SERIES_CONFIG.map((s) => s.label),
      },
      grid: { left: '3%', right: '6%', bottom: '8%', top: '12%', containLabel: true },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { fontSize: 11 },
      },
      // 双 Y 轴（AC-6）：均 scale:true 避免从 0 起压扁曲线（左右轴量级差一个数量级）
      yAxis: [
        {
          type: 'value',
          name: '亿元',
          nameTextStyle: { fontSize: 11 },
          axisLabel: { fontSize: 11 },
          splitLine: { lineStyle: { type: 'dashed' } },
          scale: true,
        },
        {
          type: 'value',
          name: '亿元',
          nameTextStyle: { fontSize: 11 },
          axisLabel: { fontSize: 11 },
          splitLine: { show: false },
          scale: true,
        },
      ],
      series: SERIES_CONFIG.map((cfg) => ({
        name: cfg.label,
        type: 'line' as const,
        yAxisIndex: cfg.axis,
        // 显示层换算：÷1e8 转亿；缺失日保持 null（不补 0/前值，AC-5）
        data: trend.points.map((p) => {
          const v = p[cfg.key]
          return v === null || v === undefined ? null : v / 1e8
        }),
        smooth: false,
        connectNulls: false,
        itemStyle: { color: cfg.color },
        lineStyle: { width: 2, color: cfg.color },
      })),
    }
  }, [trend])

  return (
    <section
      data-testid="margin-panel"
      className="bg-card rounded-xl border border-border shadow-sm p-6"
    >
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-foreground">融资融券总览</h2>
          <p className="text-sm text-muted-foreground mt-1">
            全市场融资余额 / 融券余额 / 两融合计余额 / 融资买入额趋势
          </p>
        </div>
        {/* 范围切换（AC-6）：30/90/250 改 state → SWR key 变化自动重拉，不刷新整页 */}
        <div
          className="inline-flex rounded-lg border border-border overflow-hidden"
          role="group"
          aria-label="范围切换"
        >
          {RANGE_OPTIONS.map((r) => (
            <button
              key={r}
              type="button"
              data-testid={`margin-range-${r}`}
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
      </header>

      {/* 加载态 */}
      {isLoading && !trend && (
        <div className="flex items-center justify-center py-16 text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          加载融资融券数据中...
        </div>
      )}

      {/* 错误态：错误框 + 重试 → 仅 mutate() 局部刷新 */}
      {error && !trend && (
        <div
          data-testid="margin-error"
          className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 mt-4"
        >
          <div className="flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-destructive">加载融资融券数据失败</p>
              <p className="text-sm text-destructive mt-1">
                {(error as Error).message}
              </p>
              <button
                data-testid="margin-retry"
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
          data-testid="margin-empty"
          className="rounded-lg border border-dashed border-border p-8 text-center mt-4"
        >
          <Database className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">
            融资融券数据尚未同步，暂无可用数据。
          </p>
          {isAdmin ? (
            <Link
              href="/dashboard/admin/data"
              data-testid="margin-empty-admin-link"
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
          {/* 最新值卡片（AC-6：最近结果日 + 4 指标，均 ÷1e8 亿元） */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="rounded-lg bg-secondary/50 p-3">
              <p className="text-xs text-muted-foreground">最近结果日</p>
              <p
                data-testid="margin-latest-date"
                className="text-sm font-semibold text-foreground mt-1"
              >
                {trend.latest.tradeDate}
              </p>
            </div>
            {CARD_CONFIG.map((c) => (
              <div
                key={c.key}
                data-testid={`margin-card-${c.key}`}
                className="rounded-lg bg-secondary/50 p-3"
              >
                <p className="text-xs text-muted-foreground">{c.label}（亿元）</p>
                <p className="text-sm font-semibold text-foreground mt-1">
                  {formatBillion(trend.latest![c.key])}
                </p>
              </div>
            ))}
          </div>

          {/* 缺口提示（AC-5）：hasMissingDates → connectNulls:false 断线 + 提示 */}
          {trend.hasMissingDates && (
            <p
              data-testid="margin-missing-hint"
              className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1"
            >
              <AlertCircle className="w-3.5 h-3.5" />
              部分日期无数据
            </p>
          )}

          {/* 图表（单 ECharts 实例；性能验收 container 数量=1）。
              onChartReady 测试钩子：实例挂容器 DOM，E2E 读 getOption()
              断言 legend / 双 Y 轴 / 缺口 null（用例文档约定）。 */}
          <div data-testid="margin-chart" ref={chartWrapRef} className="w-full">
            {option && (
              <ReactECharts
                option={option}
                style={{ height: 320, width: '100%' }}
                onChartReady={(chart) => {
                  if (chartWrapRef.current) {
                    ;(
                      chartWrapRef.current as HTMLDivElement & {
                        __echartsInst__?: unknown
                      }
                    ).__echartsInst__ = chart
                  }
                }}
              />
            )}
          </div>
        </div>
      )}
    </section>
  )
}
