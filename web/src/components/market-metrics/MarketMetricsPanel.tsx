'use client'

/**
 * 全市场量价面板（第 16 期 plan-07 Task 3）
 *
 * 最新三值卡片 + 单指标柱/线图 + 30/90/250 范围切换 + 空/缺口/错误/重试态。
 * 插入两套首页：管理员（IndexMonitorPage 指数总览前）与普通（dashboard 快捷入口后）。
 *
 * 实现（架构 §6.4.1/3/5、plan-07 §实现规格）：
 * - SWR 范式照抄 IndexMonitorPage.tsx:38-52（fetcher 返回 res.data = {success,data}，
 *   组件再取 .data；as unknown as cast）
 * - ECharts dynamic ssr:false（IndexTrendChart.tsx:28-31 范式），单实例
 * - MetricKey 三态：默认 amountYuan；amountYuan/volumeShares 用 bar、averagePrice 用 line
 * - 单位换算（显示层）：amountYuan/1e8→亿元、volumeShares/1e8→亿股；卡片平均价 2 位小数；
 *   tooltip 完整精度原始值
 * - 缺口：connectNulls:false + hasMissingDates 提示「部分日期无数据」
 * - 空态（latest===null）：管理员 /dashboard/admin/data 链接；普通用户纯文案
 * - 错误态：错误框 + 重试 → 仅 mutate()（AC-12 局部刷新，不刷整页）
 */
import React, { useMemo, useState } from 'react'
import useSWR from 'swr'
import dynamic from 'next/dynamic'
import Link from 'next/link'
import { AlertCircle, Database, RefreshCw, Loader2 } from 'lucide-react'
import { marketMetricsApi } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import type {
  MarketMetricsTrendData,
  MetricKey,
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
// dedupingInterval 设 0 避免切回最近拉取过的范围时被去重（IndexMonitorPage 的 30s 去重
// 适用于无切换的被动刷新；本面板 range 进 SWR key，显式切换必须重拉，AC-05）。
const SWR_OPTIONS = { revalidateOnFocus: false, dedupingInterval: 0 } as const

const RANGE_OPTIONS: MarketMetricsRange[] = [30, 90, 250]
const METRIC_ORDER: MetricKey[] = ['amountYuan', 'volumeShares', 'averagePrice']

interface MetricConfig {
  label: string
  type: 'bar' | 'line'
  unit: string // 显示层单位（亿）
  rawUnit: string // 原始单位
}
const METRIC_CONFIG: Record<MetricKey, MetricConfig> = {
  amountYuan: { label: '成交额', type: 'bar', unit: '亿元', rawUnit: '元' },
  volumeShares: { label: '成交量', type: 'bar', unit: '亿股', rawUnit: '股' },
  averagePrice: { label: '平均价', type: 'line', unit: '元', rawUnit: '元' },
}

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
  const [metric, setMetric] = useState<MetricKey>('amountYuan')

  // SWR 范式照抄 IndexMonitorPage.tsx:38-52：fetcher 返回 res.data（={success,data}），
  // 组件再取一层 .data 得业务对象；range 进 key，切换自动重拉且不刷新整页。
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

  const option = useMemo(() => {
    if (!trend || trend.points.length === 0) return null
    const cfg = METRIC_CONFIG[metric]
    const isPrice = metric === 'averagePrice'
    const dates = trend.points.map((p) => p.tradeDate)
    // 显示层换算：amountYuan/volumeShares ÷1e8；averagePrice 原值
    const seriesData = trend.points.map((p) => {
      const v = p[metric]
      if (v === null || v === undefined) return null
      return isPrice ? v : v / 1e8
    })

    return {
      animation: true,
      tooltip: {
        trigger: 'axis',
        // tooltip 显示完整精度原始值（不随轴标签取整）
        formatter: (params: any) => {
          const p = Array.isArray(params) ? params[0] : params
          const idx: number = p?.dataIndex ?? 0
          const pt = trend.points[idx]
          if (!pt) return p?.axisValueLabel ?? ''
          const raw = pt[metric]
          if (raw === null || raw === undefined) {
            return `${pt.tradeDate}<br/>${cfg.label}：无数据`
          }
          if (isPrice) {
            return `${pt.tradeDate}<br/>${cfg.label}：${raw.toLocaleString('zh-CN', {
              maximumFractionDigits: 4,
            })} ${cfg.rawUnit}`
          }
          // 成交额/成交量：原始值（元/股）完整精度 + 换算亿
          const yi = (raw / 1e8).toLocaleString('zh-CN', { maximumFractionDigits: 4 })
          return `${pt.tradeDate}<br/>${cfg.label}：${raw.toLocaleString('zh-CN')} ${
            cfg.rawUnit
          }（${yi} ${cfg.unit}）`
        },
      },
      grid: { left: '3%', right: '6%', bottom: '8%', top: '12%', containLabel: true },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        name: cfg.unit,
        nameTextStyle: { fontSize: 11 },
        axisLabel: { fontSize: 11 },
        splitLine: { lineStyle: { type: 'dashed' } },
        // 平均价折线 y 轴 scale:true（plan §8 风险备注）；柱图从 0 起
        scale: isPrice,
      },
      series: [
        {
          name: cfg.label,
          type: cfg.type,
          data: seriesData,
          smooth: false,
          connectNulls: false,
          itemStyle: { color: '#3B82F6' },
          lineStyle: { width: 2, color: '#3B82F6' },
        },
      ],
    }
  }, [trend, metric])

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
          {/* 指标切换（AC-04）：amountYuan/volumeShares 柱图、averagePrice 折线 */}
          <div
            className="inline-flex rounded-lg border border-border overflow-hidden"
            role="group"
            aria-label="指标切换"
          >
            {METRIC_ORDER.map((m) => (
              <button
                key={m}
                type="button"
                data-testid={`market-metrics-metric-${m}`}
                aria-pressed={metric === m}
                onClick={() => setMetric(m)}
                className={`px-3 py-1.5 text-sm transition-colors ${
                  metric === m
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-card text-foreground hover:bg-secondary'
                }`}
              >
                {METRIC_CONFIG[m].label}
              </button>
            ))}
          </div>
          {/* 范围切换（AC-05）：30/90/250 改 state → SWR key 变化自动重拉，不刷新整页 */}
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

      {/* 错误态（AC-12）：错误框 + 重试 → 仅 mutate() 局部刷新 */}
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
          {/* 最新三值卡片（§8.2-1：展示最近成功结果及其日期） */}
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

          {/* 缺口提示（AC-06） */}
          {trend.hasMissingDates && (
            <p
              data-testid="market-metrics-missing-hint"
              className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1"
            >
              <AlertCircle className="w-3.5 h-3.5" />
              部分日期无数据
            </p>
          )}

          {/* 图表（单 ECharts 实例；性能验收 container 数量=1） */}
          <div data-testid="market-metrics-chart" className="w-full">
            {option && (
              <ReactECharts option={option} style={{ height: 320, width: '100%' }} />
            )}
          </div>
        </div>
      )}
    </section>
  )
}
