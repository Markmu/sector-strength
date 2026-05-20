/**
 * 板块强弱分类类型定义
 */

/**
 * 板块分类状态
 */
export type ClassificationState = '反弹' | '调整'

/**
 * 板块分类数据项
 */
export interface SectorClassification {
  id: string
  sector_id: string
  sector_name?: string | null  // 可能为空，使用 symbol 作为后备
  symbol?: string  // 板块编码
  classification_date: string
  classification_level: number  // 1-9
  state: ClassificationState
  current_price: number | null
  change_percent: number | null
  created_at: string
}

/**
 * 板块分类列表响应
 */
export interface SectorClassificationResponse {
  data: SectorClassification[]
  date: string
  total_count: number
  cache_status?: 'hit' | 'miss'
}

/**
 * 分类级别颜色样式
 */
export interface LevelColorStyle {
  bg: string
  text: string
  border: string
}

export const LEVEL_COLOR_MAP: Record<number, LevelColorStyle> = {
  9: { bg: 'bg-red-700', text: 'text-white', border: 'border-red-800' },
  8: { bg: 'bg-red-500', text: 'text-white', border: 'border-red-600' },
  7: { bg: 'bg-orange-500', text: 'text-white', border: 'border-orange-600' },
  6: { bg: 'bg-amber-500', text: 'text-white', border: 'border-amber-600' },
  5: { bg: 'bg-yellow-500', text: 'text-black', border: 'border-yellow-600' },
  4: { bg: 'bg-lime-500', text: 'text-black', border: 'border-lime-600' },
  3: { bg: 'bg-green-500', text: 'text-white', border: 'border-green-600' },
  2: { bg: 'bg-emerald-500', text: 'text-white', border: 'border-emerald-600' },
  1: { bg: 'bg-emerald-700', text: 'text-white', border: 'border-emerald-800' },
}

/**
 * 获取分类级别颜色样式
 */
export function getLevelColor(level: number): LevelColorStyle {
  return LEVEL_COLOR_MAP[level] || { bg: 'bg-gray-500', text: 'text-white', border: 'border-gray-600' }
}

/**
 * 获取涨跌幅颜色样式
 */
export function getChangeColor(value: number): string {
  if (value > 0) return 'text-rise'
  if (value < 0) return 'text-fall'
  return 'text-muted-foreground'
}

export function getStateColor(state: ClassificationState): string {
  return state === '反弹' ? 'text-rise' : 'text-fall'
}
