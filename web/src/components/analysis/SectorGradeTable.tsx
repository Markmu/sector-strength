/**
 * 板块等级表格组件
 *
 * 展示按强度等级分组的板块数据
 */

'use client'

import { useState, useCallback } from 'react'
import {
  ChevronDownIcon,
  ChevronRightIcon,
  FireIcon,
  BoltIcon,
  StarIcon,
  ChartBarIcon,
  CheckIcon,
  MinusIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon,
  BuildingOfficeIcon,
  LightBulbIcon,
} from '@heroicons/react/24/outline'
import type { GradeSectorStats, SectorTableItem, SectorType, SectorDistributionResponse } from '@/types/gradeTable'

export interface SectorGradeTableProps {
  data: GradeSectorStats[]
  sectorType: SectorType | null
  loading?: boolean
  onSectorClick?: (sector: SectorTableItem) => void
  distributionData?: SectorDistributionResponse | null
}

// 等级配置 - 统一的图标和简洁色彩
const GRADE_CONFIG: Record<string, {
  label: string
  description: string
  icon: React.ComponentType<{ className?: string }>
}> = {
  'S+': {
    label: 'S+',
    description: '90-100 分',
    icon: FireIcon,
  },
  'S': {
    label: 'S',
    description: '80-89 分',
    icon: BoltIcon,
  },
  'A+': {
    label: 'A+',
    description: '70-79 分',
    icon: StarIcon,
  },
  'A': {
    label: 'A',
    description: '60-69 分',
    icon: ChartBarIcon,
  },
  'B+': {
    label: 'B+',
    description: '50-59 分',
    icon: CheckIcon,
  },
  'B': {
    label: 'B',
    description: '40-49 分',
    icon: MinusIcon,
  },
  'C': {
    label: 'C',
    description: '30-39 分',
    icon: ArrowTrendingDownIcon,
  },
  'D': {
    label: 'D',
    description: '0-29 分',
    icon: ExclamationTriangleIcon,
  },
}

export function SectorGradeTable({
  data,
  loading = false,
  onSectorClick,
}: SectorGradeTableProps) {
  const [expandedGrades, setExpandedGrades] = useState<Set<string>>(new Set())

  const toggleGrade = useCallback((grade: string) => {
    setExpandedGrades((prev) => {
      const next = new Set(prev)
      if (next.has(grade)) {
        next.delete(grade)
      } else {
        next.add(grade)
      }
      return next
    })
  }, [])

  const expandAll = useCallback(() => {
    setExpandedGrades(new Set(data.map((g) => g.grade)))
  }, [data])

  const collapseAll = useCallback(() => {
    setExpandedGrades(new Set())
  }, [])

  const handleSectorClick = useCallback((sector: SectorTableItem) => {
    if (onSectorClick) {
      onSectorClick(sector)
    }
  }, [onSectorClick])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="relative w-10 h-10 mx-auto mb-4">
            <div className="absolute inset-0 rounded-full border-2 border-[#e9ecef]" />
            <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-cyan-500 animate-spin" />
          </div>
          <p className="text-[#6c757d] text-sm font-medium">加载数据中...</p>
        </div>
      </div>
    )
  }

  if (!data.length) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center bg-white rounded-xl border border-[#e9ecef] p-12">
          <div className="text-6xl mb-4 opacity-50">📊</div>
          <p className="text-[#1a1a2e] text-xl font-semibold mb-2">暂无数据</p>
          <p className="text-[#6c757d]">请尝试调整筛选条件</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 控制按钮 */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-[#1a1a2e]">板块等级分布</h2>
        <div className="flex gap-3">
          <button
            onClick={expandAll}
            className="px-5 py-2.5 bg-white hover:bg-[#f8f9fb] text-[#1a1a2e] text-sm font-semibold rounded-lg border border-[#dee2e6] transition-all duration-200"
          >
            展开全部
          </button>
          <button
            onClick={collapseAll}
            className="px-5 py-2.5 bg-white hover:bg-[#f8f9fb] text-[#1a1a2e] text-sm font-semibold rounded-lg border border-[#dee2e6] transition-all duration-200"
          >
            折叠全部
          </button>
        </div>
      </div>

      {/* 等级卡片 */}
      <div className="space-y-3">
        {data.map((gradeStat) => {
          const isExpanded = expandedGrades.has(gradeStat.grade)
          const config = GRADE_CONFIG[gradeStat.grade] || GRADE_CONFIG['D']

          return (
            <div
              key={gradeStat.grade}
              className={`bg-white rounded-xl border overflow-hidden transition-all duration-200 shadow-sm ${
                isExpanded ? 'border-[#dee2e6] shadow-md' : 'border-[#e9ecef] hover:border-[#dee2e6]'
              }`}
            >
              {/* 等级头部 */}
              <button
                onClick={() => toggleGrade(gradeStat.grade)}
                className={`w-full px-6 py-4 flex items-center justify-between transition-colors duration-200 ${
                  isExpanded ? 'bg-[#f8f9fb]' : 'hover:bg-[#f8f9fb]'
                }`}
              >
                <div className="flex items-center gap-4">
                  {/* 展开/折叠图标 */}
                  <div className={`transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}>
                    {isExpanded ? (
                      <ChevronDownIcon className="w-5 h-5 text-[#6c757d]" />
                    ) : (
                      <ChevronRightIcon className="w-5 h-5 text-[#6c757d]" />
                    )}
                  </div>

                  {/* 等级标签 */}
                  <div className="flex items-center gap-3">
                    <config.icon className="w-6 h-6 text-[#1a1a2e]" />
                    <div className="flex flex-col items-start">
                      <span className="text-xl font-bold text-[#1a1a2e]">
                        {config.label}
                      </span>
                      <span className="text-xs text-[#6c757d]">{config.description}</span>
                    </div>
                  </div>
                </div>

                {/* 统计数字 */}
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-3 text-sm">
                    <div className="px-3 py-1.5 bg-[#f1f3f5] rounded-lg border border-[#e9ecef]">
                      <BuildingOfficeIcon className="w-4 h-4 text-[#6c757d] mr-1 inline" />
                      <span className="font-semibold text-[#1a1a2e]">{gradeStat.industry_count}</span>
                    </div>
                    <div className="px-3 py-1.5 bg-[#f1f3f5] rounded-lg border border-[#e9ecef]">
                      <LightBulbIcon className="w-4 h-4 text-[#6c757d] mr-1 inline" />
                      <span className="font-semibold text-[#1a1a2e]">{gradeStat.concept_count}</span>
                    </div>
                    <div className="px-4 py-1.5 bg-[#1a1a2e] rounded-lg font-bold text-white shadow-sm">
                      总计: {gradeStat.total_count}
                    </div>
                  </div>
                </div>
              </button>

              {/* 板块列表 */}
              {isExpanded && gradeStat.sectors.length > 0 && (
                <div className="border-t border-[#e9ecef]">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-[#f8f9fb]">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-[#6c757d] uppercase tracking-wider">排名</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-[#6c757d] uppercase tracking-wider">代码</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-[#6c757d] uppercase tracking-wider">名称</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-[#6c757d] uppercase tracking-wider">类型</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-[#6c757d] uppercase tracking-wider">综合得分</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-[#6c757d] uppercase tracking-wider">短期</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-[#6c757d] uppercase tracking-wider">中期</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-[#6c757d] uppercase tracking-wider">长期</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-[#6c757d] uppercase tracking-wider">强势股占比</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#f1f3f5]">
                        {gradeStat.sectors.map((sector) => (
                          <tr
                            key={sector.id}
                            onClick={() => handleSectorClick(sector)}
                            className="hover:bg-[#f8f9fb]/80 cursor-pointer transition-colors duration-150"
                          >
                            <td className="px-4 py-3 text-sm text-[#adb5bd]">
                              {sector.rank ?? '-'}
                            </td>
                            <td className="px-4 py-3 text-sm font-mono font-semibold text-cyan-600">
                              {sector.code}
                            </td>
                            <td className="px-4 py-3 text-sm font-semibold text-[#1a1a2e]">
                              {sector.name}
                            </td>
                            <td className="px-4 py-3">
                              <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold ${
                                sector.sector_type === 'industry'
                                  ? 'bg-[#f1f3f5] text-[#1a1a2e] border border-[#dee2e6]'
                                  : 'bg-[#f1f3f5] text-[#1a1a2e] border border-[#dee2e6]'
                              }`}>
                                {sector.sector_type === 'industry' ? (
                                  <>
                                    <BuildingOfficeIcon className="w-3.5 h-3.5 mr-1" />
                                    行业
                                  </>
                                ) : (
                                  <>
                                    <LightBulbIcon className="w-3.5 h-3.5 mr-1" />
                                    概念
                                  </>
                                )}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right text-sm font-bold text-[#1a1a2e]">
                              {sector.score !== null ? sector.score.toFixed(1) : '-'}
                            </td>
                            <td className="px-4 py-3 text-right text-sm text-[#6c757d]">
                              {sector.short_term_score?.toFixed(1) ?? '-'}
                            </td>
                            <td className="px-4 py-3 text-right text-sm text-[#6c757d]">
                              {sector.medium_term_score?.toFixed(1) ?? '-'}
                            </td>
                            <td className="px-4 py-3 text-right text-sm text-[#6c757d]">
                              {sector.long_term_score?.toFixed(1) ?? '-'}
                            </td>
                            <td className="px-4 py-3 text-right text-sm">
                              <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold ${
                                (sector.strong_stock_ratio ?? 0) > 0.5
                                  ? 'bg-emerald-50 text-emerald-600 border border-emerald-200'
                                  : 'bg-[#f1f3f5] text-[#6c757d] border border-[#e9ecef]'
                              }`}>
                                {sector.strong_stock_ratio !== null
                                  ? `${(sector.strong_stock_ratio * 100).toFixed(1)}%`
                                  : '-'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {isExpanded && gradeStat.sectors.length === 0 && (
                <div className="border-t border-[#e9ecef] px-6 py-12 text-center">
                  <div className="text-4xl mb-2 opacity-50">📭</div>
                  <p className="text-[#6c757d]">该等级暂无板块数据</p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
