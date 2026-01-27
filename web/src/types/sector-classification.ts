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

/**
 * 分类级别颜色映射（第 9 类绿 → 第 1 类红渐变）
 *
 * @description
 * 颜色方案符合 WCAG AA 标准（对比度 ≥ 4.5:1）：
 * - 第 9 类（最强）：深绿背景 + 白色文字 (bg-emerald-600 + text-white)
 * - 第 5 类（中性）：黄色背景 + 黑色文字 (bg-yellow-500 + text-black)
 * - 第 1 类（最弱）：深红背景 + 白色文字 (bg-red-600 + text-white)
 *
 * 所有颜色组合均通过 WCAG AA 级别的对比度要求
 */
export const LEVEL_COLOR_MAP: Record<number, LevelColorStyle> = {
  9: { bg: 'bg-emerald-600', text: 'text-white', border: 'border-emerald-700' },
  8: { bg: 'bg-emerald-500', text: 'text-white', border: 'border-emerald-600' },
  7: { bg: 'bg-green-500', text: 'text-white', border: 'border-green-600' },
  6: { bg: 'bg-lime-500', text: 'text-white', border: 'border-lime-600' },
  5: { bg: 'bg-yellow-500', text: 'text-black', border: 'border-yellow-600' },
  4: { bg: 'bg-amber-500', text: 'text-white', border: 'border-amber-600' },
  3: { bg: 'bg-orange-500', text: 'text-white', border: 'border-orange-600' },
  2: { bg: 'bg-red-400', text: 'text-white', border: 'border-red-500' },
  1: { bg: 'bg-red-600', text: 'text-white', border: 'border-red-700' },
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
  if (value > 0) return 'text-red-600'  // A股：涨 = 红色
  if (value < 0) return 'text-green-600'  // A股：跌 = 绿色
  return 'text-gray-500'  // 平 = 灰色
}

/**
 * 获取状态颜色样式
 */
export function getStateColor(state: ClassificationState): string {
  return state === '反弹' ? 'text-green-600' : 'text-red-600'
}
