/**
 * 板块强度分析页面
 *
 * 按强度等级查看板块分布情况
 */

'use client'

import { useState, useCallback } from 'react'
import { useSWRConfig } from 'swr'
import { useRouter } from 'next/navigation'
import {
  BuildingOfficeIcon,
  LightBulbIcon,
  MapIcon,
  SparklesIcon,
  AdjustmentsHorizontalIcon,
  TagIcon,
} from '@heroicons/react/24/outline'
import { DashboardLayout, DashboardHeader } from '@/components/dashboard'
import { Disclaimer } from '@/components/ui/Disclaimer'
import { SectorGradeTable } from '@/components/analysis/SectorGradeTable'
import { useSectorGradeTable } from '@/hooks/useSectorGradeTable'
import { useSectorDistribution } from '@/hooks/useSectorDistribution'
import type { SectorTableItem } from '@/types/gradeTable'
import { SECTOR_TYPE_DISPLAY, SECTOR_TYPE_OPTIONS, type SectorType } from '@/types/sectorTypes'

// 板块类型选项（含图标和标签）
const TYPE_BUTTON_CONFIG: {
  value: SectorType
  label: string
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
}[] = [
  { value: 'industry', label: '行业板块', icon: BuildingOfficeIcon },
  { value: 'concept', label: '概念板块', icon: LightBulbIcon },
  { value: 'region', label: '地域板块', icon: MapIcon },
  { value: 'feature', label: '特色板块', icon: SparklesIcon },
  { value: 'style', label: '风格板块', icon: AdjustmentsHorizontalIcon },
  { value: 'theme', label: '主题板块', icon: TagIcon },
]

export default function SectorAnalysisPage() {
  const router = useRouter()
  const { mutate } = useSWRConfig()
  const [sectorType, setSectorType] = useState<SectorType | null>(null)

  const { data, isLoading } = useSectorGradeTable({
    sectorType,
    enabled: true,
  })

  const { data: distributionData } = useSectorDistribution()

  const handleRefresh = useCallback(() => {
    mutate(
      (key) => typeof key === 'string' && key.includes('/analysis/'),
      undefined,
      { revalidate: true }
    )
  }, [mutate])

  const handleSectorClick = useCallback((sector: SectorTableItem) => {
    // 跳转到板块分析页面
    router.push(`/dashboard/sector-analysis/${sector.id}`)
  }, [router])

  return (
    <DashboardLayout>
      <DashboardHeader
        title="板块强度分析"
        subtitle="按强度等级查看板块分布情况"
        onRefresh={handleRefresh}
      />

      <div className="space-y-6">
        {/* 统计卡片 */}
        {distributionData && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* 总计 */}
            <div className="bg-card rounded-xl border border-border shadow-sm p-5">
              <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-2">总计</div>
              <div className="text-3xl font-bold text-foreground tabular-nums">
                {distributionData.total_count}
              </div>
            </div>

            {/* 各类型统计 - 展示前两个类型 */}
            {Object.entries(distributionData.type_counts).slice(0, 2).map(([type, count]) => (
              <div key={type} className="bg-card rounded-xl border border-border shadow-sm p-5">
                <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-2">
                  {SECTOR_TYPE_DISPLAY[type as SectorType] || type}
                </div>
                <div className="text-3xl font-bold text-foreground tabular-nums">
                  {count}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 筛选控制 */}
        <div className="bg-card rounded-xl border border-border shadow-sm p-6">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            {/* 板块类型筛选 */}
            <div className="flex flex-wrap items-center gap-4">
              <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                板块类型
              </span>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setSectorType(null)}
                  className={`px-5 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 ${
                    sectorType === null
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground hover:bg-secondary border border-border'
                  }`}
                >
                  全部
                </button>
                {TYPE_BUTTON_CONFIG.map((cfg) => (
                  <button
                    key={cfg.value}
                    onClick={() => setSectorType(cfg.value)}
                    className={`px-5 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 ${
                      sectorType === cfg.value
                        ? 'bg-primary text-primary-foreground shadow-sm'
                        : 'text-muted-foreground hover:text-foreground hover:bg-secondary border border-border'
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <cfg.icon className="w-4 h-4" />
                      {cfg.label}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* 数据日期 */}
            {data && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">数据日期</span>
                <span className="px-3 py-1.5 bg-secondary rounded-lg font-mono font-semibold text-primary border border-border">
                  {data.date}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* 等级表格 */}
        <SectorGradeTable
          data={data?.stats ?? []}
          sectorType={sectorType}
          loading={isLoading}
          onSectorClick={handleSectorClick}
          distributionData={distributionData}
        />

        {/* 缓存状态 */}
        {data?.cache_status && (
          <div className="text-center">
            <span className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold ${
              data.cache_status === 'hit'
                ? 'bg-rise/10 text-rise border border-rise/30'
                : 'bg-secondary text-muted-foreground border border-border'
            }`}>
              <span className={`w-2 h-2 rounded-full ${
                data.cache_status === 'hit' ? 'bg-rise' : 'bg-muted-foreground'
              }`} />
              数据来源: {data.cache_status === 'hit' ? '缓存' : '实时查询'}
            </span>
          </div>
        )}

        {/* 免责声明 */}
        <Disclaimer showSeparator={true} />
      </div>
    </DashboardLayout>
  )
}
