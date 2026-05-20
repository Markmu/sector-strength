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

// 强度类型配置
const STRENGTH_TYPES = {
  composite: {
    name: '综合强度',
    key: 'score' as const,
    color: '#3B82F6',
    lineWidth: 3,
  },
  short: {
    name: '短期强度',
    key: 'short_term_score' as const,
    color: '#10B981',
    lineWidth: 2,
  },
  medium: {
    name: '中期强度',
    key: 'medium_term_score' as const,
    color: '#F59E0B',
    lineWidth: 2,
  },
  long: {
    name: '长期强度',
    key: 'long_term_score' as const,
    color: '#8B5CF6',
    lineWidth: 2,
  },
} as const

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

    // 构建系列数据
    const series: any[] = []

    // 为每种强度类型创建一个系列
    Object.values(STRENGTH_TYPES).forEach((type) => {
      const values = data.map((d) => d[type.key])

      // 检查是否有数据
      if (values.every((v) => v === null || v === undefined)) {
        return
      }

      series.push({
        name: type.name,
        type: 'line',
        data: values,
        smooth: true,
        symbol: 'circle',
        symbolSize: type.key === 'score' ? 6 : 4,
        lineStyle: {
          width: type.lineWidth,
          color: type.color,
        },
        itemStyle: {
          color: type.color,
        },
        // 只为综合强度添加面积图
        ...(type.key === 'score' ? {
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
        } : {}),
      })
    })

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
          let tooltip = `<div style="padding: 4px;"><div style="font-weight: bold; margin-bottom: 8px;">${date}</div>`

          // 添加各强度类型数据
          Object.values(STRENGTH_TYPES).forEach((type) => {
            const value = point[type.key]
            if (value !== null && value !== undefined) {
              tooltip += `<div style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">
                <span style="display: inline-block; width: 12px; height: 12px; background-color: ${type.color}; border-radius: 50%;"></span>
                <span>${type.name}: ${value.toFixed(2)}</span>
              </div>`
            }
          })

          // 添加当前价格
          if (point.current_price) {
            tooltip += `<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e5e7eb;">
              当前价格: ¥${point.current_price.toFixed(2)}
            </div>`
          }

          tooltip += '</div>'
          return tooltip
        },
      },
      legend: {
        bottom: 10,
        data: Object.values(STRENGTH_TYPES).map((t) => t.name),
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
  }, [data, sectorName])

  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center border rounded-lg bg-background"
        style={{ height }}
        role="img"
        aria-label={`${sectorName}强度历史图表 - 暂无数据`}
      >
        <div className="text-muted-foreground text-center">
          <div className="text-4xl mb-2">📊</div>
          <div>暂无强度历史数据</div>
        </div>
      </div>
    )
  }

  return (
    <div className="border rounded-lg bg-card p-4">
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
