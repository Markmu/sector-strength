/**
 * 板块强度散点图组件
 *
 * 使用 ECharts 散点图展示板块在多维强度空间中的分布
 */

'use client'

import { memo, useMemo } from 'react'
import dynamic from 'next/dynamic'
import { LoadingState } from '@/components/dashboard/LoadingState'
import { ErrorState } from '@/components/dashboard/ErrorState'
import type { ScatterPlotProps, ScatterDataPoint, AxisType } from '@/types/scatter'
import { AXIS_CONFIG } from '@/types/scatter'

// 动态导入 ECharts 组件（优化性能，禁用 SSR）
const ReactECharts = dynamic(
  () => import('echarts-for-react').then((mod) => mod.default),
  {
    ssr: false,
    loading: () => <LoadingState message="加载散点图..." />,
  },
)

function SectorScatterPlotComponent({
  xAxis = 'short',
  yAxis = 'medium',
  data,
  isLoading = false,
  isError = false,
  onSectorClick,
  className = '',
}: ScatterPlotProps) {
  // 转换为 ECharts 格式的数据
  const { industryData, conceptData, allPoints } = useMemo(() => {
    const industry: number[][] = []
    const concept: number[][] = []
    const all: ScatterDataPoint[] = []

    if (data) {
      data.industry.forEach((point) => {
        // [x, y, size, color_value, ...]
        industry.push([point.x, point.y, point.size, point.color_value])
        all.push(point)
      })

      data.concept.forEach((point) => {
        concept.push([point.x, point.y, point.size, point.color_value])
        all.push(point)
      })
    }

    return { industryData: industry, conceptData: concept, allPoints: all }
  }, [data])

  // 处理点击事件
  const handleChartClick = (params: any) => {
    if (!onSectorClick || !allPoints.length) return

    // 查找点击的数据点
    const point = allPoints.find((p) => p.symbol === params.data[4]) // data[4] 是 symbol
    if (point) {
      onSectorClick(point)
    }
  }

  // ECharts 散点图配置
  const option = useMemo(() => {
    const xConfig = AXIS_CONFIG[xAxis]
    const yConfig = AXIS_CONFIG[yAxis]

    return {
      // 全局配置
      animation: false, // 关闭动画以提升大数据量性能

      // 坐标轴
      xAxis: {
        name: xConfig.label,
        nameLocation: 'middle',
        nameGap: 30,
        min: 0,
        max: 100,
        axisLine: { lineStyle: { color: '#666' } },
        splitLine: { lineStyle: { color: '#eee', type: 'dashed' } },
      },
      yAxis: {
        name: yConfig.label,
        nameLocation: 'middle',
        nameGap: 40,
        min: 0,
        max: 100,
        axisLine: { lineStyle: { color: '#666' } },
        splitLine: { lineStyle: { color: '#eee', type: 'dashed' } },
      },

      // 颜色映射：基于长期强度
      visualMap: {
        min: 0,
        max: 100,
        inRange: { color: ['#ef4444', '#eab308', '#22c55e'] }, // 红-黄-绿
        text: ['强', '弱'],
        dimension: 3, // color_value 索引
        orient: 'horizontal',
        right: 0,
        bottom: 10,
        textStyle: { color: '#666' },
      },

      // 缩放和平移
      dataZoom: [
        { type: 'slider', xAxisIndex: 0, filterMode: 'none' },
        { type: 'slider', yAxisIndex: 0, filterMode: 'none' },
        { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
        { type: 'inside', yAxisIndex: 0, filterMode: 'none' },
      ],

      // 提示框
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          if (!allPoints.length) return params.name

          // 查找对应的数据点
          const point = allPoints.find((p) => p.symbol === params.data[4])
          if (!point) return params.name

          const { name, symbol, full_data, data_completeness } = point

          return `
            <div style="padding: 12px; min-width: 200px;">
              <div style="font-weight: bold; margin-bottom: 8px; font-size: 14px;">
                ${name}
              </div>
              <div style="font-size: 12px; color: #666; margin-bottom: 4px;">${symbol}</div>
              <div style="margin-top: 8px;">
                <div><strong>${xConfig.label}:</strong> ${point.x.toFixed(1)}</div>
                <div><strong>${yConfig.label}:</strong> ${point.y.toFixed(1)}</div>
                <div><strong>综合强度:</strong> ${full_data.score?.toFixed(1) ?? 'N/A'}</div>
                <div><strong>强势股占比:</strong> ${full_data.strong_stock_ratio != null ? (full_data.strong_stock_ratio * 100).toFixed(1) + '%' : 'N/A'}</div>
                <div><strong>强度等级:</strong> ${full_data.strength_grade ?? 'N/A'}</div>
              </div>
              ${data_completeness.completeness_percent < 100 ? `
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee; font-size: 11px; color: #f59e0b;">
                  ⚠️ 数据完整度: ${data_completeness.completeness_percent.toFixed(0)}%
                </div>
              ` : ''}
            </div>
          `
        },
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#ddd',
        borderWidth: 1,
        textStyle: { color: '#333' },
        extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.15); border-radius: 8px;',
      },

      // 图例
      legend: {
        data: ['行业板块', '概念板块'],
        top: 10,
        right: 10,
        textStyle: { color: '#666' },
      },

      // 两个系列：行业板块和概念板块
      series: [
        {
          name: '行业板块',
          type: 'scatter',
          symbol: 'circle',
          symbolSize: (data: number[]) => Math.max(data[2], 10), // 基于 size
          data: industryData,
          label: {
            show: false, // 数据点太多时不显示标签
          },
          itemStyle: {
            opacity: 0.8,
          },
          emphasis: {
            itemStyle: {
              opacity: 1,
              borderColor: '#fff',
              borderWidth: 2,
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.3)',
            },
          },
          markArea: {
            silent: true,
            itemStyle: { color: 'transparent' },
          },
        },
        {
          name: '概念板块',
          type: 'scatter',
          symbol: 'diamond',
          symbolSize: (data: number[]) => Math.max(data[2], 10), // 基于 size
          data: conceptData,
          label: {
            show: false,
          },
          itemStyle: {
            opacity: 0.8,
          },
          emphasis: {
            itemStyle: {
              opacity: 1,
              borderColor: '#fff',
              borderWidth: 2,
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.3)',
            },
          },
        },
      ],
    }
  }, [xAxis, yAxis, industryData, conceptData, allPoints])

  // 加载状态
  if (isLoading) {
    return <LoadingState message="加载散点图..." />
  }

  // 错误状态
  if (isError) {
    return <ErrorState message="加载散点图失败，请稍后重试" />
  }

  // 空数据状态
  if (!allPoints.length) {
    return (
      <div className="flex items-center justify-center" style={{ height: '500px' }}>
        <div className="text-center text-gray-500">
          <p className="text-lg mb-2">暂无散点图数据</p>
          <p className="text-sm">请尝试调整筛选条件</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`w-full ${className}`}>
      <ReactECharts
        option={option}
        style={{
          height: 'clamp(400px, 60vh, 700px)',
          width: '100%',
          minHeight: '400px',
        }}
        onEvents={{
          click: handleChartClick,
        }}
        opts={{ renderer: 'canvas' }}
      />
    </div>
  )
}

// 使用 React.memo 优化渲染性能
export const SectorScatterPlot = memo(SectorScatterPlotComponent)

SectorScatterPlot.displayName = 'SectorScatterPlot'
