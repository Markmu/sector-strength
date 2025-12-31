/**
 * 散点图分析类型定义
 */

export type AxisType = 'short' | 'medium' | 'long' | 'composite'

export type SectorType = 'industry' | 'concept'

export interface DataCompleteness {
  has_strong_ratio: boolean
  has_long_term: boolean
  completeness_percent: number
}

export interface SectorFullData {
  score?: number
  short_term_score?: number
  medium_term_score?: number
  long_term_score?: number
  strong_stock_ratio?: number | null
  strength_grade?: string
}

export interface ScatterDataPoint {
  symbol: string
  name: string
  sector_type: SectorType
  x: number
  y: number
  size: number
  color_value: number
  data_completeness: DataCompleteness
  full_data: SectorFullData
}

export interface ScatterDataset {
  industry: ScatterDataPoint[]
  concept: ScatterDataPoint[]
}

export interface PaginationInfo {
  offset: number
  limit: number
}

export interface FiltersApplied {
  sector_type?: SectorType
  grade_range?: [string, string] | null
  axes: [AxisType, AxisType]
  pagination?: PaginationInfo
}

export interface SectorScatterResponse {
  scatter_data: ScatterDataset
  total_count: number
  returned_count: number
  filters_applied: FiltersApplied
  cache_status: 'hit' | 'miss'
}

export interface ScatterPlotProps {
  xAxis?: AxisType
  yAxis?: AxisType
  data?: ScatterDataset
  isLoading?: boolean
  isError?: boolean
  onSectorClick?: (point: ScatterDataPoint) => void
  className?: string
}

// 维度配置映射
export const AXIS_CONFIG: Record<AxisType, { field: keyof ScatterDataPoint['full_data']; label: string }> = {
  short: { field: 'short_term_score', label: '短期强度' },
  medium: { field: 'medium_term_score', label: '中期强度' },
  long: { field: 'long_term_score', label: '长期强度' },
  composite: { field: 'score', label: '综合强度' },
}

// 强度等级范围映射
export const GRADE_RANGE_MAP: Record<string, [number, number]> = {
  'S+': [90, 100],
  'S': [80, 89],
  'A+': [70, 79],
  'A': [60, 69],
  'B+': [50, 59],
  'B': [40, 49],
  'C': [30, 39],
  'D': [0, 29],
}
