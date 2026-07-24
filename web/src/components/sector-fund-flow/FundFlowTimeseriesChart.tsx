'use client'

/**
 * 盘中资金流变化曲线（plan-03，AC-06/07/08）
 *
 * 多板块净额叠加折线图。复用项目现有 echarts-for-react（与 SectorStrengthChart 同库），
 * 遵循 CrowdIndustryDistribution 的动态导入范式（ssr:false，避免 SSR 污染）。
 *
 * 交互：
 * - 多线叠加，每个板块一种颜色 + 图例（legend）可点击显隐
 * - 横轴 = 交易时段时间（HH:mm），纵轴 = 净额（亿），零轴基线（markLine）
 * - 鼠标悬停 tooltip 显示各板块该时点净额
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
  const { option } = useMemo(() => {
    const series = data.series ?? []
    if (series.length === 0) {
      return { option: null }
    }

    // 横轴：取所有板块采样时间的并集（按时间升序去重）
    // 各板块采样点可能不完全一致，用并集保证横轴覆盖全部时点
    const timeSet = new Set<string>()
    series.forEach((s) => {
      s.data.forEach((p) => timeSet.add(p.sampleTime))
    })
    const times = Array.from(timeSet).sort()

    // 每板块一条线：以并集时间为横轴，缺失时点插 null（断线，不连零）
    const echartsSeries = series.map((s, idx) => {
      const pointMap = new Map<string, number | null>()
      s.data.forEach((p) => {
        pointMap.set(p.sampleTime, p.netInflow)
      })
      return {
        name: s.sectorName,
        type: 'line' as const,
        // 净额单位已是亿元（后端口径，见 server 模型列定义）；undefined（该时点无采样）与 null（采样值空）都断线
        data: times.map((t) => {
          const v = pointMap.get(t)
          if (v === undefined || v === null) return null
          return Number(v.toFixed(2))
        }),
        smooth: false,
        symbol: 'circle',
        symbolSize: 5,
        showSymbol: false,
        lineStyle: { width: 2, color: SERIES_COLORS[idx % SERIES_COLORS.length] },
        itemStyle: { color: SERIES_COLORS[idx % SERIES_COLORS.length] },
        connectNulls: false,
        // 零轴基线（仅首条线附加，避免重复）
        ...(idx === 0
          ? {
              markLine: {
                silent: true,
                symbol: 'none',
                lineStyle: { type: 'dashed' as const, color: '#9CA3AF', width: 1 },
                data: [{ yAxis: 0 }],
              },
            }
          : {}),
      }
    })

    const opt = {
      tooltip: {
        trigger: 'axis' as const,
        // 多板块叠加时（最多 50 条）tooltip 行数可能很长，限高滚动避免遮挡图表
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
      legend: {
        bottom: 5,
        // 最多 50 条曲线，图例改滚动型避免撑爆布局；点击图例项可显隐对应曲线
        type: 'scroll' as const,
        pageIconSize: 12,
        pageTextStyle: { fontSize: 11 },
        data: series.map((s) => s.sectorName),
      },
      grid: {
        left: '3%',
        right: '3%',
        bottom: '15%',
        top: '8%',
        containLabel: true,
      },
      xAxis: {
        type: 'category' as const,
        data: times.map(formatSampleTime),
        boundaryGap: false,
        axisLabel: {
          fontSize: 11,
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
    return { option: opt }
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
