/**
 * 管理员配置类型定义
 *
 * @description
 * 用于管理员配置页面的类型定义，包括分类参数配置和级别定义
 * 这些配置是系统常量，用于板块强弱分类算法
 */

/**
 * 分类级别定义
 */
export interface ClassificationLevelDefinition {
  /** 分类级别 (1-9) */
  level: number
  /** 级别名称 */
  name: string
  /** 说明 */
  description: string
  /** 颜色标识 (Tailwind 类名) */
  color: string
}

/**
 * 分类配置
 */
export interface ClassificationConfig {
  /** 均线周期（天） */
  ma_periods: number[]
  /** 判断基准天数（天） */
  benchmark_days: number
  /** 分类数量 */
  classification_count: number
  /** 分类级别定义 */
  level_definitions: ClassificationLevelDefinition[]
}

/**
 * 硬编码的分类配置（系统常量）
 *
 * @description
 * 缠论板块强弱分类的参数配置：
 * - 均线周期: 8 条均线 (5, 10, 20, 30, 60, 90, 120, 240 日线)
 * - 判断基准天数: 5 天
 * - 分类数量: 9 类（第 9 类最强 → 第 1 类最弱）
 *
 * 这些参数由算法团队设定，不应随意修改
 */
export const CLASSIFICATION_CONFIG: ClassificationConfig = {
  ma_periods: [5, 10, 20, 30, 60, 90, 120, 240],
  benchmark_days: 5,
  classification_count: 9,
  level_definitions: [
    {
      level: 9,
      name: '第 9 类',
      description: '价格在所有均线上方（最强）',
      color: 'text-emerald-600',
    },
    {
      level: 8,
      name: '第 8 类',
      description: '攻克 240 日线',
      color: 'text-emerald-500',
    },
    {
      level: 7,
      name: '第 7 类',
      description: '攻克 120 日线',
      color: 'text-green-500',
    },
    {
      level: 6,
      name: '第 6 类',
      description: '攻克 90 日线',
      color: 'text-lime-500',
    },
    {
      level: 5,
      name: '第 5 类',
      description: '攻克 60 日线',
      color: 'text-yellow-600',
    },
    {
      level: 4,
      name: '第 4 类',
      description: '攻克 30 日线',
      color: 'text-amber-600',
    },
    {
      level: 3,
      name: '第 3 类',
      description: '攻克 20 日线',
      color: 'text-orange-600',
    },
    {
      level: 2,
      name: '第 2 类',
      description: '攻克 10 日线',
      color: 'text-red-400',
    },
    {
      level: 1,
      name: '第 1 类',
      description: '价格在所有均线下方（最弱）',
      color: 'text-red-600',
    },
  ],
}

/**
 * 获取分类级别强度标签
 */
export function getLevelStrengthLabel(level: number): string {
  if (level === 9) return '最强'
  if (level === 1) return '最弱'
  if (level >= 7) return '强势'
  if (level >= 4) return '中等'
  return '弱势'
}

/**
 * 获取分类级别背景颜色
 */
export function getLevelBadgeColor(level: number): string {
  if (level >= 7) return 'bg-green-100 text-green-800'
  if (level >= 4) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}
