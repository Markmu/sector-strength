/**
 * 板块强度分析页面
 *
 * 按强度等级查看板块分布情况
 */

'use client'

import { useState, useCallback } from 'react'
import { useSWRConfig } from 'swr'
import { BuildingOfficeIcon, LightBulbIcon } from '@heroicons/react/24/outline'
import { DashboardLayout, DashboardHeader } from '@/components/dashboard'
import { SectorGradeTable } from '@/components/analysis/SectorGradeTable'
import { useSectorGradeTable } from '@/hooks/useSectorGradeTable'
import { useSectorDistribution } from '@/hooks/useSectorDistribution'
import type { SectorType, SectorTableItem } from '@/types/gradeTable'

export default function SectorAnalysisPage() {
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
    console.log('点击板块:', sector)
    alert(`点击了板块: ${sector.name} (${sector.code})\n\n详情页面待实现`)
  }, [])

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
            {/* 行业板块 */}
            <div className="bg-white rounded-xl border border-[#e9ecef] shadow-sm p-5">
              <div className="text-xs text-[#6c757d] font-medium uppercase tracking-wider mb-2">行业板块</div>
              <div className="text-3xl font-bold text-[#1a1a2e] tabular-nums">
                {distributionData.industry_count}
              </div>
            </div>

            {/* 概念板块 */}
            <div className="bg-white rounded-xl border border-[#e9ecef] shadow-sm p-5">
              <div className="text-xs text-[#6c757d] font-medium uppercase tracking-wider mb-2">概念板块</div>
              <div className="text-3xl font-bold text-[#1a1a2e] tabular-nums">
                {distributionData.concept_count}
              </div>
            </div>

            {/* 总计 */}
            <div className="bg-white rounded-xl border border-[#e9ecef] shadow-sm p-5">
              <div className="text-xs text-[#6c757d] font-medium uppercase tracking-wider mb-2">总计</div>
              <div className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-cyan-600 bg-clip-text text-transparent tabular-nums">
                {distributionData.total_count}
              </div>
            </div>
          </div>
        )}

        {/* 筛选控制 */}
        <div className="bg-white rounded-xl border border-[#e9ecef] shadow-sm p-6">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            {/* 板块类型筛选 */}
            <div className="flex flex-wrap items-center gap-4">
              <span className="text-sm font-semibold text-[#6c757d] uppercase tracking-wide">
                板块类型
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setSectorType(null)}
                  className={`px-5 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 ${
                    sectorType === null
                      ? 'bg-gradient-to-r from-cyan-400 to-cyan-500 text-white shadow-sm'
                      : 'text-[#6c757d] hover:text-[#1a1a2e] hover:bg-[#f1f3f5] border border-[#dee2e6]'
                  }`}
                >
                  全部
                </button>
                <button
                  onClick={() => setSectorType('industry')}
                  className={`px-5 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 ${
                    sectorType === 'industry'
                      ? 'bg-cyan-500 text-white shadow-sm'
                      : 'text-[#6c757d] hover:text-[#1a1a2e] hover:bg-[#f1f3f5] border border-[#dee2e6]'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <BuildingOfficeIcon className="w-4 h-4" />
                    行业板块
                  </span>
                </button>
                <button
                  onClick={() => setSectorType('concept')}
                  className={`px-5 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 ${
                    sectorType === 'concept'
                      ? 'bg-cyan-500 text-white shadow-sm'
                      : 'text-[#6c757d] hover:text-[#1a1a2e] hover:bg-[#f1f3f5] border border-[#dee2e6]'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <LightBulbIcon className="w-4 h-4" />
                    概念板块
                  </span>
                </button>
              </div>
            </div>

            {/* 数据日期 */}
            {data && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-[#6c757d]">数据日期</span>
                <span className="px-3 py-1.5 bg-[#f1f3f5] rounded-lg font-mono font-semibold text-cyan-600 border border-[#dee2e6]">
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
                ? 'bg-emerald-50 text-emerald-600 border border-emerald-200'
                : 'bg-[#f1f3f5] text-[#6c757d] border border-[#e9ecef]'
            }`}>
              <span className={`w-2 h-2 rounded-full ${
                data.cache_status === 'hit' ? 'bg-emerald-500' : 'bg-[#adb5bd]'
              }`} />
              数据来源: {data.cache_status === 'hit' ? '缓存' : '实时查询'}
            </span>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
