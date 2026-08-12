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
            [0.4, '#4A8B6F'],   // 0-40: 弱（绿色）
            [0.7, '#FBBF24'],   // 40-70: 中（黄色）
            [1, '#C04E42']      // 70-100: 强（红色）
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
      formatter: (params: Array<{ dataIndex: number }>) => {
        const point = trend[params[0]?.dataIndex]
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
                <span className="text-rise text-sm flex items-center">
                  ↑ +{index.change.toFixed(2)} (+{changePercent}%)
                </span>
              ) : index.change < 0 ? (
                <span className="text-fall text-sm flex items-center">
                  ↓ {index.change.toFixed(2)} ({changePercent}%)
                </span>
              ) : (
                <span className="text-muted-foreground text-sm">
                  → 0.00 (0.0%)
                </span>
              )}
              <span className="text-muted-foreground text-sm ml-2">vs 上次刷新</span>
            </div>
          </div>

          {/* 板块统计 */}
          <div className="grid grid-cols-3 gap-2 text-center text-sm">
            <div className="bg-rise/10 rounded-lg p-2">
              <div className="text-rise font-bold text-lg">{stats.upSectors}</div>
              <div className="text-rise">上涨</div>
              <div className="text-muted-foreground text-xs">{upPercent}%</div>
            </div>
            <div className="bg-background rounded-lg p-2">
              <div className="text-foreground font-bold text-lg">{stats.neutralSectors}</div>
              <div className="text-muted-foreground">平盘</div>
              <div className="text-muted-foreground text-xs">{neutralPercent}%</div>
            </div>
            <div className="bg-fall/10 rounded-lg p-2">
              <div className="text-fall font-bold text-lg">{stats.downSectors}</div>
              <div className="text-fall">下跌</div>
              <div className="text-muted-foreground text-xs">{downPercent}%</div>
            </div>
          </div>

          <div className="text-center text-xs text-muted-foreground">
            总板块数: {stats.totalSectors}
          </div>
        </div>
      </div>

      {/* 趋势图 */}
      {trend.length > 0 && (
        <div className="border-t pt-4">
          <div className="text-sm text-muted-foreground mb-2">24小时趋势</div>
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
          className="text-sm text-primary hover:text-primary/80 underline"
        >
          查看计算方法和详情
        </button>
      </div>

      {/* 详情弹窗（简化版本） */}
      {showDetail && (
        <div
          className="fixed inset-0 bg-foreground/35 flex items-center justify-center z-50 p-4"
          onClick={() => setShowDetail(false)}
          data-testid="market-index-detail-backdrop"
        >
          <div
            className="bg-card rounded-lg p-6 max-w-md w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="market-index-detail-title"
          >
            <h3 id="market-index-detail-title" className="text-lg font-bold mb-4">市场强度指数计算方法</h3>
            <div className="text-sm text-foreground space-y-3">
              <p>
                <strong>指数定义：</strong>
                市场强度指数反映所有板块的整体强弱状态，范围为 0-100。
              </p>
              <p>
                <strong>计算公式：</strong>
                <br />
                指数 = Σ(各板块强度得分) / 板块总数
                <br />
                <span className="text-xs text-muted-foreground">（简化版本，所有板块权重相同）</span>
              </p>
              <p>
                <strong>指数解读：</strong>
                <br />
                <span className="font-semibold text-rise">70-100</span>：市场强势<br />
                <span className="font-semibold text-warning">40-70</span>：市场中性<br />
                <span className="font-semibold text-fall">0-40</span>：市场弱势
              </p>
              <p>
                <strong>板块统计：</strong>
                根据各板块的趋势方向统计上涨、下跌、平盘板块数量。
              </p>
              <div className="text-xs text-muted-foreground pt-2 border-t">
                更新时间: {new Date(index.timestamp).toLocaleString('zh-CN')}
              </div>
            </div>
            <button
              onClick={() => setShowDetail(false)}
              className="mt-4 w-full bg-primary text-on-signal py-2 rounded hover:bg-primary/90"
            >
              关闭
            </button>
          </div>
        </div>
      )}
    </div>
  )
})
