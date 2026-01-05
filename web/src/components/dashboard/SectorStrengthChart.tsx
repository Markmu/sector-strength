'use client'

import { memo, useMemo } from 'react'
import dynamic from 'next/dynamic'
import type { SectorStrengthHistoryPoint } from '@/types'
import { LoadingState } from './LoadingState'

// 动态导入 ECharts 组件
const ReactECharts = dynamic(
  () => import('echarts-for-react').then((mod) => mod.default),
  {
    ssr: false,
    loading: () => <LoadingState message="加载强度图表..." />,
  }
)

interface SectorStrengthChartProps {
  data: SectorStrengthHistoryPoint[]
  sectorName: string
  height?: string
}

export const SectorStrengthChart = memo(function SectorStrengthChart({
  data,
  sectorName,
  height = '400px',
}: SectorStrengthChartProps) {
  // ECharts 配置
  const option = useMemo(() => {
    if (!data || data.length === 0) {
      return null
    }

    const dates = data.map((d) => d.date)
    const scores = data.map((d) => d.score)

    return {
      title: {
        text: `${sectorName} - 强度历史`,
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
          const score = point.score?.toFixed(2) ?? 'N/A'
          const price = point.current_price
            ? `¥${point.current_price.toFixed(2)}`
            : 'N/A'

          return `
            <div style="padding: 4px;">
              <div style="font-weight: bold; margin-bottom: 4px;">${date}</div>
              <div>强度得分: ${score}</div>
              <div>当前价格: ${price}</div>
            </div>
          `
        },
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
        min: 0,
        max: 100,
        axisLabel: {
          formatter: '{value}',
        },
        splitLine: {
          lineStyle: {
            type: 'dashed',
          },
        },
      },
      series: [
        {
          name: '强度得分',
          type: 'line',
          data: scores,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: {
            width: 2,
            color: '#3B82F6',
          },
          itemStyle: {
            color: '#3B82F6',
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                { offset: 1, color: 'rgba(59, 130, 246, 0.05)' },
              ],
            },
          },
        },
      ],
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
          bottom: 10,
        },
      ],
    }
  }, [data, sectorName])

  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center border rounded-lg bg-gray-50"
        style={{ height }}
        role="img"
        aria-label={`${sectorName}强度历史图表 - 暂无数据`}
      >
        <div className="text-gray-500 text-center">
          <div className="text-4xl mb-2">📊</div>
          <div>暂无强度历史数据</div>
        </div>
      </div>
    )
  }

  return (
    <div className="border rounded-lg bg-white p-4">
      <ReactECharts
        option={option}
        style={{ height, width: '100%' }}
        opts={{ renderer: 'canvas' }}
        aria-label={`${sectorName}强度历史趋势图，显示${data.length}个数据点`}
        role="img"
      />
    </div>
  )
})
