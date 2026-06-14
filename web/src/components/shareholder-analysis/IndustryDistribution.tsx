'use client'

/**
 * 行业分布水平条形图（plan-04）
 *
 * 使用 ECharts bar（横向）展示行业占比，点击某个行业条目触发 onIndustryClick
 * （联动 HoldingsTable 的行业筛选）。
 *
 * 兼容 E2E spec TC-4.6 的点击断言：ECharts canvas 内 label 难以稳定点击，
 * 故在 canvas 旁渲染可点击的 DOM 行业标签列表（button + 文本），spec 的
 * `.or()` 退化路径会通过 getByText('银行') 命中。同时为每个标签加
 * data-testid="industry-bar-{industry}" 提升稳定性。
 *
 * 边界：空 distribution → 展示"暂无行业分布数据"
 */
import React, { useMemo } from 'react'
import dynamic from 'next/dynamic'
import { BarChart3Icon } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ShareholderIndustryItem } from '@/lib/api'

// 动态导入 ECharts（禁用 SSR，参照 SectorHeatmap.tsx 模式）
const ReactECharts = dynamic(() => import('echarts-for-react').then((mod) => mod.default), {
  ssr: false,
  loading: () => <div className="h-64 flex items-center justify-center text-muted-foreground text-sm">加载图表中...</div>,
})

// 图表/标签仅渲染持仓股票数 Top N（后端 distribution 返回全量真实行业，前端截断展示；
// 筛选栏下拉仍来自全量 distribution，长尾行业可选）。
const TOP_N = 10

export interface IndustryDistributionProps {
  distribution: ShareholderIndustryItem[]
  selectedIndustry?: string
  onIndustryClick?: (industry: string) => void
}

export default function IndustryDistribution({
  distribution,
  selectedIndustry,
  onIndustryClick,
}: IndustryDistributionProps) {
  // 按占比降序（全量，后端 distribution 返回全量真实行业）
  const sorted = useMemo(
    () => [...distribution].sort((a, b) => b.percentage - a.percentage),
    [distribution]
  )

  // 仅渲染持仓股票数 Top N，避免数百长尾行业撑爆图表/标签。
  // 筛选栏下拉仍来自全量 distribution（HoldingsDetail industryOptions），长尾可选。
  const displayed = useMemo(() => sorted.slice(0, TOP_N), [sorted])

  // ECharts option：水平条形图（yAxis 为类目轴）
  const option = useMemo(() => {
    // 空数据时返回 null option
    if (displayed.length === 0) return null
    // ECharts 自下而上展示，故 categories 反序使最大值在顶部
    const cats = displayed.map((d) => d.industry).reverse()
    const values = displayed.map((d) => d.percentage).reverse()
    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: Array<{ dataIndex?: number }>) => {
          const idx = params[0]?.dataIndex
          if (idx === undefined) return ''
          // 反序后下标对应原 displayed（反序后），需要还原
          const item = displayed[displayed.length - 1 - idx]
          if (!item) return ''
          return `<div>${item.industry}</div>
            <div>持仓股票数：${item.stockCount}</div>
            <div>占比：${item.percentage.toFixed(1)}%</div>`
        },
      },
      grid: { left: '15%', right: '8%', top: 10, bottom: 20, containLabel: true },
      xAxis: {
        type: 'value',
        max: 100,
        axisLabel: { formatter: '{value}%' },
      },
      yAxis: {
        type: 'category',
        data: cats,
        axisLabel: { fontSize: 12 },
      },
      series: [
        {
          type: 'bar',
          data: values,
          barMaxWidth: 24,
          itemStyle: { borderRadius: [0, 4, 4, 0] },
          label: {
            show: true,
            position: 'right',
            formatter: '{c}%',
          },
        },
      ],
    }
  }, [displayed])

  // 空状态：无行业数据
  if (sorted.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
        <BarChart3Icon className="w-10 h-10 mb-2 opacity-50" />
        <p className="text-sm">暂无行业分布数据</p>
      </div>
    )
  }

  const handleChartClick = (params: { dataIndex?: number }) => {
    if (!onIndustryClick) return
    // 反序后下标映射
    const idx = params.dataIndex
    if (idx === undefined) return
    const item = displayed[displayed.length - 1 - idx]
    if (item) onIndustryClick(item.industry)
  }

  return (
    <div data-testid="industry-distribution-chart" className="space-y-3">
      <ReactECharts
        option={option}
        style={{ height: `${Math.max(200, displayed.length * 36 + 40)}px`, width: '100%' }}
        onEvents={{ click: handleChartClick }}
        opts={{ renderer: 'canvas' }}
      />
      {/* 可点击的行业标签列表：兼容 spec getByText('银行') 点击 + 联动筛选 */}
      <div className="flex flex-wrap gap-2">
        {displayed.map((d) => {
          const isSelected = selectedIndustry === d.industry
          return (
            <button
              key={d.industry}
              type="button"
              data-testid={`industry-bar-${d.industry}`}
              onClick={() => onIndustryClick?.(d.industry)}
              className={cn(
                'px-2.5 py-1 text-xs rounded-full border transition-colors',
                isSelected
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border bg-card text-foreground hover:border-muted-foreground'
              )}
            >
              {d.industry}（{d.stockCount}，{d.percentage.toFixed(1)}%）
            </button>
          )
        })}
      </div>
      {/* Top N 说明：占比基于全部持仓（含长尾），故 Top N 占比之和可能 < 100% */}
      {displayed.length > 0 && (
        <p className="text-xs text-muted-foreground">
          仅展示持仓股票数前 {TOP_N} 行业；筛选栏下拉可查看全部行业。
        </p>
      )}
    </div>
  )
}
