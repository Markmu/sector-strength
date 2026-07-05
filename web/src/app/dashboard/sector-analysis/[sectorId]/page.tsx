/**
 * 板块分析页面
 *
 * 显示板块的强度历史曲线和均线分析图表
 */

'use client'

import { useState, useCallback, useMemo, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'
import { DashboardLayout, DashboardHeader } from '@/components/dashboard'
import { Disclaimer } from '@/components/ui/Disclaimer'
import {
  TimeRangeSelector,
  MAToggleControls,
  SectorStrengthChart,
  SectorMAChart,
  LoadingState,
  ErrorState,
  SearchableSelect,
} from '@/components/dashboard'
import { useSectorStrengthHistory, useSectorMAHistory } from '@/hooks'
import { useChartState } from '@/stores/useChartState'
import { sectorsApi } from '@/lib/api'
import SectorStocksTable from '@/components/sector-analysis/SectorStocksTable'
import type { TimeRangeOption, MAPeriod, Sector } from '@/types'

interface PageParams {
  params: Promise<{
    sectorId: string
  }>
}

export default function SectorAnalysisPage({ params }: PageParams) {
  const router = useRouter()
  const [sectorId, setSectorId] = useState<number | null>(null)
  const [allSectors, setAllSectors] = useState<Sector[]>([])
  const [sectorsLoading, setSectorsLoading] = useState(true)

  // 从 Zustand store 获取图表状态
  const { timeRange, customStartDate, customEndDate, visibleMAs, setTimeRange, setCustomDateRange, toggleMA } = useChartState()

  // 解析 sectorId - 使用 useEffect 正确处理 Promise
  useEffect(() => {
    params.then((p) => setSectorId(parseInt(p.sectorId)))
  }, [params])

  // 加载所有板块列表
  useEffect(() => {
    async function fetchSectors() {
      try {
        setSectorsLoading(true)
        const response = await sectorsApi.getSectors({ page_size: 100 })
        if (response.data && 'items' in response.data) {
          setAllSectors(response.data.items as any)
        }
      } catch (err) {
        console.error('Failed to fetch sectors:', err)
      } finally {
        setSectorsLoading(false)
      }
    }

    fetchSectors()
  }, [])

  // 获取数据
  const {
    data: strengthData,
    isLoading: strengthLoading,
    isError: strengthError,
    mutate: strengthMutate,
  } = useSectorStrengthHistory({
    sectorId: sectorId!,
    timeRange,
    startDate: timeRange === 'custom' ? customStartDate ?? undefined : undefined,
    endDate: timeRange === 'custom' ? customEndDate ?? undefined : undefined,
  })

  const {
    data: maData,
    isLoading: maLoading,
    isError: maError,
    mutate: maMutate,
  } = useSectorMAHistory({
    sectorId: sectorId!,
    timeRange,
    startDate: timeRange === 'custom' ? customStartDate ?? undefined : undefined,
    endDate: timeRange === 'custom' ? customEndDate ?? undefined : undefined,
  })

  // 计算禁用的均线 (数据不足的情况)
  const disabledMAs = useMemo(() => {
    const disabled = new Set<MAPeriod>()

    // 不再根据数据长度禁用均线
    // 如果某个均线没有数据，图表会自动跳过显示

    return disabled
  }, [])

  // 处理时间范围变化
  const handleTimeRangeChange = useCallback(
    (newTimeRange: TimeRangeOption) => {
      setTimeRange(newTimeRange)
    },
    [setTimeRange]
  )

  // 处理均线显示切换
  const handleMAToggle = useCallback(
    (maPeriod: MAPeriod) => {
      toggleMA(maPeriod)
    },
    [toggleMA]
  )

  // 处理自定义日期变化
  const handleCustomDateChange = useCallback(
    (startDate: string, endDate: string) => {
      setCustomDateRange(startDate, endDate)
    },
    [setCustomDateRange]
  )

  // 处理板块选择变化
  const handleSectorChange = useCallback(
    (newSectorId: string) => {
      if (newSectorId && newSectorId !== String(sectorId)) {
        router.push(`/dashboard/sector-analysis/${newSectorId}`)
      }
    },
    [sectorId, router]
  )

  // 加载状态
  if (strengthLoading || maLoading) {
    return (
      <DashboardLayout>
        <DashboardHeader
          title="板块分析"
          subtitle="加载中..."
        />
        <div className="flex items-center justify-center h-96">
          <LoadingState message="加载板块分析数据..." />
        </div>
      </DashboardLayout>
    )
  }

  // 错误状态
  if (strengthError || maError || !sectorId) {
    const handleRetry = () => {
      // SWR mutate 会重新触发数据获取
      strengthMutate()
      maMutate()
    }

    return (
      <DashboardLayout>
        <DashboardHeader
          title="板块分析"
          subtitle="加载失败"
        />
        <div className="flex items-center justify-center h-96">
          <ErrorState
            message="加载板块分析数据失败，请稍后重试"
            onRetry={handleRetry}
          />
        </div>
      </DashboardLayout>
    )
  }

  const sectorName = strengthData?.sector_name || maData?.sector_name || '未知板块'

  return (
    <DashboardLayout>
      <DashboardHeader
        title={`${sectorName} - 板块分析`}
        subtitle="查看板块强度历史和均线分析"
      />

      <div className="space-y-6">
        {/* 小屏幕提示 */}
        <div className="lg:hidden bg-secondary border border-border rounded-lg p-4 text-sm text-muted-foreground">
          <div className="flex items-start gap-2">
            <span className="text-lg">💡</span>
            <div>
              <div className="font-semibold mb-1">显示建议</div>
              <div>为了获得最佳体验，建议使用桌面端或平板查看完整图表。小屏幕上图表可能显示不完整。</div>
            </div>
          </div>
        </div>

        {/* 控制面板 */}
        <div className="bg-card rounded-xl border border-border shadow-sm p-6 space-y-4">
          {/* 返回按钮和板块选择器 */}
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.back()}
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <ArrowLeftIcon className="w-5 h-5" />
                <span className="text-sm font-medium">返回</span>
              </button>

              {/* 面包屑导航 */}
              <div className="hidden sm:flex items-center gap-2 text-sm text-gray-600">
                <span className="hover:text-foreground cursor-pointer" onClick={() => router.push('/dashboard')}>
                  仪表盘
                </span>
                <span>/</span>
                <span className="hover:text-foreground cursor-pointer" onClick={() => router.push('/dashboard/sector-analysis')}>
                  板块分析
                </span>
                <span>/</span>
                <span className="text-foreground font-medium">{sectorName}</span>
              </div>
            </div>

            {/* 板块选择器 */}
            <div className="flex items-center gap-2 w-full lg:w-auto min-w-[300px]">
              <label htmlFor="sector-select" className="text-sm font-medium text-foreground whitespace-nowrap">
                选择板块:
              </label>
              <SearchableSelect
                options={allSectors.map(sector => ({
                  value: String(sector.id),
                  label: sector.name,
                  description: sector.code,
                }))}
                value={sectorId ? String(sectorId) : ''}
                onChange={(value) => handleSectorChange(value)}
                placeholder="选择板块查看分析"
                disabled={sectorsLoading}
                loading={sectorsLoading}
                searchPlaceholder="搜索板块名称或代码..."
                emptyMessage="未找到匹配的板块"
                onSearch={async (keyword: string) => {
                  try {
                    const response = await sectorsApi.searchSectors(keyword, { limit: 20 })
                    if (response.data?.data) {
                      return response.data.data.map((sector: any) => ({
                        value: String(sector.value),
                        label: sector.label,
                        description: sector.code,
                      }))
                    }
                    return []
                  } catch (error) {
                    console.error('搜索板块失败:', error)
                    return []
                  }
                }}
              />
            </div>
          </div>

          {/* 移动端面包屑 */}
          <div className="sm:hidden flex items-center gap-2 text-sm text-gray-600">
            <span className="hover:text-foreground cursor-pointer" onClick={() => router.push('/dashboard')}>
              仪表盘
            </span>
            <span>/</span>
            <span className="hover:text-foreground cursor-pointer" onClick={() => router.push('/dashboard/sector-analysis')}>
              板块分析
            </span>
            <span>/</span>
            <span className="text-foreground font-medium">{sectorName}</span>
          </div>

          {/* 时间范围选择器 */}
          <TimeRangeSelector
            value={timeRange}
            customStartDate={customStartDate}
            customEndDate={customEndDate}
            onChange={handleTimeRangeChange}
            onCustomDateChange={handleCustomDateChange}
          />

          {/* 均线显示控制 */}
          <MAToggleControls
            visibleMAs={visibleMAs}
            onToggle={handleMAToggle}
            disabledMAs={disabledMAs}
          />
        </div>

        {/* 图表区域 - 左右分栏布局 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 左侧: 强度历史曲线 */}
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-foreground">强度历史</h3>
            <SectorStrengthChart
              data={strengthData?.data ?? []}
              sectorName={sectorName}
              height="450px"
            />
          </div>

          {/* 右侧: 均线曲线 */}
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-foreground">均线分析</h3>
            <SectorMAChart
              data={maData?.data ?? []}
              sectorName={sectorName}
              visibleMAs={visibleMAs}
              height="450px"
            />
          </div>
        </div>

        {/* 板块成分股列表（AC-01~AC-06，独立加载与图表互不阻塞） */}
        <SectorStocksTable sectorId={sectorId} />

        {/* 数据说明 */}
        <div className="bg-primary-light rounded-lg border border-primary/30 p-4 text-sm text-muted-foreground">
          <div className="font-semibold mb-2">💡 图表说明</div>
          <ul className="space-y-1 list-disc list-inside">
            <li><strong>强度历史:</strong> 显示板块的强度得分变化趋势 (0-100分制)</li>
            <li><strong>均线分析:</strong> 显示多周期均线及价格走势</li>
            <li><strong>交互功能:</strong> 鼠标悬停查看详细数值,滚轮缩放Y轴,拖动滑块调整时间范围</li>
            <li><strong>切换板块:</strong> 使用右上角的下拉框快速切换到其他板块</li>
          </ul>
        </div>

        {/* 免责声明 */}
        <Disclaimer showSeparator={true} />
      </div>
    </DashboardLayout>
  )
}
