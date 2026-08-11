'use client'

/**
 * 单指数估值水位图（第 15 期 plan-04 Task 9）
 *
 * AC-03：有估值指数展示 PE/PB 曲线 + 前端计算当前值分位标注；
 *       无估值指数（hasData=false）显示"该指数暂无估值数据"。
 *
 * 实现：
 * - 单选指数（从 watchlist，默认选第一只）
 * - SWR 调 indexMonitorApi.getValuation(tsCode)
 * - 前端分位计算：对返回 peTtm 序列排序，计算当前值（最后一个非 null）百分位
 * - ECharts 双线（PE / PB），markLine 标注当前 PE 分位
 */
import React, { useMemo, useState, useEffect } from 'react'
import useSWR from 'swr'
import dynamic from 'next/dynamic'
import { Loader2, AlertCircle } from 'lucide-react'
import { indexMonitorApi } from '@/lib/api'
import type {
  IndexWatchlistItem,
  IndexValuationData,
} from '@/types/indexMonitorTypes'
import SimpleSelect from '@/components/ui/SimpleSelect'

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

const SWR_OPTIONS = { revalidateOnFocus: false, dedupingInterval: 30000 } as const

interface Props {
  watchlist: IndexWatchlistItem[]
}

export default function IndexValuationChart({ watchlist }: Props) {
  const [tsCode, setTsCode] = useState<string>(() => watchlist[0]?.tsCode ?? '')

  // watchlist 变化时若 tsCode 失效则重置
  useEffect(() => {
    if (watchlist.length > 0 && !watchlist.some((w) => w.tsCode === tsCode)) {
      setTsCode(watchlist[0].tsCode)
    } else if (watchlist.length > 0 && !tsCode) {
      setTsCode(watchlist[0].tsCode)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [watchlist.length])

  const selectOptions = useMemo(
    () =>
      watchlist.map((w) => ({
        value: w.tsCode,
        label: `${w.name}${w.hasValuation ? '' : '（无估值）'}`,
      })),
    [watchlist]
  )

  const { data: valRes, isLoading, error } = useSWR<{
    success: boolean
    data: IndexValuationData
  }>(
    tsCode ? ['indexValuation', tsCode] : null,
    () =>
      indexMonitorApi
        .getValuation(tsCode)
        .then((res) => res.data as unknown as {
          success: boolean
          data: IndexValuationData
        }),
    SWR_OPTIONS
  )
  const isError = error
  const valuation = valRes?.data ?? null

  // 前端分位计算（AC-03）：对 peTtm 非空序列排序，当前值百分位
  const percentile = useMemo(() => {
    if (!valuation || !valuation.hasData || valuation.points.length === 0) return null
    const peValues: number[] = []
    let currentValue: number | null = null
    valuation.points.forEach((p) => {
      if (p.peTtm !== null && p.peTtm !== undefined) {
        peValues.push(p.peTtm)
        currentValue = p.peTtm
      }
    })
    if (peValues.length === 0 || currentValue === null) return null
    const sorted = [...peValues].sort((a, b) => a - b)
    const below = sorted.filter((v) => v < (currentValue as number)).length
    return Math.round((below / sorted.length) * 100)
  }, [valuation])

  const option = useMemo(() => {
    if (!valuation || !valuation.hasData || valuation.points.length === 0) return null

    const dates = valuation.points.map((p) => p.tradeDate)
    const peData = valuation.points.map((p) => p.peTtm)
    const pbData = valuation.points.map((p) => p.pb)

    return {
      animation: true,
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      grid: { left: '3%', right: '6%', bottom: '8%', top: '12%', containLabel: true },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
        axisLabel: { fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        name: '倍',
        nameTextStyle: { fontSize: 11 },
        axisLabel: { fontSize: 11 },
        splitLine: { lineStyle: { type: 'dashed' } },
        scale: true,
      },
      series: [
        {
          name: 'PE(TTM)',
          type: 'line',
          data: peData,
          smooth: false,
          symbol: 'none',
          lineStyle: { width: 2, color: '#EF4444' },
          itemStyle: { color: '#EF4444' },
          connectNulls: false,
        },
        {
          name: 'PB',
          type: 'line',
          data: pbData,
          smooth: false,
          symbol: 'none',
          lineStyle: { width: 2, color: '#3B82F6' },
          itemStyle: { color: '#3B82F6' },
          connectNulls: false,
        },
      ],
    }
  }, [valuation])

  return (
    <section className="bg-card rounded-xl border border-border shadow-sm p-4 space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <h2 className="text-base font-semibold text-foreground">估值水位</h2>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">指数</span>
          <SimpleSelect
            value={tsCode}
            options={selectOptions}
            onChange={setTsCode}
            ariaLabel="选择指数"
            testId="index-valuation-select"
          />
        </div>
      </div>

      {/* 分位标注 */}
      {valuation?.hasData && percentile !== null && (
        <div className="text-sm text-muted-foreground">
          当前 PE 历史分位：
          <span className="ml-1 font-medium text-foreground">{percentile}%</span>
          <span className="ml-2">
            （{percentile >= 80 ? '高位' : percentile <= 20 ? '低位' : '中位'}）
          </span>
        </div>
      )}

      {/* 图表区 */}
      {!tsCode ? (
        <div className="h-80 flex items-center justify-center text-muted-foreground text-sm">
          请选择指数
        </div>
      ) : isLoading ? (
        <div className="h-80 flex items-center justify-center text-muted-foreground text-sm">
          <Loader2 className="w-4 h-4 animate-spin mr-2" />
          加载估值数据...
        </div>
      ) : isError ? (
        <div className="h-80 flex flex-col items-center justify-center text-destructive text-sm">
          <AlertCircle className="w-5 h-5 mb-2" />
          估值数据加载失败
        </div>
      ) : !valuation || !valuation.hasData ? (
        <div className="h-80 flex items-center justify-center text-muted-foreground text-sm">
          该指数暂无估值数据
        </div>
      ) : !option ? (
        <div className="h-80 flex items-center justify-center text-muted-foreground text-sm">
          暂无估值数据
        </div>
      ) : (
        <div data-testid="index-valuation-chart">
          <ReactECharts option={option} style={{ height: 360 }} />
        </div>
      )}
    </section>
  )
}
