'use client'

import { memo } from 'react'
import dynamic from 'next/dynamic'
import { useRouter } from 'next/navigation'
import { useSectorHeatmapData } from '@/hooks/useSectorHeatmapData'
import { LoadingState } from './LoadingState'
import { ErrorState } from './ErrorState'
import type { HeatmapSector } from '@/types'

// 动态导入 ECharts 组件（优化性能，禁用 SSR）
const ReactECharts = dynamic(
  () => import('echarts-for-react').then((mod) => mod.default),
  {
    ssr: false,
    loading: () => <LoadingState message="加载热力图..." />,
  }
)

interface SectorHeatmapProps {
  sectorType?: 'industry' | 'concept'
  className?: string
}

function SectorHeatmapComponent({ sectorType, className = '' }: SectorHeatmapProps) {
  const router = useRouter()
  const { sectors, timestamp, isLoading, isError } = useSectorHeatmapData({
    sectorType,
  })

  // 处理点击事件 - 跳转到板块详情页
  const handleChartClick = (params: any) => {
    const sector = sectors.find((s) => s.name === params.name)
    if (sector?.id) {
      router.push(`/sector/${sector.id}`)
    }
  }

  // 转换为 ECharts Treemap 格式
  const treemapData = sectors.map((sector: HeatmapSector) => ({
    name: sector.name,
    value: sector.value,
    itemStyle: {
      color: sector.color,
    },
    // 自定义数据用于点击事件
    sectorId: sector.id,
  }))

  // ECharts Treemap 配置
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const sector = sectors.find((s) => s.name === params.name)
        if (!sector) return params.name
        return `
          <div style="padding: 8px;">
            <div style="font-weight: bold; margin-bottom: 4px;">${params.name}</div>
            <div>强度得分: <span style="color: ${sector.color}; font-weight: bold;">${sector.value.toFixed(1)}</span></div>
            <div style="font-size: 12px; color: #666;">点击查看详情</div>
          </div>
        `
      },
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      borderColor: '#333',
      textStyle: {
        color: '#fff',
      },
    },
    series: [
      {
        type: 'treemap',
        data: treemapData,
        breadcrumb: { show: false },
        label: {
          show: true,
          formatter: (params: any) => {
            const sector = sectors.find((s) => s.name === params.name)
            return `${params.name}\n${sector?.value.toFixed(1) || 'N/A'}`
          },
          color: '#fff',
          fontSize: 14,
          fontWeight: 'bold',
        },
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 2,
          gapWidth: 2,
        },
        emphasis: {
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 3,
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.3)',
          },
          label: {
            show: true,
            fontSize: 16,
          },
        },
        // 动画配置
        animation: true,
        animationDuration: 300,
        animationEasing: 'cubicOut',
      },
    ],
  }

  // 加载状态
  if (isLoading) {
    return <LoadingState message="加载热力图..." />
  }

  // 错误状态
  if (isError) {
    return <ErrorState message="加载热力图失败，请稍后重试" />
  }

  // 空数据状态
  if (sectors.length === 0) {
    return (
      <div className="flex items-center justify-center h-96 text-gray-500">
        暂无热力图数据
      </div>
    )
  }

  return (
    <div className={`w-full ${className}`}>
      <ReactECharts
        option={option}
        style={{
          height: 'clamp(300px, 50vh, 600px)',  // 响应式高度：最小300px，最大600px，默认50vh
          width: '100%',
          minHeight: '300px',  // 移动端最小高度
        }}
        onEvents={{
          click: handleChartClick,
        }}
        opts={{ renderer: 'canvas' }}
      />
      {timestamp && (
        <div className="text-xs text-gray-500 text-center mt-2 px-2">
          最后更新: {new Date(timestamp).toLocaleString('zh-CN')}
        </div>
      )}
    </div>
  )
}

// 使用 React.memo 优化渲染性能
export const SectorHeatmap = memo(SectorHeatmapComponent)

SectorHeatmap.displayName = 'SectorHeatmap'
