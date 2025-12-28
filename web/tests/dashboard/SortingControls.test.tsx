/**
 * SortingControls 组件测试
 * 测试排序控制组件的功能
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { SortingControls } from '@/components/dashboard/SortingControls'

describe('SortingControls', () => {
  const mockProps = {
    sortBy: 'strength' as const,
    sortOrder: 'desc' as const,
    onSortByChange: jest.fn(),
    onSortOrderChange: jest.fn(),
  }

  beforeEach(() => {
    jest.clearAllMocks()
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.runOnlyPendingTimers()
    jest.useRealTimers()
  })

  describe('渲染', () => {
    it('应该正确渲染排序控件', () => {
      render(<SortingControls {...mockProps} />)

      expect(screen.getByText('排序:')).toBeInTheDocument()
      expect(screen.getByText('强度')).toBeInTheDocument()
      expect(screen.getByText('趋势')).toBeInTheDocument()
      expect(screen.getByText('降序')).toBeInTheDocument()
    })

    it('应该高亮当前选中的排序字段', () => {
      render(<SortingControls {...mockProps} sortBy="strength" />)

      const strengthButton = screen.getByText('强度')
      expect(strengthButton).toHaveClass('bg-blue-500', 'text-white')
    })

    it('应该正确显示排序方向', () => {
      render(<SortingControls {...mockProps} sortOrder="desc" />)
      expect(screen.getByText('降序')).toBeInTheDocument()

      const { rerender } = render(<SortingControls {...mockProps} sortOrder="asc" />)
      rerender(<SortingControls {...mockProps} sortOrder="asc" />)
      expect(screen.getByText('升序')).toBeInTheDocument()
    })
  })

  describe('交互', () => {
    it('点击强度按钮应该触发 onSortByChange（防抖300ms）', async () => {
      render(<SortingControls {...mockProps} />)

      const strengthButton = screen.getByText('强度')
      fireEvent.click(strengthButton)

      // 300ms 内不应该调用
      expect(mockProps.onSortByChange).not.toHaveBeenCalled()

      // 快进 300ms
      jest.advanceTimersByTime(300)

      await waitFor(() => {
        expect(mockProps.onSortByChange).toHaveBeenCalledWith('strength')
      })
    })

    it('点击趋势按钮应该触发 onSortByChange（防抖300ms）', async () => {
      render(<SortingControls {...mockProps} />)

      const trendButton = screen.getByText('趋势')
      fireEvent.click(trendButton)

      jest.advanceTimersByTime(300)

      await waitFor(() => {
        expect(mockProps.onSortByChange).toHaveBeenCalledWith('trend')
      })
    })

    it('点击排序方向按钮应该触发 onSortOrderChange（防抖300ms）', async () => {
      render(<SortingControls {...mockProps} sortOrder="desc" />)

      const orderButton = screen.getByText('降序')
      fireEvent.click(orderButton)

      jest.advanceTimersByTime(300)

      await waitFor(() => {
        expect(mockProps.onSortOrderChange).toHaveBeenCalledWith('asc')
      })
    })

    it('快速连续点击应该只触发一次（防抖）', async () => {
      render(<SortingControls {...mockProps} />)

      const strengthButton = screen.getByText('强度')

      // 快速点击 3 次
      fireEvent.click(strengthButton)
      fireEvent.click(strengthButton)
      fireEvent.click(strengthButton)

      jest.advanceTimersByTime(300)

      await waitFor(() => {
        expect(mockProps.onSortByChange).toHaveBeenCalledTimes(1)
      })
    })

    it('组件卸载时应该清理定时器', () => {
      const { unmount } = render(<SortingControls {...mockProps} />)

      const strengthButton = screen.getByText('强度')
      fireEvent.click(strengthButton)

      // 在定时器触发前卸载组件
      unmount()

      jest.advanceTimersByTime(300)

      // 由于组件已卸载，回调不应该被调用
      expect(mockProps.onSortByChange).not.toHaveBeenCalled()
    })
  })

  describe('防抖功能', () => {
    it('应该在 300ms 后触发回调', async () => {
      render(<SortingControls {...mockProps} />)

      const strengthButton = screen.getByText('强度')
      fireEvent.click(strengthButton)

      // 200ms 时还未触发
      jest.advanceTimersByTime(200)
      expect(mockProps.onSortByChange).not.toHaveBeenCalled()

      // 300ms 时触发
      jest.advanceTimersByTime(100)
      await waitFor(() => {
        expect(mockProps.onSortByChange).toHaveBeenCalledTimes(1)
      })
    })

    it('后一次点击应该取消前一次的定时器', async () => {
      render(<SortingControls {...mockProps} />)

      const strengthButton = screen.getByText('强度')
      const trendButton = screen.getByText('趋势')

      // 点击强度
      fireEvent.click(strengthButton)
      jest.advanceTimersByTime(100)

      // 点击趋势（应该取消强度的定时器）
      fireEvent.click(trendButton)
      jest.advanceTimersByTime(300)

      await waitFor(() => {
        // 只应该调用趋势，强度被取消
        expect(mockProps.onSortByChange).toHaveBeenCalledTimes(1)
        expect(mockProps.onSortByChange).toHaveBeenCalledWith('trend')
      })
    })
  })
})
