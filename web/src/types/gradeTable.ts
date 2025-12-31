/**
 * 板块等级表格类型定义
 */

export type SectorType = 'industry' | 'concept'

export type GradeType = 'S+' | 'S' | 'A+' | 'A' | 'B+' | 'B' | 'C' | 'D'

export interface SectorTableItem {
  id: number
  code: string
  name: string
  sector_type: SectorType  // 后端返回的字段名
  score: number | null
  short_term_score: number | null
  medium_term_score: number | null
  long_term_score: number | null
  strength_grade: string | null
  strong_stock_ratio: number | null
  rank: number | null
}

export interface GradeSectorStats {
  grade: GradeType
  industry_count: number
  concept_count: number
  total_count: number
  sectors: SectorTableItem[]
}

export interface SectorGradeTableResponse {
  date: string
  stats: GradeSectorStats[]  // 后端返回字段名是 stats
  total_industry: number
  total_concept: number
  total_sectors: number
  cache_status: 'hit' | 'miss'
}

export interface SectorDistributionResponse {
  date: string
  industry_count: number
  concept_count: number
  total_count: number
}

// 等级颜色映射
export const GRADE_COLOR_MAP: Record<GradeType, { bg: string; text: string; border: string }> = {
  'S+': { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200' },
  'S': { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-200' },
  'A+': { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-200' },
  'A': { bg: 'bg-lime-100', text: 'text-lime-700', border: 'border-lime-200' },
  'B+': { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200' },
  'B': { bg: 'bg-teal-100', text: 'text-teal-700', border: 'border-teal-200' },
  'C': { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-200' },
  'D': { bg: 'bg-gray-100', text: 'text-gray-700', border: 'border-gray-200' },
}

// 等级显示顺序
export const GRADE_ORDER: GradeType[] = ['S+', 'S', 'A+', 'A', 'B+', 'B', 'C', 'D']
