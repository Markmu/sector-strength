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
 * - 每条曲线末端：custom series（clip:false）在 grid 右侧轴外区画
 *   圆点 + 水平连线 + 文字气泡（板块名 + 最新净额，红正绿负）；
 *   连线长度由像素常量控制，不向横轴追加占位时间
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

    // 横轴只含真实采样时间；末端引导线由 custom series 画在 grid 右侧轴外区，
    // 不再追加占位时间（避免污染横轴数据/刻度）。
    const axisTimes = times
    // 每条线末端元信息：供 custom series 的 renderItem 画 轴外圆点+连线+文字
    const endLabelMeta: Array<{
      name: string
      color: string
      valueColor: string
      lastIdx: number
      lastVal: number
    }> = []

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
      let lastValidIndex = -1
      for (let i = pointValues.length - 1; i >= 0; i--) {
        if (pointValues[i] !== null) {
          latestNetInflow = pointValues[i]
          lastValidIndex = i
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

      // 收集末端元信息，供 custom series 在轴外画 圆点+连线+文字
      if (latestNetInflow !== null && lastValidIndex >= 0) {
        endLabelMeta.push({
          name: s.sectorName,
          color: lineColor,
          valueColor,
          lastIdx: lastValidIndex,
          lastVal: latestNetInflow,
        })
      }

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
        // 零轴基线（仅首条线附加，避免重复）；末端引导改由轴外 custom series 绘制
        markLine:
          idx === 0
            ? {
                silent: true,
                symbol: 'none',
                data: [{ yAxis: 0, lineStyle: { type: 'dashed' as const, color: '#9CA3AF' } }],
              }
            : undefined,
      }
    })

    // 末端引导：custom series 在 grid 右侧轴外区画 圆点+水平连线+文字。
    // clip:false 使图形不被 grid 裁剪；连线长度由 LEADER_PX 像素级控制。
    // data 为每条线末端点 [lastIdx, lastVal]，落在已有数据范围内，不影响轴范围。
    const LEADER_PX = 28
    const TEXT_GAP = 6
    // 文字最小垂直间距：行高(11) + 余量，保证多线末端气泡互不重叠
    const MIN_LABEL_GAP = 14
    const endGuideSeries = {
      type: 'custom' as const,
      clip: false,
      tooltip: { show: false },
      renderItem: (
        params: { dataIndex: number; coordSys: { x: number; width: number } },
        api: { coord: (data: [number, number]) => [number, number] }
      ) => {
        const meta = endLabelMeta[params.dataIndex]
        if (!meta) return undefined
        const p0 = api.coord([meta.lastIdx, meta.lastVal])
        if (!p0 || p0.some((n) => Number.isNaN(n))) return undefined
        const lineEndX = params.coordSys.x + params.coordSys.width + LEADER_PX
        // 防重叠：把所有板块终点像素 y 算出，按升序贪心下移，保证相邻文字 ≥ MIN_LABEL_GAP。
        // 每次 renderItem 重算（确定性 O(n log n)，n=板块数，可忽略）；文字错开后，
        // 连线终点 y 跟随文字 → 文字被挤下时连线自动变成指向文字的斜线。
        const finalY = (() => {
          const items = endLabelMeta.map((m, i) => ({
            i,
            origY: api.coord([m.lastIdx, m.lastVal])[1],
          }))
          items.sort((a, b) => a.origY - b.origY)
          let cursor = -Infinity
          let resolved = p0[1]
          for (const it of items) {
            const y = Math.max(it.origY, cursor)
            if (it.i === params.dataIndex) resolved = y
            cursor = y + MIN_LABEL_GAP
          }
          return resolved
        })()
        return {
          type: 'group',
          children: [
            // 末端锚点（曲线真实终点）
            {
              type: 'circle',
              shape: { cx: p0[0], cy: p0[1], r: 3 },
              style: { fill: meta.color },
            },
            // 终点 → 文字：终点 y 用错开后的 finalY，需要时为斜线
            {
              type: 'line',
              shape: { x1: p0[0], y1: p0[1], x2: lineEndX, y2: finalY },
              style: { stroke: meta.color, lineWidth: 1 },
            },
            // 文字气泡：板块名 + 最新净额（红正绿负）
            {
              type: 'text',
              style: {
                x: lineEndX + TEXT_GAP,
                y: finalY,
                text: `{n|${meta.name}}  {v|${formatSignedAmount(meta.lastVal)}}`,
                rich: {
                  n: {
                    fill: '#374151',
                    fontSize: 11,
                    width: 70,
                    overflow: 'truncate' as const,
                    ellipsis: '…',
                    textVerticalAlign: 'middle' as const,
                  },
                  v: {
                    fill: meta.valueColor,
                    fontSize: 11,
                    fontWeight: 600,
                    textVerticalAlign: 'middle' as const,
                  },
                },
                textVerticalAlign: 'middle' as const,
              },
            },
          ],
        }
      },
      data: endLabelMeta.map((m) => [m.lastIdx, m.lastVal]),
    }

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
            // 跳过末端引导 custom series（轴外装饰，不参与 tooltip）
            if ((p as { seriesType?: string }).seriesType === 'custom') return
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
        // 右侧留白给末端连线+气泡，避免被裁切
        left: '3%',
        right: '22%',
        bottom: '8%',
        top: '8%',
        containLabel: true,
      },
      xAxis: {
        type: 'category' as const,
        // 仅真实采样时间，不再追加占位刻度
        data: axisTimes.map((t) => formatSampleTime(t)),
        boundaryGap: false,
        axisLabel: {
          fontSize: 11,
          // category 轴默认 interval:'auto' 会按像素稀疏化刻度，
          // 盘中每分钟约 240 个刻度，15:00 常被跳过。这里显式控制：
          // 半小时整点(:00/:30)显示，并强制最后一个刻度(15:00 收盘)显示。
          interval: (index: number, value: string) => {
            if (index === axisTimes.length - 1) return true
            const mm = value.slice(-2)
            return mm === '00' || mm === '30'
          },
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
      series: [...echartsSeries, endGuideSeries],
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
