'use client'

import { memo, useState } from 'react'
import dynamic from 'next/dynamic'
import { useMarketIndex } from '@/hooks/useMarketIndex'
import { LoadingState } from './LoadingState'
import { ErrorState } from './ErrorState'

// 动态导入 ECharts 组件（优化性能，禁用 SSR）
const ReactECharts = dynamic(
  () => import('echarts-for-react').then((mod) => mod.default),
  {
    ssr: false,
    loading: () => <LoadingState message="加载市场指数..." />,
  }
)

export const MarketIndexDisplay = memo(function MarketIndexDisplay() {
  const { index, stats, trend, isLoading, isError } = useMarketIndex()
  const [showDetail, setShowDetail] = useState(false)

  // 加载状态
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <LoadingState message="加载市场指数..." />
      </div>
    )
  }

  // 错误状态
  if (isError || !index || !stats) {
    return (
      <div className="flex items-center justify-center h-48">
        <ErrorState message="加载市场指数失败，请稍后重试" />
      </div>
    )
  }

  // 计算百分比
  const upPercent = stats.totalSectors > 0 ? ((stats.upSectors / stats.totalSectors) * 100).toFixed(0) : '0'
  const downPercent = stats.totalSectors > 0 ? ((stats.downSectors / stats.totalSectors) * 100).toFixed(0) : '0'
  const neutralPercent = stats.totalSectors > 0 ? ((stats.neutralSectors / stats.totalSectors) * 100).toFixed(0) : '0'

  // 变化百分比
  const changePercent = index.value > 0 ? ((index.change / index.value) * 100).toFixed(1) : '0.0'

  // ECharts Gauge 配置
  const gaugeOption = {
    series: [{
      type: 'gauge',
      min: 0,
      max: 100,
      splitNumber: 10,
      axisLine: {
        lineStyle: {
          width: 20,
          color: [
            [0.4, '#EF4444'],   // 0-40: 弱（红色）
            [0.7, '#FBBF24'],   // 40-70: 中（黄色）
            [1, '#10B981']      // 70-100: 强（绿色）
          ]
        }
      },
      pointer: {
        itemStyle: { color: '#333' }
      },
      detail: {
        valueAnimation: true,
        formatter: '{value}',
        fontSize: 28,
        fontWeight: 'bold',
        color: index.color,
        offsetCenter: [0, '80%'],
      },
      data: [{ value: index.value }],
      title: {
        show: false
      }
    }],
    tooltip: {
      formatter: () => `市场强度指数: ${index.value}`
    }
  }

  // 趋势迷你图配置
  const trendOption = {
    grid: {
      left: 0,
      right: 0,
      top: 0,
      bottom: 0,
    },
    xAxis: {
      type: 'category',
      show: false,
      data: trend.map(t => t.timestamp),
    },
    yAxis: {
      type: 'value',
      show: false,
      min: 0,
      max: 100,
    },
    series: [{
      type: 'line',
      data: trend.map(t => t.value),
      showSymbol: false,
      smooth: true,
      lineStyle: {
        color: index.color,
        width: 2,
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: `${index.color}40` },
            { offset: 1, color: `${index.color}05` },
          ],
        },
      },
    }],
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const point = trend[params[0].dataIndex]
        if (!point) return ''
        const date = new Date(point.timestamp)
        return `${date.toLocaleDateString('zh-CN')}<br/>指数: ${point.value.toFixed(2)}`
      },
    },
  }

  return (
    <div className="space-y-4">
      {/* 主指数显示 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 左侧：仪表盘 */}
        <div className="flex flex-col items-center justify-center p-6">
          <ReactECharts
            option={gaugeOption}
            style={{ height: '200px', width: '100%' }}
            opts={{ renderer: 'canvas' }}
          />
        </div>

        {/* 右侧：统计数据 */}
        <div className="flex flex-col justify-center space-y-4">
          {/* 变化指示 */}
          <div className="text-center">
            <div className="text-4xl font-bold" style={{ color: index.color }}>
              {index.value.toFixed(1)}
            </div>
            <div className="flex items-center justify-center mt-2">
              {index.change > 0 ? (
                <span className="text-green-600 text-sm flex items-center">
                  ↑ +{index.change.toFixed(2)} (+{changePercent}%)
                </span>
              ) : index.change < 0 ? (
                <span className="text-red-600 text-sm flex items-center">
                  ↓ {index.change.toFixed(2)} ({changePercent}%)
                </span>
              ) : (
                <span className="text-gray-500 text-sm">
                  → 0.00 (0.0%)
                </span>
              )}
              <span className="text-gray-500 text-sm ml-2">vs 上次刷新</span>
            </div>
          </div>

          {/* 板块统计 */}
          <div className="grid grid-cols-3 gap-2 text-center text-sm">
            <div className="bg-green-50 rounded-lg p-2">
              <div className="text-green-700 font-bold text-lg">{stats.upSectors}</div>
              <div className="text-green-600">上涨</div>
              <div className="text-gray-500 text-xs">{upPercent}%</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-2">
              <div className="text-gray-700 font-bold text-lg">{stats.neutralSectors}</div>
              <div className="text-gray-600">平盘</div>
              <div className="text-gray-500 text-xs">{neutralPercent}%</div>
            </div>
            <div className="bg-red-50 rounded-lg p-2">
              <div className="text-red-700 font-bold text-lg">{stats.downSectors}</div>
              <div className="text-red-600">下跌</div>
              <div className="text-gray-500 text-xs">{downPercent}%</div>
            </div>
          </div>

          <div className="text-center text-xs text-gray-500">
            总板块数: {stats.totalSectors}
          </div>
        </div>
      </div>

      {/* 趋势图 */}
      {trend.length > 0 && (
        <div className="border-t pt-4">
          <div className="text-sm text-gray-600 mb-2">24小时趋势</div>
          <ReactECharts
            option={trendOption}
            style={{ height: '80px', width: '100%' }}
            opts={{ renderer: 'canvas' }}
          />
        </div>
      )}

      {/* 详情按钮 */}
      <div className="text-center">
        <button
          onClick={() => setShowDetail(true)}
          className="text-sm text-blue-600 hover:text-blue-700 underline"
        >
          查看计算方法和详情
        </button>
      </div>

      {/* 详情弹窗（简化版本） */}
      {showDetail && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setShowDetail(false)}
        >
          <div
            className="bg-white rounded-lg p-6 max-w-md w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold mb-4">市场强度指数计算方法</h3>
            <div className="text-sm text-gray-700 space-y-3">
              <p>
                <strong>指数定义：</strong>
                市场强度指数反映所有板块的整体强弱状态，范围为 0-100。
              </p>
              <p>
                <strong>计算公式：</strong>
                <br />
                指数 = Σ(各板块强度得分) / 板块总数
                <br />
                <span className="text-xs text-gray-500">（简化版本，所有板块权重相同）</span>
              </p>
              <p>
                <strong>指数解读：</strong>
                <br />
                <span className="text-green-600">●</span> 70-100：市场强势<br />
                <span className="text-yellow-600">●</span> 40-70：市场中性<br />
                <span className="text-red-600">●</span> 0-40：市场弱势
              </p>
              <p>
                <strong>板块统计：</strong>
                根据各板块的趋势方向统计上涨、下跌、平盘板块数量。
              </p>
              <div className="text-xs text-gray-500 pt-2 border-t">
                更新时间: {new Date(index.timestamp).toLocaleString('zh-CN')}
              </div>
            </div>
            <button
              onClick={() => setShowDetail(false)}
              className="mt-4 w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
            >
              关闭
            </button>
          </div>
        </div>
      )}
    </div>
  )
})
