/**
 * useKeyboardNavigation store 测试
 *
 * 测试键盘导航状态管理功能
 */

import { renderHook, act } from '@testing-library/react'
import { useKeyboardNavigation } from '@/stores/useKeyboardNavigation'

describe('useKeyboardNavigation', () => {
  beforeEach(() => {
    // 每个测试前重置 store 状态
    // Zustand store 是全局单例，需要直接获取 state 并重置
    useKeyboardNavigation.getState().clearFocus()
  })

  describe('初始状态', () => {
    it('应该没有初始焦点', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      expect(result.current.focusedCell).toBeNull()
    })
  })

  describe('设置焦点', () => {
    it('应该能够设置焦点到指定单元格', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(0, 0)
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 0, cellIndex: 0 })
    })

    it('应该能够设置焦点到任意单元格', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(5, 3)
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 5, cellIndex: 3 })
    })

    it('应该能够覆盖已有焦点', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(2, 1)
      })
      act(() => {
        result.current.setFocusedCell(4, 2)
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 4, cellIndex: 2 })
    })
  })

  describe('清除焦点', () => {
    it('应该能够清除焦点', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(2, 0)
      })
      expect(result.current.focusedCell).not.toBeNull()

      act(() => {
        result.current.clearFocus()
      })
      expect(result.current.focusedCell).toBeNull()
    })

    it('清除空焦点时不应该报错', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      expect(() => {
        act(() => {
          result.current.clearFocus()
        })
      }).not.toThrow()
    })
  })

  describe('向上移动 (moveUp)', () => {
    it('应该能够向上移动一行', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(2, 0)
      })
      act(() => {
        result.current.moveUp()
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 1, cellIndex: 0 })
    })

    it('不应该移动到第一行之上', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(0, 0)
      })
      act(() => {
        result.current.moveUp()
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 0, cellIndex: 0 })
    })

    it('没有焦点时不应该移动', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.moveUp()
      })

      expect(result.current.focusedCell).toBeNull()
    })

    it('向上移动时应该保持列索引不变', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(3, 2)
      })
      act(() => {
        result.current.moveUp()
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 2, cellIndex: 2 })
    })
  })

  describe('向下移动 (moveDown)', () => {
    it('应该能够向下移动一行', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(0, 0)
      })
      act(() => {
        result.current.moveDown(10)
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 1, cellIndex: 0 })
    })

    it('不应该移动到最后一行之下', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(4, 0)
      })
      act(() => {
        result.current.moveDown(5) // 5 行数据（索引 0-4）
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 4, cellIndex: 0 })
    })

    it('没有焦点时不应该移动', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.moveDown(10)
      })

      expect(result.current.focusedCell).toBeNull()
    })

    it('向下移动时应该保持列索引不变', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(1, 3)
      })
      act(() => {
        result.current.moveDown(10)
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 2, cellIndex: 3 })
    })
  })

  describe('向左移动 (moveLeft)', () => {
    it('应该能够向左移动一列', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(0, 2)
      })
      act(() => {
        result.current.moveLeft(5)
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 0, cellIndex: 1 })
    })

    it('不应该移动到第一列之左', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(0, 0)
      })
      act(() => {
        result.current.moveLeft(5)
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 0, cellIndex: 0 })
    })

    it('没有焦点时不应该移动', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.moveLeft(5)
      })

      expect(result.current.focusedCell).toBeNull()
    })

    it('向左移动时应该保持行索引不变', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(3, 2)
      })
      act(() => {
        result.current.moveLeft(5)
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 3, cellIndex: 1 })
    })
  })

  describe('向右移动 (moveRight)', () => {
    it('应该能够向右移动一列', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(0, 0)
      })
      act(() => {
        result.current.moveRight(5)
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 0, cellIndex: 1 })
    })

    it('不应该移动到最后一列之右', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(0, 4)
      })
      act(() => {
        result.current.moveRight(5) // 5 列数据（索引 0-4）
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 0, cellIndex: 4 })
    })

    it('没有焦点时不应该移动', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.moveRight(5)
      })

      expect(result.current.focusedCell).toBeNull()
    })

    it('向右移动时应该保持行索引不变', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(3, 1)
      })
      act(() => {
        result.current.moveRight(5)
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 3, cellIndex: 2 })
    })
  })

  describe('组合导航', () => {
    it('应该能够连续向上移动', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(3, 0)
      })
      act(() => {
        result.current.moveUp()
      })
      act(() => {
        result.current.moveUp()
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 1, cellIndex: 0 })
    })

    it('应该能够连续向下移动', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(0, 0)
      })
      act(() => {
        result.current.moveDown(10)
      })
      act(() => {
        result.current.moveDown(10)
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 2, cellIndex: 0 })
    })

    it('应该能够沿对角线移动', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      act(() => {
        result.current.setFocusedCell(1, 1)
      })
      act(() => {
        result.current.moveDown(10)
      })
      act(() => {
        result.current.moveRight(5)
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 2, cellIndex: 2 })
    })

    it('应该能够在边界处正确处理', () => {
      const { result } = renderHook(() => useKeyboardNavigation())

      // 从 (0, 0) 尝试向上和向左
      act(() => {
        result.current.setFocusedCell(0, 0)
      })
      act(() => {
        result.current.moveUp()
      })
      act(() => {
        result.current.moveLeft(5)
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 0, cellIndex: 0 })

      // 从 (4, 4) 尝试向下和向右（假设 5 行 5 列）
      act(() => {
        result.current.setFocusedCell(4, 4)
      })
      act(() => {
        result.current.moveDown(5)
      })
      act(() => {
        result.current.moveRight(5)
      })

      expect(result.current.focusedCell).toEqual({ rowIndex: 4, cellIndex: 4 })
    })
  })
})
