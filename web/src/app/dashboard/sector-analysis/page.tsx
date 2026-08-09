/**
 * 板块分析列表页面
 *
 * 显示所有可用的板块，支持分页、类型筛选和分数区间筛选
 */

'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { DashboardLayout, DashboardHeader } from '@/components/dashboard'
import { Disclaimer } from '@/components/ui/Disclaimer'
import { sectorsApi } from '@/lib/api'
import type { Sector } from '@/types'
import { SECTOR_TYPES, SECTOR_TYPE_DISPLAY, SECTOR_TYPE_LABELS, SW_LEVEL_OPTIONS, SW_LEVEL_LABELS, SW_SECTOR_TYPE, type SectorType, type SwLevel } from '@/types/sectorTypes'
import {
  LineChartIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  FunnelIcon,
} from 'lucide-react'

// 分页配置
const PAGE_SIZE = 20

// 板块类型选项
type SectorTypeFilter = 'all' | SectorType

export default function SectorAnalysisListPage() {
  const router = useRouter()

  // 数据状态
  const [sectors, setSectors] = useState<Sector[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [totalCount, setTotalCount] = useState(0)

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1)

  // 筛选状态（实际用于API请求的值）
  const [sectorTypeFilter, setSectorTypeFilter] = useState<SectorTypeFilter>('industry')
  // 申万行业层级筛选（仅 sectorTypeFilter === 'sw_industry' 时生效）
  const [swLevel, setSwLevel] = useState<'all' | SwLevel>('all')
  const [minScore, setMinScore] = useState<number>(0)
  const [maxScore, setMaxScore] = useState<number>(100)

  // 临时状态（用于滑块显示，失焦后才更新实际值）
  const [tempMinScore, setTempMinScore] = useState<number>(0)
  const [tempMaxScore, setTempMaxScore] = useState<number>(100)

  // 预设范围选项
  const presetRanges = [
    { label: '全部', min: 0, max: 100 },
    { label: '低分 0-30', min: 0, max: 30 },
    { label: '中低 30-50', min: 30, max: 50 },
    { label: '中高 50-70', min: 50, max: 70 },
    { label: '高分 70-80', min: 70, max: 80 },
    { label: '高分 80-90', min: 80, max: 90 },
    { label: '高分 90-100', min: 90, max: 100 },
    { label: '自定义', min: -1, max: -1 }, // -1 表示自定义模式
  ]

  // 判断当前是否是自定义模式
  const isCustomRange = !presetRanges.some(
    range => range.min === minScore && range.max === maxScore && range.min !== -1
  )

  // 用于记录是否已经挂载
  const isMounted = useRef(false)

  // 初始化临时值
  useEffect(() => {
    if (!isMounted.current) {
      setTempMinScore(minScore)
      setTempMaxScore(maxScore)
      isMounted.current = true
    }
  }, [minScore, maxScore])

  // 加载板块数据（带分页和筛选）
  useEffect(() => {
    async function fetchSectors() {
      try {
        setLoading(true)
        setError(null)

        console.log(`Fetching sectors: page=${currentPage}, type=${sectorTypeFilter}, score=[${minScore}, ${maxScore}]`)

        const response = await sectorsApi.getSectors({
          page: currentPage,
          page_size: PAGE_SIZE,
          sector_type: sectorTypeFilter === 'all' ? undefined : sectorTypeFilter,
          level: sectorTypeFilter === SW_SECTOR_TYPE && swLevel !== 'all' ? swLevel : undefined,
          min_strength_score: minScore,
          max_strength_score: maxScore,
        })

        // API 响应格式: { data: { success: true, data: { items: [...], total: 527 } } }
        const responseData = (response.data as any).data

        if (responseData && responseData.items) {
          const items = responseData.items as Sector[]

          console.log(`Received ${items.length} items from API`)

          setSectors(items)
          setTotalCount(responseData.total || 0)
        } else {
          console.error('Unexpected response format:', response)
          setError('数据格式错误')
        }
      } catch (err) {
        console.error('Failed to fetch sectors:', err)
        setError(`加载板块列表失败: ${err instanceof Error ? err.message : '未知错误'}`)
      } finally {
        setLoading(false)
      }
    }

    fetchSectors()
  }, [currentPage, sectorTypeFilter, swLevel, minScore, maxScore])

  // 计算总页数
  const totalPages = Math.ceil(totalCount / PAGE_SIZE)

  const handleSectorClick = (sectorId: string | undefined) => {
    if (sectorId) {
      router.push(`/dashboard/sector-analysis/${sectorId}`)
    }
  }

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage)
      // 滚动到顶部
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  const handleTypeFilterChange = (newType: SectorTypeFilter) => {
    setSectorTypeFilter(newType)
    // 切换类型时重置申万层级筛选
    setSwLevel(newType === SW_SECTOR_TYPE ? 'L1' : 'all')
    setCurrentPage(1) // 重置到第一页
  }

  const handleSwLevelChange = (newLevel: 'all' | SwLevel) => {
    setSwLevel(newLevel)
    setCurrentPage(1) // 重置到第一页
  }

  // 处理最小值变化
  const handleMinScoreChange = (value: number) => {
    // 确保不超过最大值
    const clampedValue = Math.min(value, tempMaxScore)
    setTempMinScore(clampedValue)
  }

  // 处理最大值变化
  const handleMaxScoreChange = (value: number) => {
    // 确保不小于最小值
    const clampedValue = Math.max(value, tempMinScore)
    setTempMaxScore(clampedValue)
  }

  // 处理最小值失焦
  const handleMinScoreBlur = () => {
    if (tempMinScore !== minScore) {
      setMinScore(tempMinScore)
      setTempMinScore(tempMinScore) // 同步临时值
      setCurrentPage(1) // 重置到第一页
    }
  }

  // 处理最大值失焦
  const handleMaxScoreBlur = () => {
    if (tempMaxScore !== maxScore) {
      setMaxScore(tempMaxScore)
      setTempMaxScore(tempMaxScore) // 同步临时值
      setCurrentPage(1) // 重置到第一页
    }
  }

  // 处理预设范围点击
  const handlePresetRangeClick = (min: number, max: number) => {
    if (min === -1 || max === -1) {
      // 自定义模式，不改变当前值
      return
    }
    setMinScore(min)
    setMaxScore(max)
    setTempMinScore(min)
    setTempMaxScore(max)
    setCurrentPage(1) // 重置到第一页
  }

  // 获取板块类型显示名称
  const getTypeDisplayName = (type: string) => {
    return SECTOR_TYPE_LABELS[type as SectorType] || SECTOR_TYPE_DISPLAY[type as SectorType] || type
  }

  // 获取板块类型颜色
  const getTypeColor = (type: string) => {
    const baseStyles = 'px-2 py-0.5 text-xs font-medium rounded border'
    return type === 'industry'
      ? `${baseStyles} bg-primary-light text-primary border-primary/30`
      : `${baseStyles} bg-secondary text-muted-foreground border-border`
  }

  // 获取趋势图标
  const getTrendIcon = (trendDirection: number) => {
    if (trendDirection > 0) {
      return <TrendingUpIcon className="w-4 h-4 text-fall" />
    } else if (trendDirection < 0) {
      return <TrendingDownIcon className="w-4 h-4 text-rise" />
    }
    return null
  }

  if (loading) {
    return (
      <DashboardLayout>
        <DashboardHeader title="板块分析" subtitle="加载中..." />
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">加载板块列表...</p>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <DashboardHeader title="板块分析" subtitle="加载失败" />
        <div className="flex items-center justify-center h-96">
          <div className="text-center text-destructive">
            <p>{error}</p>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <DashboardHeader
        title="板块分析"
        subtitle={`共 ${totalCount} 个板块，当前显示第 ${currentPage} 页`}
      />

      <div className="space-y-6">
        {/* 说明信息 */}
        <div className="bg-primary-light rounded-lg border border-primary/30 p-4">
          <div className="flex items-start gap-3">
            <LineChartIcon className="w-6 h-6 text-primary flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-foreground mb-1">板块分析功能</h3>
              <p className="text-sm text-muted-foreground">
                点击任意板块查看其强度历史趋势和均线分析。图表支持时间范围调整、均线显示控制和交互式缩放。
              </p>
            </div>
          </div>
        </div>

        {/* 筛选控制面板 */}
        <div className="bg-card rounded-xl border border-border shadow-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <FunnelIcon className="w-5 h-5 text-muted-foreground" />
            <h3 className="text-lg font-semibold text-foreground">筛选条件</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* 板块类型筛选 */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                板块类型
              </label>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => handleTypeFilterChange('all')}
                  className={`px-4 py-2 text-sm font-medium rounded-lg border ${
                    sectorTypeFilter === 'all'
                      ? 'bg-primary text-primary-foreground border-primary z-10'
                      : 'bg-card text-foreground border-border hover:bg-secondary relative'
                  }`}
                >
                  全部
                </button>
                {SECTOR_TYPES.filter((t) => t !== 'region').map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => handleTypeFilterChange(t)}
                    className={`px-4 py-2 text-sm font-medium rounded-lg border ${
                      sectorTypeFilter === t
                        ? 'bg-primary text-primary-foreground border-primary z-10'
                        : 'bg-card text-foreground border-border hover:bg-secondary relative'
                    }`}
                  >
                    {SECTOR_TYPE_LABELS[t]}
                  </button>
                ))}
              </div>
            </div>

            {/* 申万行业层级筛选（仅选中申万时显示） */}
            {sectorTypeFilter === SW_SECTOR_TYPE && (
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  申万层级
                </label>
                <div className="flex flex-wrap gap-2">
                  {SW_LEVEL_OPTIONS.map((l) => (
                    <button
                      key={l.value}
                      type="button"
                      onClick={() => handleSwLevelChange(l.value)}
                      className={`px-4 py-2 text-sm font-medium rounded-lg border ${
                        swLevel === l.value
                          ? 'bg-primary text-primary-foreground border-primary z-10'
                          : 'bg-card text-foreground border-border hover:bg-secondary relative'
                      }`}
                    >
                      {SW_LEVEL_LABELS[l.value]}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* 分数区间筛选 */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-foreground mb-2">
                强度分数区间: {minScore} - {maxScore}
              </label>

              {/* 预设范围按钮 */}
              <div className="flex flex-wrap gap-2 mb-4">
                {presetRanges.map((range) => {
                  const isActive = range.min === minScore && range.max === maxScore && range.min !== -1
                  const isCustomButton = range.min === -1
                  const showAsActive = isCustomButton ? isCustomRange : isActive

                  return (
                    <button
                      key={range.label}
                      type="button"
                      onClick={() => handlePresetRangeClick(range.min, range.max)}
                      disabled={isCustomButton}
                      className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-all ${
                        showAsActive
                          ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                          : 'bg-card text-muted-foreground border-border hover:bg-secondary hover:border-border'
                      } ${isCustomButton ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
                    >
                      {range.label}
                      {isCustomButton && isCustomRange && '(当前)'}
                    </button>
                  )
                })}
              </div>

              {/* 滑块区域 */}
              <div className="bg-background rounded-lg p-4 border border-border">
                <div className="flex items-center gap-4">
                  <div className="flex-1">
                    <div className="flex justify-between items-center mb-2">
                      <label className="text-xs font-medium text-foreground">
                        最小值
                      </label>
                      <span className="text-xs font-bold text-primary bg-primary-light px-2 py-0.5 rounded">
                        {tempMinScore}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={tempMinScore}
                      onChange={(e) => handleMinScoreChange(Number(e.target.value))}
                      onBlur={handleMinScoreBlur}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                      style={{
                        background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${(tempMinScore / 100) * 100}%, #e5e7eb ${(tempMinScore / 100) * 100}%, #e5e7eb 100%)`
                      }}
                    />
                  </div>

                  <div className="flex items-center justify-center">
                    <span className="text-faint font-light">至</span>
                  </div>

                  <div className="flex-1">
                    <div className="flex justify-between items-center mb-2">
                      <label className="text-xs font-medium text-foreground">
                        最大值
                      </label>
                      <span className="text-xs font-bold text-primary bg-primary-light px-2 py-0.5 rounded">
                        {tempMaxScore}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={tempMaxScore}
                      onChange={(e) => handleMaxScoreChange(Number(e.target.value))}
                      onBlur={handleMaxScoreBlur}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                      style={{
                        background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${(tempMaxScore / 100) * 100}%, #e5e7eb ${(tempMaxScore / 100) * 100}%, #e5e7eb 100%)`
                      }}
                    />
                  </div>
                </div>

                {/* 视觉化范围条 */}
                <div className="mt-3 h-2 bg-gray-200 rounded-full relative overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all duration-200"
                    style={{
                      left: `${(minScore / 100) * 100}%`,
                      width: `${((maxScore - minScore) / 100) * 100}%`,
                      position: 'absolute'
                    }}
                  />
                </div>

                {/* 提示信息 */}
                {tempMinScore !== minScore || tempMaxScore !== maxScore ? (
                  <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    调整后松开滑块生效（当前: {tempMinScore}-{tempMaxScore}）
                  </p>
                ) : (
                  <p className="text-xs text-rise mt-2 flex items-center gap-1">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    已应用筛选: {minScore}-{maxScore}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* 筛选结果统计 */}
          <div className="mt-4 pt-4 border-t border-border">
            <p className="text-sm text-gray-600">
              当前页: <span className="font-semibold text-foreground">{sectors.length}</span> 个板块 | 总计: {totalCount} 个
            </p>
          </div>
        </div>

        {/* 板块列表 */}
        <div className="bg-card rounded-xl border border-border shadow-sm">
          <div className="px-6 py-4 border-b border-border">
            <h2 className="text-lg font-semibold text-foreground">
              板块列表
              {sectors.length > 0 && (
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  (第 {currentPage} / {totalPages} 页)
                </span>
              )}
            </h2>
          </div>

          {sectors.length > 0 ? (
            <>
              <div className="divide-y divide-border">
                {sectors.map((sector) => (
                  <button
                    key={sector.id}
                    onClick={() => handleSectorClick(sector.id)}
                    className="w-full px-6 py-4 flex items-center justify-between hover:bg-secondary transition-colors"
                  >
                    <div className="flex items-center gap-4 flex-1">
                      {/* 板块图标 */}
                      <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-semibold flex-shrink-0">
                        {sector.name.charAt(0)}
                      </div>

                      {/* 板块信息 */}
                      <div className="text-left flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <div className="font-semibold text-foreground">{sector.name}</div>
                          <span className={`px-2 py-0.5 text-xs font-medium rounded border ${getTypeColor(sector.type)}`}>
                            {getTypeDisplayName(sector.type)}
                          </span>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          代码: {sector.code}
                        </div>
                      </div>

                      {/* 强度分数和趋势 */}
                      <div className="flex items-center gap-4 flex-shrink-0">
                        <div className="text-right">
                          <div className="text-sm font-medium text-foreground">
                            强度: {(sector.strength_score ?? 0).toFixed(1)}
                          </div>
                          <div className="flex items-center justify-end gap-1">
                            {getTrendIcon(sector.trend_direction ?? 0)}
                          </div>
                        </div>
                        <div className="flex items-center gap-2 text-faint">
                          <span className="text-sm">查看分析</span>
                          <TrendingUpIcon className="w-4 h-4" />
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              {/* 分页控制 */}
              {totalPages > 1 && (
                <div className="px-6 py-4 border-t border-border flex items-center justify-between">
                  <div className="text-sm text-gray-600">
                    第 {currentPage} / {totalPages} 页，共 {totalCount} 条
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                      className="px-3 py-2 text-sm font-medium rounded-lg border border-border hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                    >
                      <ChevronLeftIcon className="w-4 h-4" />
                      上一页
                    </button>

                    <div className="flex items-center gap-1">
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        let pageNum
                        if (totalPages <= 5) {
                          pageNum = i + 1
                        } else if (currentPage <= 3) {
                          pageNum = i + 1
                        } else if (currentPage >= totalPages - 2) {
                          pageNum = totalPages - 4 + i
                        } else {
                          pageNum = currentPage - 2 + i
                        }

                        return (
                          <button
                            key={pageNum}
                            onClick={() => handlePageChange(pageNum)}
                            className={`min-w-[40px] px-3 py-2 text-sm font-medium rounded-lg border ${
                              currentPage === pageNum
                                ? 'bg-primary text-primary-foreground border-primary'
                                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                            }`}
                          >
                            {pageNum}
                          </button>
                        )
                      })}
                    </div>

                    <button
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                      className="px-3 py-2 text-sm font-medium rounded-lg border border-border hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                    >
                      下一页
                      <ChevronRightIcon className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="px-6 py-12 text-center text-muted-foreground">
              <LineChartIcon className="w-12 h-12 mx-auto mb-3 text-faint" />
              <p className="text-lg font-medium mb-2">未找到符合条件的板块</p>
              <p className="text-sm">请尝试调整筛选条件</p>
            </div>
          )}
        </div>

        {/* 使用提示 */}
        <div className="bg-amber-50 rounded-lg border border-amber-200 p-4 text-sm text-amber-800">
          <div className="font-semibold mb-2">💡 使用提示</div>
          <ul className="space-y-1 list-disc list-inside">
            <li>点击板块名称查看详细的历史趋势和均线分析</li>
            <li>使用筛选器按板块类型和强度分数进行筛选</li>
            <li>在分析页面可以调整时间范围（1周/1月/2月/3月/6月/1年）</li>
            <li>支持显示/隐藏不同的均线（MA5/10/20/30/60/90/120/240）</li>
          </ul>
        </div>

        {/* 免责声明 */}
        <Disclaimer showSeparator={true} />
      </div>
    </DashboardLayout>
  )
}
