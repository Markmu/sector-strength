'use client'

/**
 * 盘中资金流变化曲线（plan-03，AC-06/07/08）
 *
 * 多板块净额叠加折线图。复用项目现有 echarts-for-react（与 SectorStrengthChart 同库），
 * 遵循 CrowdIndustryDistribution 的动态导入范式（ssr:false，避免 SSR 污染）。
 *
 * 交互：
 * - 多线叠加，每个板块一种颜色
 * - 横轴 = 交易时段时间（HH:mm），纵轴 = 净额（亿），零轴基线（markLine）
 * - 鼠标悬停 tooltip 显示各板块该时点净额
 * - 每条曲线末端：markPoint 锚点小圆点 + markLine 水平连线（连线长度=间距），
 *   连线末端 label 为无边框气泡（板块名 + 最新净额，红正绿负）
 *
 * 空态由父组件处理（未选板块引导态 / 无采样数据空态）；本组件仅在 series 非空时渲染。
 *
 * data-testid 约定：
 * - 容器：fund-flow-timeseries-chart
 */
import React, { useMemo } from 'react'
import dynamic from 'next/dynamic'
import type { FundFlowTimeseriesData } from '@/types/fundFlowTypes'
import { formatSampleTime, formatSignedAmount } from './helpers'

// 动态导入 ECharts（禁用 SSR，参照 CrowdIndustryDistribution.tsx:21-31）
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

// 多板块配色：50 色均匀色环（HSL 色相均匀分布 + 固定饱和度/亮度，保证多线可区分）
// 首批 8 色沿用原高饱和度色，之后按色相环均匀补充，支持最多 50 条曲线叠加。
const SERIES_COLORS: string[] = (() => {
  const primary = [
    '#EF4444', '#3B82F6', '#10B981', '#F59E0B',
    '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16',
  ]
  const rest: string[] = []
  // 从第 9 色起，在 360° 色相环上均匀取点，错开前 8 色的色相区间
  for (let i = 8; i < 50; i++) {
    const hue = Math.round((i * 360) / 50)
    rest.push(`hsl(${hue}, 65%, 55%)`)
  }
  return [...primary, ...rest]
})()

export interface FundFlowTimeseriesChartProps {
  data: FundFlowTimeseriesData
  height?: string
}

export default function FundFlowTimeseriesChart({
  data,
  height = '420px',
}: FundFlowTimeseriesChartProps) {
  const option = useMemo(() => {
    const series = data.series ?? []
    if (series.length === 0) {
      return null
    }

    // 横轴：取所有板块采样时间的并集（按时间升序去重）
    // 各板块采样点可能不完全一致，用并集保证横轴覆盖全部时点
    const timeSet = new Set<string>()
    series.forEach((s) => {
      s.data.forEach((p) => timeSet.add(p.sampleTime))
    })
    const times = Array.from(timeSet).sort()

    // 在最后一个采样时间之后追加一个「占位时间」，仅用于末端连线 markLine 的右端坐标，
    // 让连线能从曲线末端水平延伸出去（连线长度 ≈ 该时间跨度对应的像素宽）。
    // 所有 series 在该时间点为 null，不会画出多余线段。
    const padTime = (() => {
      if (times.length === 0) return null
      const last = new Date(times[times.length - 1])
      if (Number.isNaN(last.getTime())) return null
      last.setMinutes(last.getMinutes() + 15)
      return last.toISOString()
    })()
    const axisTimes = padTime ? [...times, padTime] : times

    // 每板块一条线：以并集时间为横轴，缺失时点插 null（断线，不连零）
    const echartsSeries = series.map((s, idx) => {
      const pointMap = new Map<string, number | null>()
      s.data.forEach((p) => {
        pointMap.set(p.sampleTime, p.netInflow)
      })
      const lineColor = SERIES_COLORS[idx % SERIES_COLORS.length]
      // 各时点净额（亿元）：undefined（无采样）与 null（采样值空）都断线
      const pointValues = times.map((t) => {
        const v = pointMap.get(t)
        if (v === undefined || v === null) return null
        return Number(v.toFixed(2))
      })
      // 末端标签净额取该板块最后一个有效采样点
      let latestNetInflow: number | null = null
      let lastValidTime: string | null = null
      for (let i = pointValues.length - 1; i >= 0; i--) {
        if (pointValues[i] !== null) {
          latestNetInflow = pointValues[i]
          lastValidTime = times[i]
          break
        }
      }
      // A 股惯例：净流入（正）红、净流出（负）绿
      const valueColor =
        latestNetInflow === null || latestNetInflow === 0
          ? '#6B7280'
          : latestNetInflow > 0
            ? '#EF4444'
            : '#10B981'

      return {
        name: s.sectorName,
        type: 'line' as const,
        data: pointValues,
        smooth: false,
        symbol: 'circle',
        symbolSize: 5,
        showSymbol: false,
        lineStyle: { width: 2, color: lineColor },
        itemStyle: { color: lineColor },
        connectNulls: false,
        // 末端气泡（endLabel）：无边框，板块名 + 最新净额（红正绿负）。
        // endLabel 是折线图末端气泡唯一可靠渲染方式；小 distance 让气泡紧贴连线末端。
        endLabel: {
          show: true,
          valueAnimation: false,
          // 极小边距，气泡紧贴连线末端
          distance: 2,
          padding: [3, 6],
          backgroundColor: 'rgba(255,255,255,0.95)',
          borderRadius: 4,
          fontSize: 11,
          color: '#374151',
          formatter: () => {
            const valText =
              latestNetInflow === null ? '—' : formatSignedAmount(latestNetInflow)
            return `{name|${s.sectorName}}  {val|${valText}}`
          },
          rich: {
            name: { color: '#374151', fontSize: 11, width: 70, overflow: 'truncate' as const, ellipsis: '…' },
            val: { color: valueColor, fontSize: 11, fontWeight: 600 },
          },
        },
        // 末端标签防重叠：重叠时下移
        labelLayout: {
          hideOverlap: false,
          moveOverlap: 'shiftY' as const,
        },
        // markLine 合并：零轴基线（仅首条线）+ 末端连线（每条线，水平延伸到占位时间）
        // 末端连线长度 = 曲线末端到气泡的间距（由占位时间跨度决定）
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { width: 1 },
          data: [
            // 零轴基线（仅首条线附加，避免重复）
            ...(idx === 0
              ? [{ yAxis: 0, lineStyle: { type: 'dashed' as const, color: '#9CA3AF' } }]
              : []),
            // 末端连线：从最后一个有效点水平延伸到占位时间点
            // coord 用与 x 轴类别一致的「HH:mm」格式（formatSampleTime）
            // 注意：markLine 的 data 每条线段必须是 [起点, 终点] 的二元数组
            ...(lastValidTime !== null && latestNetInflow !== null && padTime
              ? [
                  [
                    { coord: [formatSampleTime(lastValidTime), latestNetInflow] },
                    {
                      coord: [formatSampleTime(padTime), latestNetInflow],
                      lineStyle: { color: lineColor },
                    },
                  ],
                ]
              : []),
          ],
        },
        // 末端锚点小圆点（在最后一个有效点上），用 markPoint symbol 可靠渲染
        ...(lastValidTime !== null && latestNetInflow !== null
          ? {
              markPoint: {
                silent: true,
                symbol: 'circle',
                symbolSize: 5,
                itemStyle: { color: lineColor },
                label: { show: false },
                data: [{ coord: [formatSampleTime(lastValidTime), latestNetInflow] }],
              },
            }
          : {}),
      }
    })

    return {
      tooltip: {
        trigger: 'axis' as const,
        // 多板块叠加时 tooltip 行数可能很长，限高滚动避免遮挡图表
        confine: true,
        formatter: (params: Array<{ axisValue: string; data: number | null; color: string; seriesName: string }>) => {
          if (!params || params.length === 0) return ''
          const t = params[0].axisValue
          let html = `<div style="font-weight:600;margin-bottom:4px;">${formatSampleTime(t)}</div>`
          html += '<div style="max-height:240px;overflow-y:auto;">'
          params.forEach((p) => {
            const val = p.data
            html += `<div style="display:flex;align-items:center;gap:8px;margin:2px 0;">
              <span style="display:inline-block;width:10px;height:10px;background:${p.color};border-radius:50%;"></span>
              <span>${p.seriesName}：</span>
              <span style="font-weight:600;">${val === null || val === undefined ? '—' : formatSignedAmount(val)}</span>
            </div>`
          })
          html += '</div>'
          return html
        },
      },
      // 用末端气泡替代内置 legend
      legend: { show: false },
      grid: {
        // 右侧留白给末端气泡，避免被裁切
        left: '3%',
        right: '18%',
        bottom: '8%',
        top: '8%',
        containLabel: true,
      },
      xAxis: {
        type: 'category' as const,
        // 含末端占位时间（供连线右端坐标）；占位刻度不显示标签
        data: axisTimes.map((t) => formatSampleTime(t)),
        boundaryGap: false,
        axisLabel: {
          fontSize: 11,
          // 隐藏占位刻度标签（最后一个）
          formatter: (value: string, index: number) =>
            index === axisTimes.length - 1 && padTime ? '' : value,
        },
      },
      yAxis: {
        type: 'value' as const,
        name: '净额(亿)',
        nameTextStyle: { fontSize: 11 },
        axisLabel: {
          formatter: '{value}',
          fontSize: 11,
        },
        splitLine: { lineStyle: { type: 'dashed' as const } },
      },
      series: echartsSeries,
    }
  }, [data])

  if (!option) {
    return null
  }

  return (
    <div
      data-testid="fund-flow-timeseries-chart"
      className="border rounded-lg bg-card p-4"
    >
      <ReactECharts
        option={option}
        style={{ height, width: '100%' }}
        opts={{ renderer: 'canvas' }}
      />
    </div>
  )
}
