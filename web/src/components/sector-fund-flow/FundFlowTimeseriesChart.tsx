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
 * - 每条曲线末端：custom series（clip:false）在 grid 右侧留白列画
 *   圆点 + 短斜线 + 文字气泡（板块名 + 最新净额，红正绿负）。文字位于绘图区外、
 *   专门标签列，不与曲线重叠；防重叠用「贴终点·最小让位」+ 边界 clamp，连线始终是短斜线、绝不溢出。
 *
 * 生长动画（自驱动，标签严格跟随曲线当前末端点）：
 * 放弃 ECharts 内置动画（line 的 clip 与 custom 的 enterFrom 机制独立、不同步，且 custom
 * 拿不到 clip 进度，标签 y 无法跟随）。改用 requestAnimationFrame 自驱：进度 p 从 0→1 线性
 * 推进（ANIM_MS 毫秒、linear），每帧按 p 截断曲线（亚像素 y 插值）并把标签贴在当前末端点上。
 * 曲线生长与标签位置由同一 p 驱动 → 严格同源同步，标签上下跟随曲线高低。
 *
 * 空态由父组件处理（未选板块引导态 / 无采样数据空态）；本组件仅在 series 非空时渲染。
 *
 * data-testid 约定：
 * - 容器：fund-flow-timeseries-chart
 */
import React, { useEffect, useMemo, useRef, useState } from 'react'
import dynamic from 'next/dynamic'
import type { EChartsInstance } from 'echarts-for-react'
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

// 生长动画时长（毫秒）。进度 p 从 0→1 线性推进，标签跟随曲线当前末端点。
const ANIM_MS = 1800

/**
 * A 股完整交易日连续竞价时段的分钟刻度（含两端），用于固定盘中曲线横轴。
 * 9:30-11:30 / 13:00-15:00，跳过午休。共 242 个点。
 * 横轴始终覆盖完整交易日，与采样进度无关：盘中只采到 10:00 时横轴也延伸到 15:00，
 * 曲线只画到当前采样点，后续为断线空白。格式与 formatSampleTime 输出一致（"HH:MM"）。
 */
const TRADING_DAY_AXIS_TIMES: string[] = (() => {
  const times: string[] = []
  const pushRange = (startH: number, startM: number, endH: number, endM: number) => {
    let h = startH
    let m = startM
    // 含两端：走到 endH:endM（含）
    while (h < endH || (h === endH && m <= endM)) {
      times.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`)
      m += 1
      if (m === 60) {
        m = 0
        h += 1
      }
    }
  }
  pushRange(9, 30, 11, 30) // 上午：121 点
  pushRange(13, 0, 15, 0) // 下午：121 点
  return times
})()

export interface FundFlowTimeseriesChartProps {
  data: FundFlowTimeseriesData
  height?: string
}

export default function FundFlowTimeseriesChart({
  data,
  height = '420px',
}: FundFlowTimeseriesChartProps) {
  // ECharts 实例（通过 onChartReady 获取，供 RAF 每帧 setOption）
  const chartRef = useRef<EChartsInstance | null>(null)
  // 实例就绪标记：onChartReady 后置 true，触发动画 useEffect 启动（解决执行顺序）
  const [ready, setReady] = useState(false)

  // 横轴时间：固定为完整交易日连续竞价时段（9:30-11:30 / 13:00-15:00，跳过午休）。
  // 与采样进度无关——盘中只采到 10:00 时横轴也延伸到 15:00，保证横轴始终是完整交易日。
  const axisTimes = useMemo(() => TRADING_DAY_AXIS_TIMES, [])

  // 每条线的预处理：按 axisTimes 对齐的真实值序列 + 颜色 + 末端真实净额。
  // 这些与进度无关，提前算好；进度只驱动截断与插值。
  // 注意：采样点 sampleTime 是 ISO 字符串，固定轴 key 是 "HH:MM"，
  // 这里用 formatSampleTime 归一化后再查表对齐。
  const linePrep = useMemo(() => {
    const series = data.series ?? []
    return series.map((s, idx) => {
      const lineColor = SERIES_COLORS[idx % SERIES_COLORS.length]
      const pointMap = new Map<string, number | null>()
      s.data.forEach((p) => {
        pointMap.set(formatSampleTime(p.sampleTime), p.netInflow)
      })
      // 各时点净额（亿元）：undefined（无采样）与 null（采样值空）都断线
      const pointValues: Array<number | null> = axisTimes.map((t) => {
        const v = pointMap.get(t)
        if (v === undefined || v === null) return null
        return Number(v.toFixed(2))
      })
      // 末端真实净额：最后一个非 null 采样点（p=1 结束态的显示值）
      let latestNetInflow: number | null = null
      for (let i = pointValues.length - 1; i >= 0; i--) {
        if (pointValues[i] !== null) {
          latestNetInflow = pointValues[i]
          break
        }
      }
      return {
        sectorName: s.sectorName,
        lineColor,
        pointValues,
        latestNetInflow,
      }
    })
  }, [data, axisTimes])

  /**
   * 按进度 p（0→1）构建完整 ECharts option。
   * 曲线按 p 截断（亚像素 y 插值），标签贴在当前末端点上 → 严格同源同步。
   * p=1 时无截断，即完整数据。
   */
  const buildOption = useMemo(() => {
    return (p: number) => {
      const lines = linePrep
      if (lines.length === 0) return null

      // 每条线在当前进度下的：截断后的 data + 当前末端 [endIdx, endVal（插值）]。
      // endVal 用亚像素插值，标签 y 丝滑跟随曲线高低起伏。
      const perLine = lines.map((line) => {
        const values = line.pointValues
        const validIdx: number[] = []
        for (let i = 0; i < values.length; i++) {
          if (values[i] !== null) validIdx.push(i)
        }
        // 无有效点：整线 null，标签隐藏
        if (validIdx.length === 0) {
          return {
            ...line,
            truncatedData: values.map(() => null) as Array<number | null>,
            endIdx: -1,
            endVal: null as number | null,
          }
        }
        // p: 0→1 映射到 validIdx 序列 0→(len-1)（按各线有效点序列推进，断线时停在断点前）
        const g = p * (validIdx.length - 1)
        const segBase = Math.min(Math.floor(g), validIdx.length - 1)
        const frac = g - segBase
        const baseAxisIdx = validIdx[segBase]
        // 截断 data：baseAxisIdx 之前（含）保留真实值，之后全 null
        const truncatedData: Array<number | null> = values.map((v, i) =>
          i <= baseAxisIdx ? v : null
        )
        // 当前末端 y：亚像素插值（在 baseAxisIdx 与下一个有效点之间）
        let endVal: number | null
        const baseVal = values[baseAxisIdx]
        if (segBase >= validIdx.length - 1 || frac < 1e-6) {
          endVal = baseVal
        } else {
          const nextAxisIdx = validIdx[segBase + 1]
          const nextVal = values[nextAxisIdx]
          endVal = baseVal! + (nextVal! - baseVal!) * frac
        }
        return { ...line, truncatedData, endIdx: baseAxisIdx, endVal }
      })

      // 末端标签元信息（用于防重叠 + renderItem）。颜色用动画末端的插值值判定。
      const endLabelMeta = perLine
        .filter((l) => l.endIdx >= 0 && l.endVal !== null)
        .map((l) => {
          const v = l.endVal!
          const valueColor = v === 0 ? '#6B7280' : v > 0 ? '#EF4444' : '#10B981'
          return {
            name: l.sectorName,
            color: l.lineColor,
            valueColor,
            lastIdx: l.endIdx,
            lastVal: v,
          }
        })

      // line series：稳定 id 配合 replaceMerge，取消板块时精确移除
      const echartsSeries = perLine.map((line, idx) => ({
        id: `line-${line.sectorName}`,
        name: line.sectorName,
        type: 'line' as const,
        data: line.truncatedData,
        smooth: false,
        symbol: 'circle',
        symbolSize: 5,
        showSymbol: false,
        lineStyle: { width: 2, color: line.lineColor },
        itemStyle: { color: line.lineColor },
        connectNulls: false,
        // 零轴基线（仅首条线附加，避免重复）
        markLine:
          idx === 0
            ? {
                silent: true,
                symbol: 'none',
                data: [{ yAxis: 0, lineStyle: { type: 'dashed' as const, color: '#9CA3AF' } }],
              }
            : undefined,
      }))

      // 末端引导 custom series（圆点 + 短斜线 + 文字气泡）
      // 几何常量：单位均为像素。中文 fontSize:11 实际渲染行高约 16-18px，
      // 间距分两档自适应：充裕用 GOAL_GAP(18)，紧张收缩到 FLOOR_GAP(12)，
      // 极拥挤（标签数超过可用高度）线性压缩保证全部可见、不顶出画布。
      const LEADER_PX = 16            // 末端点 → 文字气泡的水平连线长度
      const TEXT_GAP = 4              // 连线终点 → 文字左边缘的间隙
      const GOAL_GAP = 18             // 目标间距（空间充裕，≥ 中文行高）
      const FLOOR_GAP = 12            // 极限下限（空间紧张收缩到此，仍勉强可读）
      const LABEL_PADDING_X = 5       // 文字背景圆角矩形左右内边距
      const LABEL_PADDING_Y = 2       // 文字背景圆角矩形上下内边距
      const LABEL_RADIUS = 3          // 文字背景圆角半径

      // 防重叠放置：阶段1 贪心「仅下推」保证相邻 ≥ gap 且不重叠就不让位（自适应）；
      // 阶段2 边界适配修正顶/底消失。返回每个标签的 [y, 生效间距]。
      // - span <= availSpan（能放下）：求合法平移区间，必非空 → 平移后顶/底都在界内。
      // - span >  availSpan（放不下）：线性映射到边界内，等比压缩，全部可见。
      const placeLabels = (
        items: Array<{ i: number; origY: number }>,
        gap: number,
        topLimit: number,
        bottomLimit: number
      ): Array<{ y: number; effGap: number }> => {
        // 阶段1：贪心放置（仅下推，不重叠就不让位 → 自然贴近曲线末端原位）
        const placedY: number[] = []
        for (const it of items) {
          let y = it.origY
          if (placedY.length > 0) {
            const last = placedY[placedY.length - 1]
            if (last + gap > y) y = last + gap
          }
          placedY.push(y)
        }
        // 阶段2：边界适配
        const minY = placedY[0]
        const maxY = placedY[placedY.length - 1]
        const span = maxY - minY
        const availSpan = bottomLimit - topLimit
        if (span <= availSpan) {
          // 能放下：合法平移区间 [lo, hi] 非空（span<=availSpan 保证 lo<=hi），取最近 0 的值
          const lo = topLimit - minY
          const hi = bottomLimit - maxY
          let shift = 0
          if (lo <= 0 && hi >= 0) {
            shift = 0 // 原位即合法
          } else if (hi < 0) {
            shift = hi // 整体上移（maxY 超 bottomLimit）
          } else {
            shift = lo // lo > 0，整体下移（minY 低于 topLimit）
          }
          const shifted = placedY.map((y) => y + shift)
          return shifted.map((y) => ({ y, effGap: gap }))
        }
        // 放不下：线性映射到 [topLimit, bottomLimit]，等比压缩，全部可见
        const scale = span > 0 ? availSpan / span : 1
        const scaled = placedY.map((y) => topLimit + (y - minY) * scale)
        // 压缩后相邻间距 ≈ availSpan/(n-1)（n=1 时无意义，给个兜底）
        const compressedGap = items.length > 1 ? availSpan / (items.length - 1) : gap
        return scaled.map((y) => ({ y, effGap: compressedGap }))
      }
      const endGuideSeries = {
        id: 'end-guide',
        type: 'custom' as const,
        clip: false,
        tooltip: { show: false },
        renderItem: (
          params: {
            dataIndex: number
            coordSys: { x: number; y: number; width: number; height: number }
          },
          api: { coord: (d: [number, number]) => [number, number] }
        ) => {
          const meta = endLabelMeta[params.dataIndex]
          if (!meta) return undefined
          // 当前末端点的像素坐标（随 p 变化 → 标签跟随）
          const p0 = api.coord([meta.lastIdx, meta.lastVal])
          if (!p0 || p0.some((n) => Number.isNaN(n))) return undefined
          const [p0x, p0y] = p0
          // 连线终点 x：相对 group 原点（在末端点 p0x）向右 LEADER_PX。
          // 不能用 coordSys.width（那是 grid 总宽度，加到 group 上会让文字水平溢出）。
          const lineEndX = LEADER_PX

          // 防重叠 + 边界适配（自适应间距，保证所有标签可见）：
          // 用 placeLabels 纯函数放置。gap 自适应选择：
          // 1. 先用目标间距 GOAL_GAP 放置；
          // 2. 若目标放不下（触发了线性压缩）但下限间距能放下，降级 FLOOR_GAP 重放——
          //    避免不必要的压缩、尽量保持可读间距；
          // 3. 仍放不下（极拥挤）则接受线性压缩，全部可见。
          const { finalY, effGap } = (() => {
            const halfLine = FLOOR_GAP / 2 // 边界半行用下限，给压缩留余量
            const topLimit = params.coordSys.y + halfLine
            const bottomLimit = params.coordSys.y + params.coordSys.height - halfLine
            const items = endLabelMeta
              .map((m, i) => ({ i, origY: api.coord([m.lastIdx, m.lastVal])[1] }))
              .sort((a, b) => a.origY - b.origY)

            const availSpan = bottomLimit - topLimit
            const needSpanAt = (gap: number) =>
              items.length > 1 ? gap * (items.length - 1) : 0

            // 目标间距能放下，直接用；否则尝试下限；仍不行则线性压缩
            const useGap =
              needSpanAt(GOAL_GAP) <= availSpan
                ? GOAL_GAP
                : needSpanAt(FLOOR_GAP) <= availSpan
                  ? FLOOR_GAP
                  : GOAL_GAP // 进入 placeLabels 的线性压缩分支

            const placed = placeLabels(items, useGap, topLimit, bottomLimit)
            const idx = items.findIndex((it) => it.i === params.dataIndex)
            const target = placed[idx] ?? { y: p0y, effGap: useGap }
            return { finalY: target.y, effGap: target.effGap }
          })()

          // 文字内容（板块名 + 最新净额，红正绿负）
          const labelText = `${meta.name} ${formatSignedAmount(meta.lastVal)}`
          // canvas 文字宽度估算（fontSize:11 中文约 11px/字，数字/符号约 6px）。
          // 用于画背景矩形，避免文字与曲线/其他标签糊在一起。
          const charWidth = 11
          const cjkRe = /[\u4e00-\u9fff]/
          let textWidth = 0
          for (const ch of labelText) {
            textWidth += cjkRe.test(ch) ? charWidth : charWidth * 0.6
          }

          return {
            type: 'group',
            x: p0x,
            y: p0y,
            children: [
              // 末端锚点（当前曲线末端点）——相对原点 (0,0)
              { type: 'circle', shape: { cx: 0, cy: 0, r: 3 }, style: { fill: meta.color } },
              // 末端(0,0) → 文字左边缘：水平分量 LEADER_PX + 防重叠垂直错开
              {
                type: 'line',
                shape: { x1: 0, y1: 0, x2: lineEndX, y2: finalY - p0y },
                style: { stroke: meta.color, lineWidth: 1 },
              },
              // 文字背景：半透明圆角矩形，提升可读性并提供视觉缓冲。
              // 高度跟随实际生效间距 effGap（压缩场景下同步缩小，避免背景框重叠）
              {
                type: 'rect',
                shape: {
                  x: lineEndX + TEXT_GAP - LABEL_PADDING_X,
                  y: finalY - p0y - effGap / 2 + LABEL_PADDING_Y,
                  width: textWidth + LABEL_PADDING_X * 2,
                  height: effGap - LABEL_PADDING_Y * 2,
                  r: LABEL_RADIUS,
                },
                style: {
                  fill: 'rgba(255, 255, 255, 0.78)',
                },
                z: 1,
              },
              // 文字气泡：板块名 + 最新净额（红正绿负），左对齐文字起点
              {
                type: 'text',
                z: 2,
                style: {
                  x: lineEndX + TEXT_GAP,
                  y: finalY - p0y,
                  text: labelText,
                  fill: meta.valueColor,
                  fontSize: 11,
                  fontWeight: 600,
                  textAlign: 'left' as const,
                  textVerticalAlign: 'middle' as const,
                },
              },
            ],
          }
        },
        // data 项 = 当前末端 [endIdx, endVal（插值）]，随 p 变化；key 用于 diff 移除
        data: endLabelMeta.map((m) => ({ key: m.name, value: [m.lastIdx, m.lastVal] })),
      }

      return {
        // 关闭 ECharts 内置动画：由外部 RAF 自驱，避免内置动画与 RAF 冲突产生双重动画/闪烁
        animation: false,
        tooltip: {
          trigger: 'axis' as const,
          // 多板块叠加时 tooltip 行数可能很长，限高滚动避免遮挡图表
          confine: true,
          formatter: (params: unknown) => {
            const arr = params as Array<{
              axisValue: string
              data: number | null
              color: string
              seriesName: string
              seriesType?: string
            }>
            if (!arr || arr.length === 0) return ''
            const t = arr[0].axisValue // axisValue 已是 "HH:MM"（xAxis.data 即轴时间）
            let html = `<div style="font-weight:600;margin-bottom:4px;">${t}</div>`
            html += '<div style="max-height:240px;overflow-y:auto;">'
            arr.forEach((p) => {
              // 跳过末端引导 custom series（右侧标签列装饰，不参与 tooltip）
              if (p.seriesType === 'custom') return
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
          // 右侧留白作为标签列：板块名/净额气泡画在 grid 右侧轴外区，
          // 与曲线分属不同区域，不重叠；留白宽度需容纳约 7 个中文字 + 净额。
          left: '3%',
          right: '20%',
          bottom: '8%',
          top: '8%',
          containLabel: true,
        },
        xAxis: {
          type: 'category' as const,
          data: axisTimes,
          boundaryGap: false,
          axisLabel: {
            fontSize: 11,
            // category 轴默认 interval:'auto' 会按像素稀疏化刻度，
            // 盘中每分钟约 240 个刻度，15:00 常被跳过。这里显式控制：
            // 半小时整点(:00/:30)显示，并强制最后一个刻度(15:00 收盘)显示。
            // 特例：固定轴跳过午休后 11:30 与 13:00 是相邻刻度（像素紧贴），
            // 两者都命中 :00/:30 会重叠 → 隐藏 11:30，保留 13:00（下午开盘整点）。
            interval: (index: number, value: string) => {
              if (index === axisTimes.length - 1) return true
              if (value === '11:30') return false
              const mm = value.slice(-2)
              return mm === '00' || mm === '30'
            },
          },
        },
        yAxis: {
          type: 'value' as const,
          name: '净额(亿)',
          nameTextStyle: { fontSize: 11 },
          axisLabel: { formatter: '{value}', fontSize: 11 },
          splitLine: { lineStyle: { type: 'dashed' as const } },
        },
        series: [...echartsSeries, endGuideSeries],
      }
    }
  }, [linePrep, axisTimes])

  // 最终态 option（p=1），供 ReactECharts 首次挂载渲染（SSR/首屏直接显示完整曲线）
  const finalOption = useMemo(() => buildOption(1), [buildOption])

  // 自驱动生长动画：data 变化（含刷新延长、取消板块）时从 p=0 重播。
  // 用 RAF 每帧 setOption(buildOption(p))，曲线截断与标签位置同源于 p → 严格同步。
  useEffect(() => {
    const inst = chartRef.current
    if (!inst || linePrep.length === 0) return
    let rafId = 0
    const start = performance.now()
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / ANIM_MS)
      const opt = buildOption(p)
      if (opt) {
        // replaceMerge:['series'] 让 ECharts 按 series.id 增删（取消板块时精确移除）
        inst.setOption(opt, { replaceMerge: ['series'] })
      }
      if (p < 1) {
        rafId = requestAnimationFrame(tick)
      }
    }
    rafId = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafId)
  }, [buildOption, linePrep, ready])

  if (!finalOption) {
    return null
  }

  return (
    <div
      data-testid="fund-flow-timeseries-chart"
      className="border rounded-lg bg-card p-4"
    >
      <ReactECharts
        onChartReady={(inst) => {
          chartRef.current = inst
          setReady(true)
        }}
        option={finalOption}
        style={{ height, width: '100%' }}
        opts={{ renderer: 'canvas' }}
      />
    </div>
  )
}
