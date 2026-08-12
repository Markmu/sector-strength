'use client'

/**
 * ETF 历史趋势曲线（plan-05，AC-06/07/08/09/11）
 *
 * 仿 FundFlowTimeseriesChart.tsx（src/components/sector-fund-flow/FundFlowTimeseriesChart.tsx）范式：
 * `dynamic(() => import('echarts-for-react').then(m=>m.default), {ssr:false, loading:...})`，
 * 不建全局 wrapper。echarts 必须 ssr:false，否则 SSR 污染。
 *
 * 本组件包含：对象/指标/区间选择器 + 趋势曲线。
 * - 对象选择器：指数 / 单只 ETF 切换 + 对象下拉（候选来自指数排行 + 已展开明细 ETF）
 * - 指标选择：份额(share) / 净流入额(netInflow)
 * - 区间选择：7 / 30 / 90 日
 * - 调 useEtfTrend({targetType, targetCode, metric, days, endDate}) 取序列
 *
 * 四态：
 * - 未选对象 → "请选择要查看的指数或 ETF"（引导态，不画空坐标系）
 * - 完全无数据(hasData=false) → "该对象暂无数据"（空态）
 * - 有部分数据（历史不足区间，AC-09）→ 正常绘制已有部分
 * - loading/error 同标准态
 *
 * data-testid 约定（spec 选择器依赖，命名必须与 etf-monitor.spec.ts 一致）：
 * - 图表容器：etf-trend-chart
 * - 引导态：etf-trend-placeholder
 * - 空态：etf-trend-empty
 * - 错误态：etf-trend-error / etf-trend-retry
 * - 对象类型切换：etf-trend-target-type-{index|etf}
 * - 对象下拉触发：etf-trend-target-select
 * - 指标切换：etf-trend-metric-{share|netInflow}
 * - 区间切换：etf-trend-days-{7|30|90}
 */
import React, { useMemo } from 'react'
import dynamic from 'next/dynamic'
import { LineChartIcon } from 'lucide-react'
import {
  useEtfTrend,
} from '@/hooks/useEtfMonitor'
import type {
  EtfTrendMetric,
  EtfTargetType,
  EtfTrendDays,
} from '@/types/etfMonitorTypes'
import SimpleSelect from '@/components/ui/SimpleSelect'
import { formatSignedAmount } from './helpers'

// 动态导入 ECharts（禁用 SSR，参照 FundFlowTimeseriesChart.tsx 范式）
const ReactECharts = dynamic(
  () => import('echarts-for-react').then((mod) => mod.default),
  {
    ssr: false,
    loading: () => (
      <div className="h-80 flex items-center justify-center text-muted-foreground text-sm">
        加载图表中...
      </div>
    ),
  }
)

export interface EtfTrendTarget {
  type: EtfTargetType
  code: string
  name?: string
}

export interface EtfTrendChartProps {
  /** 当前对象（null=未选 → 引导态） */
  target: EtfTrendTarget | null
  /** 当前对象类型（独立于 target，切换类型只清空对象不改类型回退） */
  targetType: EtfTargetType
  metric: EtfTrendMetric
  days: EtfTrendDays
  endDate?: string | null
  /** 指数候选（用于指数对象下拉） */
  indexOptions: Array<{ code: string; name: string }>
  /** ETF 候选（用于单只 ETF 对象下拉，来自已展开明细或全量） */
  etfOptions: Array<{ code: string; name: string }>
  onTargetTypeChange: (t: EtfTargetType) => void
  onTargetChange: (t: EtfTrendTarget | null) => void
  onMetricChange: (m: EtfTrendMetric) => void
  onDaysChange: (d: EtfTrendDays) => void
}

export default function EtfTrendChart({
  target,
  targetType,
  metric,
  days,
  endDate,
  indexOptions,
  etfOptions,
  onTargetTypeChange,
  onTargetChange,
  onMetricChange,
  onDaysChange,
}: EtfTrendChartProps) {
  const targetCode = target?.code ?? null

  // 候选列表按当前对象类型切换
  const options = targetType === 'index' ? indexOptions : etfOptions
  const optionLabel = (code: string) =>
    options.find((o) => o.code === code)?.name ?? code

  // 趋势数据：未选对象（targetCode=null）时 hook 不发请求（条件 key）
  const { trend, isLoading, isError, mutate } = useEtfTrend({
    targetType,
    targetCode,
    metric,
    days,
    endDate,
  })

  // 构建 ECharts option（份额单条曲线 / 净流入额零轴基线 + 正负段色标）
  const option = useMemo(() => {
    const series = trend?.series ?? []
    const dates = series.map((p) => p.tradeDate)
    const values = series.map((p) => p.value)

    const isNetInflow = metric === 'netInflow'
    // 净流入额：零轴上方红、下方绿（A 股惯例）；份额：单条蓝
    const lineColor = isNetInflow ? '#EF4444' : '#3B82F6'

    const lineSeries: Record<string, unknown> = {
      name: isNetInflow ? '净流入额' : '份额',
      type: 'line',
      data: values,
      smooth: false,
      symbol: 'circle',
      symbolSize: 5,
      showSymbol: series.length <= 31,
      lineStyle: { width: 2, color: lineColor },
      itemStyle: { color: lineColor },
      connectNulls: false,
      // 净流入额加零轴基线
      markLine: isNetInflow
        ? {
            silent: true,
            symbol: 'none',
            data: [
              { yAxis: 0, lineStyle: { type: 'dashed', color: '#9CA3AF' } },
            ],
          }
        : undefined,
      // 净流入额正负段色标：visualMap 按 0 分段
    }

    const baseOption: Record<string, unknown> = {
      animation: true,
      tooltip: {
        trigger: 'axis',
        formatter: (params: unknown) => {
          const arr = params as Array<{
            axisValue: string
            data: number | null
          }>
          if (!arr || arr.length === 0) return ''
          const t = arr[0].axisValue
          const val = arr[0].data
          const valText =
            val === null || val === undefined
              ? '-'
              : isNetInflow
                ? formatSignedAmount(val, '亿元')
                : `${val.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}亿份`
          return `<div style="font-weight:600;">${t}</div><div>${valText}</div>`
        },
      },
      grid: {
        left: '3%',
        right: '6%',
        bottom: '10%',
        top: '8%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
        axisLabel: { fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        name: trend?.unit ?? (isNetInflow ? '亿元' : '亿份'),
        nameTextStyle: { fontSize: 11 },
        axisLabel: { fontSize: 11 },
        splitLine: { lineStyle: { type: 'dashed' } },
      },
      series: [lineSeries],
    }

    // 净流入额正负段色标：用 visualMap piecewise 按 0 分段（>0 红、<0 绿）
    if (isNetInflow) {
      baseOption.visualMap = {
        show: false,
        pieces: [
          { gt: 0, color: '#EF4444' },
          { lte: 0, color: '#10B981' },
        ],
        dimension: 1,
      }
    }

    return baseOption
  }, [trend, metric])

  return (
    <div className="space-y-4">
      {/* 对象 / 指标 / 区间选择器 */}
      <div className="flex flex-wrap items-center gap-4">
        {/* 对象类型切换（指数 / 单只 ETF）。类型独立于对象，切换只清空对象不回退类型 */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">对象</span>
          <div className="inline-flex rounded-lg border border-border bg-background p-0.5">
            <button
              type="button"
              onClick={() => {
                onTargetTypeChange('index')
                // 候选列表不同 → 清空已选对象（若当前选的是 etf 对象）
                if (target?.type === 'etf') onTargetChange(null)
              }}
              data-testid="etf-trend-target-type-index"
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                targetType === 'index'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              指数
            </button>
            <button
              type="button"
              onClick={() => {
                onTargetTypeChange('etf')
                if (target?.type === 'index') onTargetChange(null)
              }}
              data-testid="etf-trend-target-type-etf"
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                targetType === 'etf'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              单只 ETF
            </button>
          </div>
        </div>

        {/* 对象下拉（SimpleSelect：trigger 暴露 data-testid，选项为 role=option，spec 点击选择） */}
        <div className="flex items-center gap-2">
          <SimpleSelect
            value={targetCode ?? ''}
            options={options.map((o) => ({ value: o.code, label: o.name }))}
            onChange={(code) => {
              if (!code) {
                onTargetChange(null)
                return
              }
              onTargetChange({
                type: targetType,
                code,
                name: optionLabel(code),
              })
            }}
            placeholder="请选择…"
            testId="etf-trend-target-select"
            ariaLabel="趋势对象选择"
          />
        </div>

        {/* 指标切换（份额 / 净流入额） */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">指标</span>
          <div className="inline-flex rounded-lg border border-border bg-background p-0.5">
            <button
              type="button"
              onClick={() => onMetricChange('netInflow')}
              data-testid="etf-trend-metric-netInflow"
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                metric === 'netInflow'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              净流入额
            </button>
            <button
              type="button"
              onClick={() => onMetricChange('share')}
              data-testid="etf-trend-metric-share"
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                metric === 'share'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              份额
            </button>
          </div>
        </div>

        {/* 区间切换（7 / 30 / 90 日） */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">区间</span>
          <div className="inline-flex rounded-lg border border-border bg-background p-0.5">
            {([7, 30, 90] as EtfTrendDays[]).map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => onDaysChange(d)}
                data-testid={`etf-trend-days-${d}`}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  days === d
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {d} 日
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 趋势图四态 */}
      {targetCode === null ? (
        // 未选对象 → 引导态（不画空坐标系，AC-06）
        <div
          className="p-12 text-center border border-dashed border-border rounded-lg"
          data-testid="etf-trend-placeholder"
        >
          <LineChartIcon className="w-10 h-10 mx-auto mb-3 text-muted-foreground/50" />
          <p className="text-base font-medium text-foreground mb-1">
            请选择要查看的指数或 ETF
          </p>
          <p className="text-sm text-muted-foreground">
            在上方选择对象，即可查看份额或净流入额的历史趋势曲线
          </p>
        </div>
      ) : isError ? (
        // 错误态 + 重试（AC-10，独立降级）
        <div className="p-8 text-center" data-testid="etf-trend-error">
          <p className="text-sm text-muted-foreground mb-3">趋势数据加载失败</p>
          <button
            type="button"
            onClick={() => mutate()}
            data-testid="etf-trend-retry"
            className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
          >
            重试
          </button>
        </div>
      ) : isLoading ? (
        <div className="h-80 flex items-center justify-center text-muted-foreground text-sm">
          加载趋势数据...
        </div>
      ) : !trend?.hasData || (trend?.series ?? []).length === 0 ? (
        // 完全无数据 → 空态（AC 降级回归：该对象暂无数据）
        <div
          className="p-12 text-center border border-dashed border-border rounded-lg"
          data-testid="etf-trend-empty"
        >
          <p className="text-base font-medium text-foreground mb-1">
            该对象暂无数据
          </p>
          <p className="text-sm text-muted-foreground">
            请切换其他对象或区间
          </p>
        </div>
      ) : (
        // 数据态：绘制曲线（有部分数据也走此分支，AC-09 正常绘制已有部分）
        <div
          data-testid="etf-trend-chart"
          className="border rounded-lg bg-card p-4"
        >
          <div className="mb-2 text-sm text-muted-foreground">
            {targetType === 'index' ? '指数' : 'ETF'}：{target?.name ?? targetCode} ·{' '}
            {metric === 'netInflow' ? '净流入额' : '份额'} · {days} 日
          </div>
          <ReactECharts
            option={option}
            style={{ height: '400px', width: '100%' }}
            opts={{ renderer: 'canvas' }}
          />
        </div>
      )}
    </div>
  )
}
