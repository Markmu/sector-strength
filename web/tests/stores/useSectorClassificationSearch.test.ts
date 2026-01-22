/**
 * 板块分类搜索 Store 测试
 *
 * 测试 Zustand 搜索状态管理
 */

import { renderHook, act } from '@testing-library/react'
import { useSectorClassificationSearch } from '@/stores/useSectorClassificationSearch'

describe('useSectorClassificationSearch', () => {
  beforeEach(() => {
    // 每个测试前重置 store 状态
    const { result } = renderHook(() => useSectorClassificationSearch())
    act(() => {
      result.current.clearSearch()
    })
  })

  describe('初始状态', () => {
    it('应该有空的初始搜索状态', () => {
      const { result } = renderHook(() => useSectorClassificationSearch())

      expect(result.current.searchQuery).toBe('')
    })
  })

  describe('setSearchQuery', () => {
    it('应该能够设置搜索关键词', () => {
      const { result } = renderHook(() => useSectorClassificationSearch())

      act(() => {
        result.current.setSearchQuery('新能源')
      })

      expect(result.current.searchQuery).toBe('新能源')
    })

    it('应该能够设置为空字符串', () => {
      const { result } = renderHook(() => useSectorClassificationSearch())

      act(() => {
        result.current.setSearchQuery('测试')
      })
      expect(result.current.searchQuery).toBe('测试')

      act(() => {
        result.current.setSearchQuery('')
      })
      expect(result.current.searchQuery).toBe('')
    })

    it('应该能够设置包含空格的关键词', () => {
      const { result } = renderHook(() => useSectorClassificationSearch())

      act(() => {
        result.current.setSearchQuery('  半导体  ')
      })

      expect(result.current.searchQuery).toBe('  半导体  ')
    })

    it('应该能够设置中文关键词', () => {
      const { result } = renderHook(() => useSectorClassificationSearch())

      act(() => {
        result.current.setSearchQuery('人工智能')
      })

      expect(result.current.searchQuery).toBe('人工智能')
    })

    it('应该能够设置英文关键词', () => {
      const { result } = renderHook(() => useSectorClassificationSearch())

      act(() => {
        result.current.setSearchQuery('technology')
      })

      expect(result.current.searchQuery).toBe('technology')
    })
  })

  describe('clearSearch', () => {
    it('应该能够清除搜索', () => {
      const { result } = renderHook(() => useSectorClassificationSearch())

      act(() => {
        result.current.setSearchQuery('测试')
      })
      expect(result.current.searchQuery).toBe('测试')

      act(() => {
        result.current.clearSearch()
      })
      expect(result.current.searchQuery).toBe('')
    })

    it('多次清除应该保持为空字符串', () => {
      const { result } = renderHook(() => useSectorClassificationSearch())

      act(() => {
        result.current.setSearchQuery('测试1')
      })
      act(() => {
        result.current.clearSearch()
      })
      expect(result.current.searchQuery).toBe('')

      act(() => {
        result.current.setSearchQuery('测试2')
      })
      act(() => {
        result.current.clearSearch()
      })
      expect(result.current.searchQuery).toBe('')

      act(() => {
        result.current.clearSearch()
      })
      expect(result.current.searchQuery).toBe('')
    })

    it('清除空搜索应该保持为空', () => {
      const { result } = renderHook(() => useSectorClassificationSearch())

      expect(result.current.searchQuery).toBe('')

      act(() => {
        result.current.clearSearch()
      })
      expect(result.current.searchQuery).toBe('')
    })
  })

  describe('状态持久性', () => {
    it('多个组件使用相同状态', () => {
      const { result: result1 } = renderHook(() => useSectorClassificationSearch())
      const { result: result2 } = renderHook(() => useSectorClassificationSearch())

      // 使用第一个 hook 修改状态
      act(() => {
        result1.current.setSearchQuery('新能源')
      })

      // 第二个 hook 应该看到相同的状态
      expect(result2.current.searchQuery).toBe('新能源')
    })

    it('清除操作应该影响所有组件', () => {
      const { result: result1 } = renderHook(() => useSectorClassificationSearch())
      const { result: result2 } = renderHook(() => useSectorClassificationSearch())

      act(() => {
        result1.current.setSearchQuery('测试')
      })
      expect(result2.current.searchQuery).toBe('测试')

      act(() => {
        result2.current.clearSearch()
      })
      expect(result1.current.searchQuery).toBe('')
    })
  })
})
