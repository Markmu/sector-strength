/**
 * 金叉/死叉检测算法测试
 */

import type { SectorMAHistoryPoint } from '@/types'
import { detectCrosses } from '@/lib/chartUtils'

describe('金叉/死叉检测算法', () => {
  it('应该正确检测金叉', () => {
    const data: SectorMAHistoryPoint[] = [
      {
        date: '2024-12-01',
        current_price: 1000,
        ma5: 1000,
        ma20: 1010, // MA5 < MA20
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
      {
        date: '2024-12-02',
        current_price: 1020,
        ma5: 1015,
        ma20: 1012, // MA5 > MA20 (金叉)
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
    ]

    const crosses = detectCrosses(data)

    expect(crosses).toHaveLength(1)
    expect(crosses[0].type).toBe('golden')
    expect(crosses[0].date).toBe('2024-12-02')
    expect(crosses[0].value).toBe(1015)
  })

  it('应该正确检测死叉', () => {
    const data: SectorMAHistoryPoint[] = [
      {
        date: '2024-12-01',
        current_price: 1020,
        ma5: 1015,
        ma20: 1010, // MA5 > MA20
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
      {
        date: '2024-12-02',
        current_price: 1000,
        ma5: 1005,
        ma20: 1012, // MA5 < MA20 (死叉)
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
    ]

    const crosses = detectCrosses(data)

    expect(crosses).toHaveLength(1)
    expect(crosses[0].type).toBe('death')
    expect(crosses[0].date).toBe('2024-12-02')
    expect(crosses[0].value).toBe(1005)
  })

  it('应该正确检测多个金叉和死叉', () => {
    const data: SectorMAHistoryPoint[] = [
      {
        date: '2024-12-01',
        current_price: 1000,
        ma5: 1000,
        ma20: 1010, // MA5 < MA20
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
      {
        date: '2024-12-02',
        current_price: 1020,
        ma5: 1015,
        ma20: 1012, // 金叉
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
      {
        date: '2024-12-03',
        current_price: 1030,
        ma5: 1025,
        ma20: 1020, // 继续上涨
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
      {
        date: '2024-12-04',
        current_price: 1010,
        ma5: 1015,
        ma20: 1025, // 死叉
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
    ]

    const crosses = detectCrosses(data)

    expect(crosses).toHaveLength(2)
    expect(crosses[0].type).toBe('golden')
    expect(crosses[1].type).toBe('death')
  })

  it('应该跳过均线值为 null 的数据点', () => {
    const data: SectorMAHistoryPoint[] = [
      {
        date: '2024-12-01',
        current_price: 1000,
        ma5: null, // null 值
        ma20: 1010,
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
      {
        date: '2024-12-02',
        current_price: 1020,
        ma5: 1015,
        ma20: 1012,
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
    ]

    const crosses = detectCrosses(data)

    // 第一个数据点的 null 值应该被跳过
    expect(crosses).toHaveLength(0)
  })

  it('应该处理空数据', () => {
    const data: SectorMAHistoryPoint[] = []

    const crosses = detectCrosses(data)

    expect(crosses).toHaveLength(0)
  })

  it('应该处理只有一个数据点的情况', () => {
    const data: SectorMAHistoryPoint[] = [
      {
        date: '2024-12-01',
        current_price: 1000,
        ma5: 1000,
        ma20: 1010,
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
    ]

    const crosses = detectCrosses(data)

    expect(crosses).toHaveLength(0)
  })

  it('应该不检测到无交叉的情况', () => {
    const data: SectorMAHistoryPoint[] = [
      {
        date: '2024-12-01',
        current_price: 1000,
        ma5: 1000,
        ma20: 1010, // MA5 < MA20
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
      {
        date: '2024-12-02',
        current_price: 1010,
        ma5: 1005,
        ma20: 1015, // MA5 < MA20 (仍低于 MA20，无交叉)
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
    ]

    const crosses = detectCrosses(data)

    expect(crosses).toHaveLength(0)
  })

  it('应该处理均线相等的情况（不触发交叉）', () => {
    const data: SectorMAHistoryPoint[] = [
      {
        date: '2024-12-01',
        current_price: 1000,
        ma5: 1000,
        ma20: 1000, // MA5 == MA20
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
      {
        date: '2024-12-02',
        current_price: 1020,
        ma5: 1015,
        ma20: 1012, // MA5 > MA20
        ma10: null,
        ma30: null,
        ma60: null,
        ma90: null,
        ma120: null,
        ma240: null,
      },
    ]

    const crosses = detectCrosses(data)

    // 相等情况不触发交叉
    expect(crosses).toHaveLength(0)
  })
})
