/**
 * SortableTableHeader 组件测试
 *
 * 测试可排序表头组件的渲染和交互
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { SortableTableHeader } from '@/components/sector-classification/SortableTableHeader'
import { useSectorClassificationSort } from '@/stores/useSectorClassificationSort'

// Mock Zustand store
jest.mock('@/stores/useSectorClassificationSort')

const mockUseSectorClassificationSort = useSectorClassificationSort as jest.MockedFunction<typeof useSectorClassificationSort>

describe('SortableTableHeader', () => {
  const mockToggleSortBy = jest.fn()
  const mockSortState = {
    sortBy: 'classification_level' as const,
    sortOrder: 'desc' as const,
    toggleSortBy: mockToggleSortBy,
    setSortBy: jest.fn(),
    reset: jest.fn(),
  }

  beforeEach(() => {
    jest.clearAllMocks()
    mockUseSectorClassificationSort.mockReturnValue(mockSortState)
  })

  describe('渲染', () => {
    it('应该渲染表头文本', () => {
      render(<SortableTableHeader column="sector_name" label="板块名称" />)

      expect(screen.getByText('板块名称')).toBeInTheDocument()
    })

    it('应该应用正确的对齐方式（左对齐）', () => {
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" align="left" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveClass('text-left')
    })

    it('应该应用居中对齐', () => {
      const { container } = render(
        <SortableTableHeader column="classification_level" label="分类级别" align="center" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveClass('text-center')
    })

    it('应该应用右对齐', () => {
      const { container } = render(
        <SortableTableHeader column="change_percent" label="涨跌幅" align="right" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveClass('text-right')
    })

    it('应该应用自定义 className', () => {
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" className="custom-class" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveClass('custom-class')
    })

    it('应该是可点击的（cursor-pointer）', () => {
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveClass('cursor-pointer')
    })
  })

  describe('排序指示器', () => {
    it('当前排序列应该显示高亮背景', () => {
      mockSortState.sortBy = 'sector_name'
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveClass('bg-gray-50')
    })

    it('非当前排序列不应该显示高亮背景', () => {
      mockSortState.sortBy = 'classification_level'
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')
      expect(th).not.toHaveClass('bg-gray-50')
    })

    it('升序排序应该显示向上箭头图标', () => {
      mockSortState.sortBy = 'sector_name'
      mockSortState.sortOrder = 'asc'
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const svg = container.querySelector('svg')
      expect(svg).toBeInTheDocument()
      // ChevronUp 图标路径
      expect(svg?.querySelector('path')?.getAttribute('d')).toContain('M5 15l7-7 7 7')
    })

    it('降序排序应该显示向下箭头图标', () => {
      mockSortState.sortBy = 'sector_name'
      mockSortState.sortOrder = 'desc'
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const svg = container.querySelector('svg')
      expect(svg).toBeInTheDocument()
      // ChevronDown 图标路径
      expect(svg?.querySelector('path')?.getAttribute('d')).toContain('M19 9l-7 7-7-7')
    })

    it('非当前排序列不应该显示排序图标', () => {
      mockSortState.sortBy = 'classification_level'
      render(<SortableTableHeader column="sector_name" label="板块名称" />)

      // 不应该有 SVG（没有排序图标）
      const svgs = document.querySelectorAll('svg')
      // 注意：页面上可能有其他 SVG，所以这里只检查我们组件内部
      // 更好的方式是检查容器内是否有 SVG
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )
      const svg = container.querySelector('svg')
      expect(svg).not.toBeInTheDocument()
    })
  })

  describe('交互', () => {
    it('点击应该调用 toggleSortBy', () => {
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')!
      fireEvent.click(th)

      expect(mockToggleSortBy).toHaveBeenCalledWith('sector_name')
      expect(mockToggleSortBy).toHaveBeenCalledTimes(1)
    })

    it('按 Enter 键应该触发排序', () => {
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')!
      fireEvent.keyDown(th, { key: 'Enter' })

      expect(mockToggleSortBy).toHaveBeenCalledWith('sector_name')
    })

    it('按 Space 键应该触发排序', () => {
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')!
      fireEvent.keyDown(th, { key: ' ' })

      expect(mockToggleSortBy).toHaveBeenCalledWith('sector_name')
    })

    it('按其他键不应该触发排序', () => {
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')!
      fireEvent.keyDown(th, { key: 'a' })

      expect(mockToggleSortBy).not.toHaveBeenCalled()
    })
  })

  describe('可访问性', () => {
    it('应该有正确的 ARIA 属性（升序）', () => {
      mockSortState.sortBy = 'sector_name'
      mockSortState.sortOrder = 'asc'
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveAttribute('aria-sort', 'ascending')
    })

    it('应该有正确的 ARIA 属性（降序）', () => {
      mockSortState.sortBy = 'sector_name'
      mockSortState.sortOrder = 'desc'
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveAttribute('aria-sort', 'descending')
    })

    it('非活动列应该有 aria-sort="none"', () => {
      mockSortState.sortBy = 'classification_level'
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveAttribute('aria-sort', 'none')
    })

    it('应该有 role="columnheader"', () => {
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveAttribute('role', 'columnheader')
    })

    it('应该有 scope="col"', () => {
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveAttribute('scope', 'col')
    })

    it('应该有 tabIndex={0} 以支持键盘导航', () => {
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveAttribute('tabIndex', '0')
    })

    it('排序图标应该有 aria-label', () => {
      mockSortState.sortBy = 'sector_name'
      mockSortState.sortOrder = 'asc'
      render(<SortableTableHeader column="sector_name" label="板块名称" />)

      const iconContainer = screen.getByLabelText('排序：升序')
      expect(iconContainer).toBeInTheDocument()
    })
  })

  describe('样式', () => {
    it('应该有 hover 效果', () => {
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveClass('hover:bg-gray-100')
    })

    it('应该有过渡效果', () => {
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveClass('transition-colors')
    })

    it('应该是不可选择的', () => {
      const { container } = render(
        <SortableTableHeader column="sector_name" label="板块名称" />
      )

      const th = container.querySelector('th')
      expect(th).toHaveClass('select-none')
    })
  })
})
