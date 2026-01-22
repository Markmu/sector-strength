/**
 * 板块分类排序工具函数测试
 *
 * 测试排序逻辑的正确性
 */

import { sortClassifications } from '@/components/sector-classification/sortUtils'
import type { SectorClassification } from '@/types/sector-classification'
import type { SortColumn, SortOrder } from '@/stores/useSectorClassificationSort'

// 测试数据
const mockData: SectorClassification[] = [
  {
    id: '1',
    sector_id: 'sector-1',
    sector_name: '新能源',
    classification_date: '2026-01-22',
    classification_level: 9,
    state: '反弹',
    current_price: 1234.56,
    change_percent: 2.5,
    created_at: '2026-01-22T10:00:00Z',
  },
  {
    id: '2',
    sector_id: 'sector-2',
    sector_name: '半导体',
    classification_date: '2026-01-22',
    classification_level: 5,
    state: '调整',
    current_price: 987.65,
    change_percent: -1.2,
    created_at: '2026-01-22T10:00:00Z',
  },
  {
    id: '3',
    sector_id: 'sector-3',
    sector_name: '消费电子',
    classification_date: '2026-01-22',
    classification_level: 1,
    state: '调整',
    current_price: 567.89,
    change_percent: 0,
    created_at: '2026-01-22T10:00:00Z',
  },
  {
    id: '4',
    sector_id: 'sector-4',
    sector_name: '房地产',
    classification_date: '2026-01-22',
    classification_level: 3,
    state: '反弹',
    current_price: 345.67,
    change_percent: -3.5,
    created_at: '2026-01-22T10:00:00Z',
  },
]

describe('sortClassifications', () => {
  describe('分类级别排序', () => {
    it('应该按分类级别降序排序（第 9 类在前）', () => {
      const result = sortClassifications(mockData, 'classification_level', 'desc')

      expect(result[0].classification_level).toBe(9)
      expect(result[1].classification_level).toBe(5)
      expect(result[2].classification_level).toBe(3)
      expect(result[3].classification_level).toBe(1)
    })

    it('应该按分类级别升序排序（第 1 类在前）', () => {
      const result = sortClassifications(mockData, 'classification_level', 'asc')

      expect(result[0].classification_level).toBe(1)
      expect(result[1].classification_level).toBe(3)
      expect(result[2].classification_level).toBe(5)
      expect(result[3].classification_level).toBe(9)
    })

    it('相同级别应保持原顺序', () => {
      const dataWithSameLevel = [
        { ...mockData[0], classification_level: 5 },
        { ...mockData[1], classification_level: 5 },
      ]

      const result = sortClassifications(dataWithSameLevel, 'classification_level', 'desc')

      // 相同级别时，sort 是稳定的，保持原顺序
      expect(result[0].id).toBe(dataWithSameLevel[0].id)
      expect(result[1].id).toBe(dataWithSameLevel[1].id)
    })
  })

  describe('板块名称排序', () => {
    it('应该按板块名称升序排序（字母顺序）', () => {
      const result = sortClassifications(mockData, 'sector_name', 'asc')

      expect(result[0].sector_name).toBe('半导体')
      expect(result[1].sector_name).toBe('房地产')
      expect(result[2].sector_name).toBe('新能源')
      expect(result[3].sector_name).toBe('消费电子')
    })

    it('应该按板块名称降序排序（字母倒序）', () => {
      const result = sortClassifications(mockData, 'sector_name', 'desc')

      expect(result[0].sector_name).toBe('消费电子')
      expect(result[1].sector_name).toBe('新能源')
      expect(result[2].sector_name).toBe('房地产')
      expect(result[3].sector_name).toBe('半导体')
    })

    it('应该正确处理中文字符排序', () => {
      const chineseData: SectorClassification[] = [
        { ...mockData[0], sector_name: '人工智能' },
        { ...mockData[1], sector_name: '新能源' },
        { ...mockData[2], sector_name: '半导体' },
      ]

      const result = sortClassifications(chineseData, 'sector_name', 'asc')

      // 使用 localeCompare('zh-CN') 正确排序中文
      expect(result[0].sector_name).toBe('人工智能')
      expect(result[1].sector_name).toBe('半导体')
      expect(result[2].sector_name).toBe('新能源')
    })
  })

  describe('涨跌幅排序', () => {
    it('应该按涨跌幅降序排序（最大涨幅在前）', () => {
      const result = sortClassifications(mockData, 'change_percent', 'desc')

      expect(result[0].change_percent).toBe(2.5)
      expect(result[1].change_percent).toBe(0)
      expect(result[2].change_percent).toBe(-1.2)
      expect(result[3].change_percent).toBe(-3.5)
    })

    it('应该按涨跌幅升序排序（最大跌幅在前）', () => {
      const result = sortClassifications(mockData, 'change_percent', 'asc')

      expect(result[0].change_percent).toBe(-3.5)
      expect(result[1].change_percent).toBe(-1.2)
      expect(result[2].change_percent).toBe(0)
      expect(result[3].change_percent).toBe(2.5)
    })

    it('应该正确处理正数、负数和零', () => {
      const result = sortClassifications(mockData, 'change_percent', 'desc')

      // 验证正数在零之前
      const positiveIndex = result.findIndex(item => item.change_percent > 0)
      const zeroIndex = result.findIndex(item => item.change_percent === 0)
      const negativeIndex = result.findIndex(item => item.change_percent < 0)

      expect(positiveIndex).toBeLessThan(zeroIndex)
      expect(zeroIndex).toBeLessThan(negativeIndex)
    })
  })

  describe('数据不变性', () => {
    it('不应修改原始数据', () => {
      const originalData = [...mockData]
      const originalOrder = originalData.map(item => item.id)

      sortClassifications(mockData, 'classification_level', 'desc')

      // 原始数据顺序应保持不变
      expect(mockData.map(item => item.id)).toEqual(originalOrder)
    })

    it('应该返回新数组', () => {
      const result = sortClassifications(mockData, 'classification_level', 'desc')

      expect(result).not.toBe(mockData)
      expect(mockData).toHaveLength(4)
      expect(result).toHaveLength(4)
    })
  })

  describe('空数组处理', () => {
    it('应该正确处理空数组', () => {
      const result = sortClassifications([], 'classification_level', 'desc')

      expect(result).toEqual([])
    })

    it('应该正确处理单项数组', () => {
      const singleItem = [mockData[0]]
      const result = sortClassifications(singleItem, 'classification_level', 'desc')

      expect(result).toEqual(singleItem)
    })
  })
})
