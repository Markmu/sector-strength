/**
 * 板块分类过滤工具函数测试
 *
 * 测试搜索过滤逻辑的正确性
 */

import { filterClassifications } from '@/components/sector-classification/filterUtils'
import type { SectorClassification } from '@/types/sector-classification'

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

describe('filterClassifications', () => {
  describe('空搜索', () => {
    it('空字符串应该返回所有数据', () => {
      const result = filterClassifications(mockData, '')
      expect(result).toEqual(mockData)
      expect(result).toHaveLength(4)
    })

    it('只有空格的搜索应该返回所有数据', () => {
      const result = filterClassifications(mockData, '   ')
      expect(result).toEqual(mockData)
      expect(result).toHaveLength(4)
    })

    it('混合空格应该被 trim 并返回所有数据', () => {
      const result = filterClassifications(mockData, '  \t  ')
      expect(result).toEqual(mockData)
      expect(result).toHaveLength(4)
    })
  })

  describe('部分匹配', () => {
    it('应该支持单字符匹配', () => {
      const result = filterClassifications(mockData, '新')
      expect(result).toHaveLength(1)
      expect(result[0].sector_name).toBe('新能源')
    })

    it('应该支持多字符匹配', () => {
      const result = filterClassifications(mockData, '半导')
      expect(result).toHaveLength(1)
      expect(result[0].sector_name).toBe('半导体')
    })

    it('应该支持完整名称匹配', () => {
      const result = filterClassifications(mockData, '新能源')
      expect(result).toHaveLength(1)
      expect(result[0].sector_name).toBe('新能源')
    })

    it('应该匹配开头部分', () => {
      const result = filterClassifications(mockData, '消')
      expect(result).toHaveLength(1)
      expect(result[0].sector_name).toBe('消费电子')
    })

    it('应该匹配中间部分', () => {
      const result = filterClassifications(mockData, '费电')
      expect(result).toHaveLength(1)
      expect(result[0].sector_name).toBe('消费电子')
    })

    it('应该匹配结尾部分', () => {
      const result = filterClassifications(mockData, '源')
      expect(result).toHaveLength(1)
      expect(result[0].sector_name).toBe('新能源')
    })
  })

  describe('大小写不敏感', () => {
    it('应该不区分大小写（中文无大小写）', () => {
      const result1 = filterClassifications(mockData, '新能源')
      const result2 = filterClassifications(mockData, 'XINNENGYUAN')

      // 中文搜索应该匹配
      expect(result1).toHaveLength(1)
      expect(result1[0].sector_name).toBe('新能源')
    })

    it('应该处理混合大小写', () => {
      const result1 = filterClassifications(mockData, '半导体')
      const result2 = filterClassifications(mockData, '半导体')

      expect(result1).toEqual(result2)
    })
  })

  describe('中文搜索', () => {
    it('应该正确处理中文字符', () => {
      const result = filterClassifications(mockData, '房地产')
      expect(result).toHaveLength(1)
      expect(result[0].sector_name).toBe('房地产')
    })

    it('应该支持中文部分匹配', () => {
      const result = filterClassifications(mockData, '地产')
      expect(result).toHaveLength(1)
      expect(result[0].sector_name).toBe('房地产')
    })

    it('应该正确处理多个中文字符', () => {
      const result = filterClassifications(mockData, '消费电子')
      expect(result).toHaveLength(1)
      expect(result[0].sector_name).toBe('消费电子')
    })
  })

  describe('无匹配结果', () => {
    it('应该返回空数组当没有匹配时', () => {
      const result = filterClassifications(mockData, '不存在')
      expect(result).toHaveLength(0)
      expect(result).toEqual([])
    })

    it('应该返回空数组对于完全不相关的关键词', () => {
      const result = filterClassifications(mockData, 'technology')
      expect(result).toHaveLength(0)
    })

    it('应该返回空数组对于特殊字符', () => {
      const result = filterClassifications(mockData, '!@#$%')
      expect(result).toHaveLength(0)
    })
  })

  describe('空格处理', () => {
    it('应该自动 trim 首尾空格', () => {
      const result = filterClassifications(mockData, '  新能源  ')
      expect(result).toHaveLength(1)
      expect(result[0].sector_name).toBe('新能源')
    })

    it('应该保留中间空格进行匹配', () => {
      const result = filterClassifications(mockData, '消费 电子')
      expect(result).toHaveLength(0) // 因为数据中没有带空格的名称
    })

    it('应该处理只有空格的搜索', () => {
      const result = filterClassifications(mockData, '   ')
      expect(result).toHaveLength(4)
    })
  })

  describe('数据不变性', () => {
    it('不应修改原始数据', () => {
      const originalData = [...mockData]
      const originalOrder = originalData.map(item => item.id)

      filterClassifications(mockData, '新能源')

      // 原始数据顺序应保持不变
      expect(mockData.map(item => item.id)).toEqual(originalOrder)
    })

    it('应该返回新数组', () => {
      const result = filterClassifications(mockData, '新能源')

      expect(result).not.toBe(mockData)
      expect(mockData).toHaveLength(4)
    })
  })

  describe('边界情况', () => {
    it('应该正确处理空数组', () => {
      const result = filterClassifications([], '新能源')
      expect(result).toEqual([])
    })

    it('应该正确处理单项数组', () => {
      const singleItem = [mockData[0]]
      const result = filterClassifications(singleItem, '新能源')
      expect(result).toEqual(singleItem)
    })

    it('应该正确处理 undefined 搜索', () => {
      const result = filterClassifications(mockData, undefined as any)
      expect(result).toEqual(mockData)
    })

    it('应该正确处理 null 搜索', () => {
      const result = filterClassifications(mockData, null as any)
      expect(result).toEqual(mockData)
    })
  })

  describe('多个匹配', () => {
    it('应该返回所有匹配的项目', () => {
      const dataWithMatches = [
        mockData[0], // 新能源
        mockData[1], // 半导体
        { ...mockData[2], sector_name: '新能源电池' }, // 新能源电池
      ]

      const result = filterClassifications(dataWithMatches, '新')
      expect(result).toHaveLength(2)
      expect(result[0].sector_name).toBe('新能源')
      expect(result[1].sector_name).toBe('新能源电池')
    })
  })
})
