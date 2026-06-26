'use client'

/**
 * 行业分布水平条形图（plan-02，AC-04）
 *
 * 主指标 = 扎堆股数量占比。
 * 复用 shareholder-analysis/IndustryDistribution.tsx 的 ECharts + 双轨标签范式：
 * - ECharts 动态导入（ssr: false）
 * - canvas 旁渲染可点击 DOM button（兼容 spec getByTestId 点击，规避 canvas 点击不稳定）
 *
 * data-testid 约定（spec 选择器依赖）：
 * - 容器：crowd-industry-distribution
 * - 行业标签：crowd-industry-bar-{industry}
 */
import React, { useMemo } from 'react'
import dynamic from 'next/dynamic'
import { BarChart3Icon } from 'lucide-react'
import type { CrowdIndustryItem } from '@/lib/api'

// 动态导入 ECharts（禁用 SSR，参照 shareholder-analysis/IndustryDistribution.tsx:22-26）
const ReactECharts = dynamic(
  () => import('echarts-for-react').then((mod) => mod.default),
  {
    ssr: false,
    loading: () => (
      <div className="h-64 flex items-center justify-center text-muted-foreground text-sm">
        加载图表中...
      </div>
    ),
  }
)

// 仅渲染 Top N（后端 distribution 返回全量，前端截断展示；长尾行业不撑爆图表）
const TOP_N = 20

export interface CrowdIndustryDistributionProps {
  distribution: CrowdIndustryItem[]
  isLoading?: boolean
  /** 板块维度标签（随 sector_type 切换，用于空状态/说明文案） */
  sectorTypeLabel?: string
  /**
   * 行业点击回调（首版仅作可视化交互入口预留，不联动排行榜筛选）。
   * 联动筛选是 PRD §3.3 后续迭代项，不在 plan-02 范围。
   */
  onIndustryClick?: (industry: string) => void
}

export default function CrowdIndustryDistribution({
  distribution,
  isLoading,
  sectorTypeLabel = '行业',
  onIndustryClick,
}: CrowdIndustryDistributionProps) {
  // 按扎堆股数量（stockCount）降序，占比次降序；截 Top N
  const sorted = useMemo(
    () =>
      [...distribution].sort(
        (a, b) => b.stockCount - a.stockCount || b.percentage - a.percentage
      ),
    [distribution]
  )
  const displayed = useMemo(() => sorted.slice(0, TOP_N), [sorted])

  // ECharts option：水平条形图，主指标 stockCount，label 显示 percentage%
  // 参照 shareholder-analysis/IndustryDistribution.tsx:54-100 的 yAxis category + series bar 范式
  const option = useMemo(() => {
    if (displayed.length === 0) return null
    // ECharts 自下而上展示，故 categories 反序使最大值在顶部
    const cats = displayed.map((d) => d.industry).reverse()
    const values = displayed.map((d) => d.stockCount).reverse()
    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: Array<{ dataIndex?: number }>) => {
          const idx = params[0]?.dataIndex
          if (idx === undefined) return ''
          const item = displayed[displayed.length - 1 - idx]
          if (!item) return ''
          return `<div>${item.industry}</div>
            <div>扎堆股数：${item.stockCount}</div>
            <div>占比：${item.percentage.toFixed(1)}%</div>`
        },
      },
      grid: { left: '15%', right: '8%', top: 10, bottom: 20, containLabel: true },
      xAxis: {
        type: 'value',
        axisLabel: { formatter: '{value}' },
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
          // label 显示占比%（主指标是占比，而非绝对数量）
          label: {
            show: true,
            position: 'right',
            formatter: (p: { dataIndex?: number }) => {
              const item = displayed[displayed.length - 1 - (p.dataIndex ?? 0)]
              return item ? `${item.percentage.toFixed(1)}%` : ''
            },
          },
        },
      ],
    }
  }, [displayed])

  // 空状态（distribution 完全为空）
  if (!isLoading && sorted.length === 0) {
    return (
      <div
        data-testid="crowd-industry-distribution"
        className="flex flex-col items-center justify-center py-10 text-muted-foreground"
      >
        <BarChart3Icon className="w-10 h-10 mb-2 opacity-50" />
        <p className="text-sm">暂无{sectorTypeLabel}分布数据</p>
      </div>
    )
  }

  return (
    <div data-testid="crowd-industry-distribution" className="space-y-3">
      {isLoading && (
        <div className="h-64 flex items-center justify-center text-muted-foreground text-sm">
          加载图表中...
        </div>
      )}
      {!isLoading && option && (
        <>
          <ReactECharts
            option={option}
            style={{
              height: `${Math.max(200, displayed.length * 36 + 40)}px`,
              width: '100%',
            }}
            opts={{ renderer: 'canvas' }}
          />
          {/* 可点击的行业标签列表：兼容 spec getByTestId 点击（参照 IndustryDistribution.tsx:129-150） */}
          <div className="flex flex-wrap gap-2">
            {displayed.map((d) => (
              <button
                key={d.industry}
                type="button"
                data-testid={`crowd-industry-bar-${d.industry}`}
                onClick={() => onIndustryClick?.(d.industry)}
                className="px-2.5 py-1 text-xs rounded-full border border-border bg-card text-foreground hover:border-muted-foreground transition-colors"
              >
                {d.industry}（{d.stockCount}，{d.percentage.toFixed(1)}%）
              </button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            仅展示扎堆股数前 {TOP_N} {sectorTypeLabel}（按数量占比）。
          </p>
        </>
      )}
    </div>
  )
}
