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
} from '@heroicons/react/24/outline'
import type { GradeSectorStats, SectorTableItem, SectorDistributionResponse } from '@/types/gradeTable'
import { SECTOR_TYPE_LABELS, SECTOR_TYPE_DISPLAY, type SectorType } from '@/types/sectorTypes'

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
            <div className="absolute inset-0 rounded-full border-2 border-border" />
            <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-primary animate-spin" />
          </div>
          <p className="text-muted-foreground text-sm font-medium">加载数据中...</p>
        </div>
      </div>
    )
  }

  if (!data.length) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center bg-card rounded-xl border border-border p-12">
          <div className="text-6xl mb-4 opacity-50">📊</div>
          <p className="text-foreground text-xl font-semibold mb-2">暂无数据</p>
          <p className="text-muted-foreground">请尝试调整筛选条件</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 控制按钮 */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-foreground">板块等级分布</h2>
        <div className="flex gap-3">
          <button
            onClick={expandAll}
            className="px-5 py-2.5 bg-card hover:bg-background text-foreground text-sm font-semibold rounded-lg border border-border transition-all duration-200"
          >
            展开全部
          </button>
          <button
            onClick={collapseAll}
            className="px-5 py-2.5 bg-card hover:bg-background text-foreground text-sm font-semibold rounded-lg border border-border transition-all duration-200"
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
              className={`bg-card rounded-xl border overflow-hidden transition-all duration-200 shadow-sm ${
                isExpanded ? 'border-border shadow-md' : 'border-border hover:border-border'
              }`}
            >
              {/* 等级头部 */}
              <button
                onClick={() => toggleGrade(gradeStat.grade)}
                className={`w-full px-6 py-4 flex items-center justify-between transition-colors duration-200 ${
                  isExpanded ? 'bg-background' : 'hover:bg-background'
                }`}
              >
                <div className="flex items-center gap-4">
                  {/* 展开/折叠图标 */}
                  <div className={`transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}>
                    {isExpanded ? (
                      <ChevronDownIcon className="w-5 h-5 text-muted-foreground" />
                    ) : (
                      <ChevronRightIcon className="w-5 h-5 text-muted-foreground" />
                    )}
                  </div>

                  {/* 等级标签 */}
                  <div className="flex items-center gap-3">
                    <config.icon className="w-6 h-6 text-foreground" />
                    <div className="flex flex-col items-start">
                      <span className="text-xl font-bold text-foreground">
                        {config.label}
                      </span>
                      <span className="text-xs text-muted-foreground">{config.description}</span>
                    </div>
                  </div>
                </div>

                {/* 统计数字 */}
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-3 text-sm">
                    {Object.entries(gradeStat.type_counts).map(([type, count]) => (
                      <div key={type} className="px-3 py-1.5 bg-secondary rounded-lg border border-border">
                        <span className="font-semibold text-foreground">{count}</span>
                        <span className="text-muted-foreground ml-1">{SECTOR_TYPE_LABELS[type as SectorType] || type}</span>
                      </div>
                    ))}
                    <div className="px-4 py-1.5 bg-secondary rounded-lg border border-border font-bold text-foreground">
                      总计: {gradeStat.total_count}
                    </div>
                  </div>
                </div>
              </button>

              {/* 板块列表 */}
              {isExpanded && gradeStat.sectors.length > 0 && (
                <div className="border-t border-border">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-background">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">排名</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">代码</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">名称</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">类型</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">综合得分</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">短期</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">中期</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">长期</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">强势股占比</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {gradeStat.sectors.map((sector) => (
                          <tr
                            key={sector.id}
                            onClick={() => handleSectorClick(sector)}
                            className="hover:bg-background/80 cursor-pointer transition-colors duration-150"
                          >
                            <td className="px-4 py-3 text-sm text-faint">
                              {sector.rank ?? '-'}
                            </td>
                            <td className="px-4 py-3 text-sm font-mono font-semibold text-primary">
                              {sector.code}
                            </td>
                            <td className="px-4 py-3 text-sm font-semibold text-foreground">
                              {sector.name}
                            </td>
                            <td className="px-4 py-3">
                              <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-secondary text-foreground border border-border">
                                {SECTOR_TYPE_LABELS[sector.sector_type as SectorType] || sector.sector_type}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right text-sm font-bold text-foreground">
                              {sector.score !== null ? sector.score.toFixed(1) : '-'}
                            </td>
                            <td className="px-4 py-3 text-right text-sm text-muted-foreground">
                              {sector.short_term_score?.toFixed(1) ?? '-'}
                            </td>
                            <td className="px-4 py-3 text-right text-sm text-muted-foreground">
                              {sector.medium_term_score?.toFixed(1) ?? '-'}
                            </td>
                            <td className="px-4 py-3 text-right text-sm text-muted-foreground">
                              {sector.long_term_score?.toFixed(1) ?? '-'}
                            </td>
                            <td className="px-4 py-3 text-right text-sm">
                              <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold ${
                                (sector.strong_stock_ratio ?? 0) > 0.5
                                  ? 'bg-rise/10 text-rise border border-rise/20'
                                  : 'bg-secondary text-muted-foreground border border-border'
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
                <div className="border-t border-border px-6 py-12 text-center">
                  <div className="text-4xl mb-2 opacity-50">📭</div>
                  <p className="text-muted-foreground">该等级暂无板块数据</p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
