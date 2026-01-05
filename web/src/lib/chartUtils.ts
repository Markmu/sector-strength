/**
 * 图表工具函数
 *
 * 包含图表数据处理、金叉/死叉检测等通用算法
 */

import type { SectorMAHistoryPoint, CrossPoint } from '@/types'

/**
 * 金叉/死叉检测算法
 *
 * 检测 MA5 和 MA20 的交叉点：
 * - 金叉 (Golden Cross): MA5 上穿 MA20，看涨信号
 * - 死叉 (Death Cross): MA5 下穿 MA20，看跌信号
 *
 * 算法复杂度：O(n) 单次遍历
 *
 * @param data - 均线历史数据数组
 * @returns 交叉点数组，包含日期、类型和数值
 *
 * @example
 * ```ts
 * const crosses = detectCrosses(maData)
 * // [{ date: '2024-12-01', type: 'golden', value: 1234.56 }]
 * ```
 */
export function detectCrosses(data: SectorMAHistoryPoint[]): CrossPoint[] {
  const crosses: CrossPoint[] = []

  // 需要至少 2 个数据点才能检测交叉
  if (!data || data.length < 2) {
    return crosses
  }

  for (let i = 1; i < data.length; i++) {
    const prev = data[i - 1]
    const curr = data[i]

    const ma5Prev = prev.ma5
    const ma20Prev = prev.ma20
    const ma5Curr = curr.ma5
    const ma20Curr = curr.ma20

    // 处理 null/undefined 值 - 跳过数据不完整的点
    if (!ma5Prev || !ma20Prev || !ma5Curr || !ma20Curr) {
      continue
    }

    // 检测金叉: 昨日 MA5 < MA20，今日 MA5 > MA20
    if (ma5Prev < ma20Prev && ma5Curr > ma20Curr) {
      crosses.push({
        date: curr.date,
        type: 'golden',
        value: ma5Curr,
      })
    }

    // 检测死叉: 昨日 MA5 > MA20，今日 MA5 < MA20
    if (ma5Prev > ma20Prev && ma5Curr < ma20Curr) {
      crosses.push({
        date: curr.date,
        type: 'death',
        value: ma5Curr,
      })
    }
  }

  return crosses
}

/**
 * 计算统计信息
 *
 * @param crosses - 交叉点数组
 * @returns 包含金叉和死叉数量的统计对象
 */
export function getCrossStats(crosses: CrossPoint[]) {
  return {
    goldenCrossCount: crosses.filter((c) => c.type === 'golden').length,
    deathCrossCount: crosses.filter((c) => c.type === 'death').length,
    total: crosses.length,
  }
}
