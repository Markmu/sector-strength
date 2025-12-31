/**
 * 板块强度分析控制面板组件
 *
 * 提供筛选器和维度切换功能
 */

'use client'

import { memo } from 'react'
import { BuildingOfficeIcon, LightBulbIcon } from '@heroicons/react/24/outline'
import type { SectorType, AxisType } from '@/types/scatter'
import { AXIS_CONFIG, GRADE_RANGE_MAP } from '@/types/scatter'

export interface AnalysisControlsProps {
  xAxis: AxisType
  yAxis: AxisType
  sectorType: SectorType
  minGrade?: string | null
  maxGrade?: string | null
  onXAxisChange: (value: AxisType) => void
  onYAxisChange: (value: AxisType) => void
  onSectorTypeChange: (value: SectorType) => void
  onGradeRangeChange: (min: string | null, max: string | null) => void
  className?: string
}

// 板块类型选项（移除"全部"，只保留行业和概念）
const SECTOR_TYPE_OPTIONS = [
  { value: 'industry' as const, label: '行业板块', icon: BuildingOfficeIcon },
  { value: 'concept' as const, label: '概念板块', icon: LightBulbIcon },
]

// 维度选项
const AXIS_OPTIONS = [
  { value: 'short' as const, label: '短期强度' },
  { value: 'medium' as const, label: '中期强度' },
  { value: 'long' as const, label: '长期强度' },
  { value: 'composite' as const, label: '综合强度' },
]

// 强度等级选项（从高到低）
const GRADE_OPTIONS = [
  { value: 'S+', label: 'S+ (90-100)' },
  { value: 'S', label: 'S (80-89)' },
  { value: 'A+', label: 'A+ (70-79)' },
  { value: 'A', label: 'A (60-69)' },
  { value: 'B+', label: 'B+ (50-59)' },
  { value: 'B', label: 'B (40-49)' },
  { value: 'C', label: 'C (30-39)' },
  { value: 'D', label: 'D (0-29)' },
]

function AnalysisControlsComponent({
  xAxis,
  yAxis,
  sectorType,
  minGrade,
  maxGrade,
  onXAxisChange,
  onYAxisChange,
  onSectorTypeChange,
  onGradeRangeChange,
  className = '',
}: AnalysisControlsProps) {
  return (
    <div className={`bg-white rounded-xl border border-[#e9ecef] shadow-sm p-4 ${className}`}>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 板块类型筛选 */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-[#1a1a2e]">
            板块类型
          </label>
          <div className="flex flex-wrap gap-2">
            {SECTOR_TYPE_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => onSectorTypeChange(option.value)}
                className={`
                  inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                  ${sectorType === option.value
                    ? 'bg-cyan-500 text-white shadow-sm'
                    : 'bg-[#f1f3f5] text-[#1a1a2e] hover:bg-[#dee2e6]'
                  }
                `}
              >
                <option.icon className="w-4 h-4 mr-1" />
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {/* X轴维度 */}
        <div className="space-y-2">
          <label htmlFor="x-axis-select" className="block text-sm font-medium text-[#1a1a2e]">
            X轴维度
          </label>
          <select
            id="x-axis-select"
            value={xAxis}
            onChange={(e) => onXAxisChange(e.target.value as AxisType)}
            className="w-full px-3 py-2 border border-[#dee2e6] rounded-lg text-sm bg-white text-[#1a1a2e] focus:ring-2 focus:ring-cyan-100 focus:border-cyan-400"
          >
            {AXIS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Y轴维度 */}
        <div className="space-y-2">
          <label htmlFor="y-axis-select" className="block text-sm font-medium text-[#1a1a2e]">
            Y轴维度
          </label>
          <select
            id="y-axis-select"
            value={yAxis}
            onChange={(e) => onYAxisChange(e.target.value as AxisType)}
            className="w-full px-3 py-2 border border-[#dee2e6] rounded-lg text-sm bg-white text-[#1a1a2e] focus:ring-2 focus:ring-cyan-100 focus:border-cyan-400"
          >
            {AXIS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* 强度等级筛选 */}
        <div className="space-y-2">
          <fieldset className="space-y-2">
            <legend className="block text-sm font-medium text-[#1a1a2e] px-1">
              强度等级
            </legend>
            <div className="flex items-center gap-2">
              <select
                id="min-grade-select"
                value={minGrade ?? ''}
                onChange={(e) => onGradeRangeChange(
                  e.target.value || null,
                  maxGrade ?? null
                )}
                className="flex-1 px-2 py-1.5 border border-[#dee2e6] rounded-lg text-sm bg-white text-[#1a1a2e] focus:ring-2 focus:ring-cyan-100 focus:border-cyan-400"
              >
                <option value="">最低</option>
                {GRADE_OPTIONS.map((option) => (
                  <option key={`min-${option.value}`} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <span className="text-[#6c757d]">至</span>
              <select
                id="max-grade-select"
                value={maxGrade ?? ''}
                onChange={(e) => onGradeRangeChange(
                  minGrade ?? null,
                  e.target.value || null
                )}
                className="flex-1 px-2 py-1.5 border border-[#dee2e6] rounded-lg text-sm bg-white text-[#1a1a2e] focus:ring-2 focus:ring-cyan-100 focus:border-cyan-400"
              >
                <option value="">最高</option>
                {GRADE_OPTIONS.map((option) => (
                  <option key={`max-${option.value}`} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </fieldset>
        </div>
      </div>

      {/* 当前筛选状态提示 */}
      <div className="mt-4 pt-4 border-t border-[#e9ecef]">
        <div className="flex flex-wrap items-center gap-2 text-xs text-[#6c757d]">
          <span className="font-medium">当前筛选:</span>
          <span className="px-2 py-1 bg-[#f1f3f5] rounded">
            {SECTOR_TYPE_OPTIONS.find(o => o.value === sectorType)?.label}
          </span>
          <span>→</span>
          <span className="px-2 py-1 bg-[#f1f3f5] rounded">
            X: {AXIS_CONFIG[xAxis].label}
          </span>
          <span>vs</span>
          <span className="px-2 py-1 bg-[#f1f3f5] rounded">
            Y: {AXIS_CONFIG[yAxis].label}
          </span>
          {(minGrade || maxGrade) && (
            <>
              <span>→</span>
              <span className="px-2 py-1 bg-cyan-50 text-cyan-700 rounded">
                等级: {minGrade || '?'} - {maxGrade || '?'}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// 使用 React.memo 优化渲染性能
export const AnalysisControls = memo(AnalysisControlsComponent)

AnalysisControls.displayName = 'AnalysisControls'
