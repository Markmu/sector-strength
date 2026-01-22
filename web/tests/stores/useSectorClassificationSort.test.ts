/**
 * 板块分类排序 Store 测试
 *
 * 测试 Zustand 排序状态管理
 */

import { renderHook, act } from '@testing-library/react'
import { useSectorClassificationSort } from '@/stores/useSectorClassificationSort'
import type { SortColumn, SortOrder } from '@/stores/useSectorClassificationSort'

describe('useSectorClassificationSort', () => {
  beforeEach(() => {
    // 每个测试前重置 store 状态
    const { result } = renderHook(() => useSectorClassificationSort())
    act(() => {
      result.current.reset()
    })
  })

  describe('初始状态', () => {
    it('应该有默认排序状态', () => {
      const { result } = renderHook(() => useSectorClassificationSort())

      expect(result.current.sortBy).toBe('classification_level')
      expect(result.current.sortOrder).toBe('desc')
    })

    it('默认按分类级别降序排序', () => {
      const { result } = renderHook(() => useSectorClassificationSort())

      expect(result.current.sortBy).toBe('classification_level')
      expect(result.current.sortOrder).toBe('desc')
    })
  })

  describe('toggleSortBy', () => {
    it('首次点击新列应设置为降序', () => {
      const { result } = renderHook(() => useSectorClassificationSort())

      act(() => {
        result.current.toggleSortBy('sector_name')
      })

      expect(result.current.sortBy).toBe('sector_name')
      expect(result.current.sortOrder).toBe('desc')
    })

    it('点击当前排序列（降序）应切换为升序', () => {
      const { result } = renderHook(() => useSectorClassificationSort())

      // 初始状态：classification_level, desc
      expect(result.current.sortBy).toBe('classification_level')
      expect(result.current.sortOrder).toBe('desc')

      act(() => {
        result.current.toggleSortBy('classification_level')
      })

      expect(result.current.sortBy).toBe('classification_level')
      expect(result.current.sortOrder).toBe('asc')
    })

    it('再次点击当前排序列（升序）应切换回降序', () => {
      const { result } = renderHook(() => useSectorClassificationSort())

      // 第一次点击：切换为升序
      act(() => {
        result.current.toggleSortBy('classification_level')
      })
      expect(result.current.sortOrder).toBe('asc')

      // 第二次点击：切换回降序
      act(() => {
        result.current.toggleSortBy('classification_level')
      })
      expect(result.current.sortOrder).toBe('desc')
    })

    it('从不同列切换应重置为降序', () => {
      const { result } = renderHook(() => useSectorClassificationSort())

      // 设置 sector_name 为升序
      act(() => {
        result.current.toggleSortBy('sector_name')
      })
      act(() => {
        result.current.toggleSortBy('sector_name')
      })
      expect(result.current.sortBy).toBe('sector_name')
      expect(result.current.sortOrder).toBe('asc')

      // 切换到 change_percent
      act(() => {
        result.current.toggleSortBy('change_percent')
      })
      expect(result.current.sortBy).toBe('change_percent')
      expect(result.current.sortOrder).toBe('desc')
    })
  })

  describe('setSortBy', () => {
    it('应该能够设置排序列和方向', () => {
      const { result } = renderHook(() => useSectorClassificationSort())

      act(() => {
        result.current.setSortBy('change_percent', 'asc')
      })

      expect(result.current.sortBy).toBe('change_percent')
      expect(result.current.sortOrder).toBe('asc')
    })

    it('应该能够设置为任意排序列', () => {
      const { result } = renderHook(() => useSectorClassificationSort())

      const columns: SortColumn[] = ['classification_level', 'sector_name', 'change_percent']

      columns.forEach((column) => {
        act(() => {
          result.current.setSortBy(column, 'desc')
        })
        expect(result.current.sortBy).toBe(column)
        expect(result.current.sortOrder).toBe('desc')
      })
    })

    it('应该能够设置为任意排序方向', () => {
      const { result } = renderHook(() => useSectorClassificationSort())

      const orders: SortOrder[] = ['asc', 'desc']

      orders.forEach((order) => {
        act(() => {
          result.current.setSortBy('sector_name', order)
        })
        expect(result.current.sortOrder).toBe(order)
      })
    })
  })

  describe('reset', () => {
    it('应该重置为默认状态', () => {
      const { result } = renderHook(() => useSectorClassificationSort())

      // 修改状态
      act(() => {
        result.current.toggleSortBy('sector_name')
      })
      act(() => {
        result.current.toggleSortBy('sector_name')
      })
      expect(result.current.sortBy).toBe('sector_name')
      expect(result.current.sortOrder).toBe('asc')

      // 重置
      act(() => {
        result.current.reset()
      })

      expect(result.current.sortBy).toBe('classification_level')
      expect(result.current.sortOrder).toBe('desc')
    })

    it('重置后应能够正常操作', () => {
      const { result } = renderHook(() => useSectorClassificationSort())

      // 重置
      act(() => {
        result.current.reset()
      })

      // 重置后操作
      act(() => {
        result.current.toggleSortBy('change_percent')
      })
      expect(result.current.sortBy).toBe('change_percent')
      expect(result.current.sortOrder).toBe('desc')
    })
  })

  describe('状态持久性', () => {
    it('多个组件使用相同状态', () => {
      const { result: result1 } = renderHook(() => useSectorClassificationSort())
      const { result: result2 } = renderHook(() => useSectorClassificationSort())

      // 使用第一个 hook 修改状态
      act(() => {
        result1.current.toggleSortBy('sector_name')
      })

      // 第二个 hook 应该看到相同的状态
      expect(result2.current.sortBy).toBe('sector_name')
      expect(result2.current.sortOrder).toBe('desc')
    })
  })
})
