'use client'

import { memo, useMemo } from 'react'
import dynamic from 'next/dynamic'
import type { SectorMAHistoryPoint, MAPeriod } from '@/types'
import { LoadingState } from './LoadingState'

// 动态导入 ECharts 组件
const ReactECharts = dynamic(
  () => import('echarts-for-react').then((mod) => mod.default),
  {
    ssr: false,
    loading: () => <LoadingState message="加载均线图表..." />,
  }
)

interface SectorMAChartProps {
  data: SectorMAHistoryPoint[]
  sectorName: string
  visibleMAs: Record<MAPeriod, boolean>
  height?: string
}

// 均线颜色配置
const MA_COLORS: Record<MAPeriod, string> = {
  ma5: '#EF4444',
  ma10: '#F59E0B',
  ma20: '#FBBF24',
  ma30: '#10B981',
  ma60: '#3B82F6',
  ma90: '#6366F1',
  ma120: '#8B5CF6',
  ma240: '#EC4899',
}

export const SectorMAChart = memo(function SectorMAChart({
  data,
  sectorName,
  visibleMAs,
  height = '400px',
}: SectorMAChartProps) {
  // ECharts 配置
  const option = useMemo(() => {
    if (!data || data.length === 0) {
      return null
    }

    const dates = data.map((d) => d.date)

    // 构建系列数据
    const series: any[] = []

    // 当前价格 (虚线)
    const currentPrices = data.map((d) => d.current_price)
    if (currentPrices.some((p) => p !== null)) {
      series.push({
        name: '当前价格',
        type: 'line',
        data: currentPrices,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2,
          type: 'dashed',
          color: '#9CA3AF',
        },
      })
    }

    // 均线系列
    const maPeriods: MAPeriod[] = ['ma5', 'ma10', 'ma20', 'ma30', 'ma60', 'ma90', 'ma120', 'ma240']
    maPeriods.forEach((period) => {
      if (!visibleMAs[period]) return

      const maData = data.map((d) => d[period])
      if (maData.every((v) => v === null || v === undefined)) return

      series.push({
        name: period.toUpperCase(),
        type: 'line',
        data: maData,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2,
          color: MA_COLORS[period],
        },
      })
    })

    // 如果没有任何系列数据，返回空配置
    if (series.length === 0) {
      return null
    }

    return {
      title: {
        text: `${sectorName} - 均线分析`,
        left: 'center',
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold',
        },
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          if (!params || params.length === 0) return ''
          const param = params[0]
          const point = data[param.dataIndex]
          if (!point) return ''

          const date = new Date(point.date).toLocaleDateString('zh-CN')
          let tooltip = `<div style="padding: 4px;"><div style="font-weight: bold; margin-bottom: 4px;">${date}</div>`

          // 添加当前价格
          if (point.current_price) {
            tooltip += `<div>当前价格: ¥${point.current_price.toFixed(2)}</div>`
          }

          // 添加均线数据
          const maPeriods: MAPeriod[] = ['ma5', 'ma10', 'ma20', 'ma30', 'ma60', 'ma90', 'ma120', 'ma240']
          maPeriods.forEach((period) => {
            if (visibleMAs[period] && point[period]) {
              tooltip += `<div style="color: ${MA_COLORS[period]}">${period.toUpperCase()}: ${point[period]?.toFixed(2)}</div>`
            }
          })

          tooltip += '</div>'
          return tooltip
        },
      },
      legend: {
        bottom: 10,
        data: ['当前价格', ...maPeriods.filter((p) => visibleMAs[p]).map((p) => p.toUpperCase())],
        selected: Object.fromEntries(
          Object.entries(visibleMAs).map(([key, value]) => [key.toUpperCase(), value])
        ),
      },
      grid: {
        left: '5%',
        right: '5%',
        bottom: '15%',
        top: '15%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: {
          rotate: 45,
          formatter: (value: string) => {
            const date = new Date(value)
            return `${date.getMonth() + 1}/${date.getDate()}`
          },
        },
      },
      yAxis: {
        type: 'value',
        scale: true, // 自动计算最小最大值
        splitLine: {
          lineStyle: {
            type: 'dashed',
          },
        },
      },
      series,
      dataZoom: [
        {
          type: 'inside',
          yAxisIndex: 0,
          start: 0,
          end: 100,
        },
        {
          type: 'slider',
          yAxisIndex: 0,
          start: 0,
          end: 100,
          height: 20,
          bottom: 50,
        },
      ],
    }
  }, [data, sectorName, visibleMAs])

  if (!data || data.length === 0 || !option) {
    return (
      <div
        className="flex items-center justify-center border rounded-lg bg-background"
        style={{ height }}
        role="img"
        aria-label={`${sectorName}均线分析图表 - 暂无数据`}
      >
        <div className="text-muted-foreground text-center">
          <div className="text-4xl mb-2">📈</div>
          <div>暂无均线历史数据</div>
        </div>
      </div>
    )
  }

  // 计算可见均线数量（用于无障碍描述）
  const visibleMACount = Object.values(visibleMAs).filter(Boolean).length

  return (
    <div className="border rounded-lg bg-card p-4">
      <ReactECharts
        option={option}
        style={{ height, width: '100%' }}
        opts={{ renderer: 'canvas' }}
        aria-label={`${sectorName}均线分析图，显示${data.length}个数据点，${visibleMACount}条均线`}
        role="img"
      />
    </div>
  )
})
