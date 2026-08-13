'use client'

/**
 * 多指数走势对比图（第 15 期 plan-04 Task 8）
 *
 * AC-02：选择多只指数（不限制数量，默认全选）后展示收盘价走势；归一化开关（基准日=100）
 *       方便量级不同的指数（如上证指数 3000 点 vs 创业板指 2000 点）对比涨跌幅。
 *
 * 实现：
 * - 从 watchlist 多选指数（不限制数量，默认全选）
 * - 归一化：以各自首日 close 为基准 100，后续按比例换算
 * - 原始：双 yAxis（量级差异大时可分别对比），这里用单 yAxis + 归一化切换更直观
 * - ECharts 多 line series，tooltip 显示各指数当日 close / 归一化值
 *
 * SWR 调 indexMonitorApi.getTrend(tsCodes, start, end)，默认拉近 1 年。
 */
import React, { useMemo, useState } from 'react'
import useSWR from 'swr'
import dynamic from 'next/dynamic'
import { Loader2, AlertCircle } from 'lucide-react'
import { indexMonitorApi } from '@/lib/api'
import type {
  IndexWatchlistItem,
  IndexTrendData,
} from '@/types/indexMonitorTypes'

// 动态导入 ECharts（ssr:false，与 EtfTrendChart / FundFlowTimeseriesChart 范式一致）
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

// 默认全选时最多可达 14 只关注指数，颜色尽量互不重复
const SERIES_COLORS = [
  '#EF4444',
  '#3B82F6',
  '#10B981',
  '#F59E0B',
  '#8B5CF6',
  '#EC4899',
  '#06B6D4',
  '#F97316',
  '#14B8A6',
  '#6366F1',
  '#84CC16',
  '#D946EF',
  '#0EA5E9',
  '#A855F7',
]

const SWR_OPTIONS = { revalidateOnFocus: false, dedupingInterval: 30000 } as const

interface Props {
  watchlist: IndexWatchlistItem[]
}

export default function IndexTrendChart({ watchlist }: Props) {
  // 默认全选（不限制选择数量）
  const [selected, setSelected] = useState<string[]>(() =>
    watchlist.map((w) => w.tsCode)
  )
  const [normalize, setNormalize] = useState(false)

  // watchlist 变化时重置默认选中（全选）——渲染期调整 state（React 官方范式）
  const [prevWatchlistLength, setPrevWatchlistLength] = useState(watchlist.length)
  if (prevWatchlistLength !== watchlist.length) {
    setPrevWatchlistLength(watchlist.length)
    setSelected(watchlist.map((w) => w.tsCode))
  }

  const toggleSelect = (tsCode: string) => {
    setSelected((prev) => {
      if (prev.includes(tsCode)) {
        return prev.filter((c) => c !== tsCode)
      }
      return [...prev, tsCode]
    })
  }

  // SWR：selected 为空不发请求
  const { data: trendRes, isLoading, error } = useSWR<{
    success: boolean
    data: IndexTrendData
  }>(
    selected.length > 0 ? ['indexTrend', selected] : null,
    () =>
      indexMonitorApi
        .getTrend(selected)
        .then((res) => res.data as unknown as {
          success: boolean
          data: IndexTrendData
        }),
    SWR_OPTIONS
  )
  const isError = error
  const trend = trendRes?.data ?? null

  // 构建统一横轴（所有 series 的 tradeDate 并集，升序）
  const allDates = useMemo(() => {
    if (!trend) return []
    const set = new Set<string>()
    trend.series.forEach((s) => s.points.forEach((p) => set.add(p.tradeDate)))
    return Array.from(set).sort()
  }, [trend])

  // 构建 ECharts option
  const option = useMemo(() => {
    if (!trend || trend.series.length === 0 || allDates.length === 0) return null

    const series = trend.series.map((s, idx) => {
      const color = SERIES_COLORS[idx % SERIES_COLORS.length]
      // close 按 tradeDate 索引
      const closeMap = new Map<string, number | null>()
      s.points.forEach((p) => closeMap.set(p.tradeDate, p.close))

      // 找首个非 null close 作为归一化基准
      let base = 100
      if (normalize) {
        for (const d of allDates) {
          const v = closeMap.get(d)
          if (v !== null && v !== undefined && v > 0) {
            base = v
            break
          }
        }
      }

      const data = allDates.map((d) => {
        const v = closeMap.get(d)
        if (v === undefined || v === null) return null
        return normalize && v > 0 ? Number(((v / base) * 100).toFixed(2)) : v
      })

      return {
        name: s.name,
        type: 'line' as const,
        data,
        smooth: false,
        symbol: 'circle',
        symbolSize: 4,
        showSymbol: allDates.length <= 31,
        lineStyle: { width: 2, color },
        itemStyle: { color },
        connectNulls: false,
      }
    })

    return {
      animation: true,
      tooltip: {
        trigger: 'axis',
      },
      legend: {
        top: 0,
        type: 'scroll' as const,
      },
      grid: { left: '3%', right: '6%', bottom: '8%', top: '12%', containLabel: true },
      xAxis: {
        type: 'category',
        data: allDates,
        boundaryGap: false,
        axisLabel: { fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        name: normalize ? '归一化(基准=100)' : '收盘价',
        nameTextStyle: { fontSize: 11 },
        axisLabel: { fontSize: 11 },
        splitLine: { lineStyle: { type: 'dashed' } },
        scale: true,
      },
      series,
    }
  }, [trend, allDates, normalize])

  return (
    <section className="bg-card rounded-xl border border-border shadow-sm p-4 space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <h2 className="text-base font-semibold text-foreground">多指数走势对比</h2>
        <div className="flex items-center gap-3">
          <label className="inline-flex items-center gap-1.5 text-sm text-muted-foreground cursor-pointer">
            <input
              type="checkbox"
              checked={normalize}
              onChange={(e) => setNormalize(e.target.checked)}
              className="rounded"
            />
            归一化（基准日=100）
          </label>
        </div>
      </div>

      {/* 指数选择 */}
      <div className="flex flex-wrap gap-2">
        {watchlist.map((w) => {
          const active = selected.includes(w.tsCode)
          return (
            <button
              key={w.tsCode}
              type="button"
              onClick={() => toggleSelect(w.tsCode)}
              className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                active
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-card text-muted-foreground border-border hover:border-primary/50'
              }`}
            >
              {w.name}
            </button>
          )
        })}
      </div>
      <p className="text-xs text-muted-foreground">
        已选 {selected.length} / {watchlist.length} 只
      </p>

      {/* 图表区 */}
      {selected.length === 0 ? (
        <div className="h-80 flex items-center justify-center text-muted-foreground text-sm">
          请选择至少 1 只指数
        </div>
      ) : isLoading ? (
        <div className="h-80 flex items-center justify-center text-muted-foreground text-sm">
          <Loader2 className="w-4 h-4 animate-spin mr-2" />
          加载走势数据...
        </div>
      ) : isError ? (
        <div className="h-80 flex flex-col items-center justify-center text-destructive text-sm">
          <AlertCircle className="w-5 h-5 mb-2" />
          走势数据加载失败
        </div>
      ) : !trend || !trend.hasData || !option ? (
        <div className="h-80 flex items-center justify-center text-muted-foreground text-sm">
          暂无走势数据
        </div>
      ) : (
        <div data-testid="index-trend-chart">
          <ReactECharts option={option} style={{ height: 360 }} />
        </div>
      )}
    </section>
  )
}
