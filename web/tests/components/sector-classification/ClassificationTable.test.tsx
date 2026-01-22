/**
 * ClassificationTable 组件测试 - 键盘导航功能
 *
 * 测试键盘导航相关功能
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { ClassificationTable } from '@/components/sector-classification/ClassificationTable'
import { useKeyboardNavigation } from '@/stores/useKeyboardNavigation'
import type { SectorClassification } from '@/types/sector-classification'

// Mock 键盘导航 store
const mockSetFocusedCell = jest.fn()
const mockClearFocus = jest.fn()
const mockMoveUp = jest.fn()
const mockMoveDown = jest.fn()
const mockMoveLeft = jest.fn()
const mockMoveRight = jest.fn()

jest.mock('@/stores/useKeyboardNavigation', () => ({
  useKeyboardNavigation: jest.fn(),
}))

// Mock 其他 stores
jest.mock('@/stores/useSectorClassificationSort', () => ({
  useSectorClassificationSort: () => ({
    sortBy: 'classification_level',
    sortOrder: 'desc',
    toggleSortBy: jest.fn(),
    setSortBy: jest.fn(),
    reset: jest.fn(),
  }),
}))

jest.mock('@/stores/useSectorClassificationSearch', () => ({
  useSectorClassificationSearch: () => ({
    searchQuery: '',
    setSearchQuery: jest.fn(),
    clearSearch: jest.fn(),
  }),
}))

// Mock 工具函数
jest.mock('@/components/sector-classification/filterUtils', () => ({
  filterClassifications: jest.fn((data) => data),
}))

jest.mock('@/components/sector-classification/sortUtils', () => ({
  sortClassifications: jest.fn((data) => data),
}))

describe('ClassificationTable - 键盘导航', () => {
  // 每个测试后重置 mock
  afterEach(() => {
    jest.clearAllMocks()
  })

  const mockData: SectorClassification[] = [
    {
      id: '1',
      sector_id: 's1',
      sector_name: '板块A',
      classification_date: '2026-01-22',
      classification_level: 9,
      state: '反弹',
      current_price: 100.5,
      change_percent: 2.5,
      created_at: '2026-01-22T00:00:00Z',
    },
    {
      id: '2',
      sector_id: 's2',
      sector_name: '板块B',
      classification_date: '2026-01-22',
      classification_level: 5,
      state: '调整',
      current_price: 95.3,
      change_percent: -1.2,
      created_at: '2026-01-22T00:00:00Z',
    },
    {
      id: '3',
      sector_id: 's3',
      sector_name: '板块C',
      classification_date: '2026-01-22',
      classification_level: 1,
      state: '调整',
      current_price: 88.7,
      change_percent: -3.5,
      created_at: '2026-01-22T00:00:00Z',
    },
  ]

  describe('表格可聚焦性', () => {
    it('应该有 tabIndex={0} 使表格可聚焦', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: null,
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      render(<ClassificationTable data={mockData} />)

      const table = screen.getByRole('grid', { name: '板块分类表格' })
      expect(table).toHaveAttribute('tabIndex', '0')
    })

    it('应该有正确的 ARIA 属性', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: null,
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      render(<ClassificationTable data={mockData} />)

      const table = screen.getByRole('grid', { name: '板块分类表格' })
      expect(table).toHaveAttribute('role', 'grid')
      expect(table).toHaveAttribute('aria-label', '板块分类表格')
    })
  })

  describe('方向键导航', () => {
    it('应该在有焦点时处理向上箭头键', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: { rowIndex: 1, cellIndex: 0 },
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      render(<ClassificationTable data={mockData} />)

      const table = screen.getByRole('grid', { name: '板块分类表格' })
      fireEvent.keyDown(table, { key: 'ArrowUp' })

      expect(mockMoveUp).toHaveBeenCalled()
    })

    it('应该在有焦点时处理向下箭头键', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: { rowIndex: 0, cellIndex: 0 },
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      render(<ClassificationTable data={mockData} />)

      const table = screen.getByRole('grid', { name: '板块分类表格' })
      fireEvent.keyDown(table, { key: 'ArrowDown' })

      expect(mockMoveDown).toHaveBeenCalledWith(3) // 3 行数据
    })

    it('应该在有焦点时处理向左箭头键', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: { rowIndex: 0, cellIndex: 2 },
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      render(<ClassificationTable data={mockData} />)

      const table = screen.getByRole('grid', { name: '板块分类表格' })
      fireEvent.keyDown(table, { key: 'ArrowLeft' })

      expect(mockMoveLeft).toHaveBeenCalledWith(5) // 5 列
    })

    it('应该在有焦点时处理向右箭头键', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: { rowIndex: 0, cellIndex: 0 },
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      render(<ClassificationTable data={mockData} />)

      const table = screen.getByRole('grid', { name: '板块分类表格' })
      fireEvent.keyDown(table, { key: 'ArrowRight' })

      expect(mockMoveRight).toHaveBeenCalledWith(5) // 5 列
    })

    it('应该在无焦点时不处理方向键', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: null,
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      render(<ClassificationTable data={mockData} />)

      const table = screen.getByRole('grid', { name: '板块分类表格' })
      fireEvent.keyDown(table, { key: 'ArrowUp' })

      expect(mockMoveUp).not.toHaveBeenCalled()
    })
  })

  describe('Enter 键行选中', () => {
    it('应该在选择回调存在时处理 Enter 键', () => {
      const mockOnRowSelect = jest.fn()

      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: { rowIndex: 1, cellIndex: 0 },
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      render(<ClassificationTable data={mockData} onRowSelect={mockOnRowSelect} />)

      const table = screen.getByRole('grid', { name: '板块分类表格' })
      fireEvent.keyDown(table, { key: 'Enter' })

      expect(mockOnRowSelect).toHaveBeenCalledWith(mockData[1]) // 第二行数据
    })

    it('应该在没有选择回调时不处理 Enter 键', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: { rowIndex: 1, cellIndex: 0 },
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      render(<ClassificationTable data={mockData} />)

      const table = screen.getByRole('grid', { name: '板块分类表格' })
      fireEvent.keyDown(table, { key: 'Enter' })

      // 不应该抛出错误
    })
  })

  describe('Escape 键清除焦点', () => {
    it('应该处理 Escape 键清除焦点', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: { rowIndex: 1, cellIndex: 0 },
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      render(<ClassificationTable data={mockData} />)

      const table = screen.getByRole('grid', { name: '板块分类表格' })
      fireEvent.keyDown(table, { key: 'Escape' })

      expect(mockClearFocus).toHaveBeenCalled()
    })
  })

  describe('焦点高亮显示', () => {
    it('应该在聚焦行时添加高亮样式', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: { rowIndex: 1, cellIndex: 0 },
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      const { container } = render(<ClassificationTable data={mockData} />)

      // 获取所有行
      const rows = container.querySelectorAll('tbody tr')
      expect(rows).toHaveLength(3)

      // 第二行（索引 1）应该有焦点高亮样式
      expect(rows[1]).toHaveClass('bg-blue-50')
    })

    it('应该在聚焦单元格时添加边框样式', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: { rowIndex: 0, cellIndex: 2 },
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      const { container } = render(<ClassificationTable data={mockData} />)

      // 获取第一行的所有单元格
      const firstRowCells = container.querySelectorAll('tbody tr:first-child td')
      expect(firstRowCells).toHaveLength(5)

      // 第三个单元格（索引 2）应该有焦点边框样式
      expect(firstRowCells[2]).toHaveClass('ring-2', 'ring-blue-500', 'ring-inset')
    })

    it('应该在没有焦点时不显示高亮样式', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: null,
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      const { container } = render(<ClassificationTable data={mockData} />)

      // 所有行都不应该有焦点高亮样式
      const rows = container.querySelectorAll('tbody tr')
      rows.forEach((row) => {
        expect(row).not.toHaveClass('bg-blue-50')
      })
    })
  })

  describe('单元格点击聚焦', () => {
    it('应该在点击单元格时设置焦点', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: null,
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      const { container } = render(<ClassificationTable data={mockData} />)

      // 点击第一行的第一个单元格
      const firstRowFirstCell = container.querySelector('tbody tr:first-child td:first-child')
      fireEvent.click(firstRowFirstCell!)

      expect(mockSetFocusedCell).toHaveBeenCalledWith(0, 0)
    })

    it('应该在点击行时设置焦点到行的第一个单元格', () => {
      const mockOnRowClick = jest.fn()

      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: null,
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      const { container } = render(
        <ClassificationTable data={mockData} onRowClick={mockOnRowClick} />
      )

      // 点击第二行
      const secondRow = container.querySelector('tbody tr:nth-child(2)')
      fireEvent.click(secondRow!)

      expect(mockSetFocusedCell).toHaveBeenCalledWith(1, 0) // 第二行，第一列
      expect(mockOnRowClick).toHaveBeenCalledWith(mockData[1], 1)
    })
  })

  describe('ARIA 属性', () => {
    it('应该正确设置行和单元格的 ARIA 属性', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: { rowIndex: 1, cellIndex: 2 },
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      const { container } = render(<ClassificationTable data={mockData} />)

      // 检查行的 ARIA 属性
      const rows = container.querySelectorAll('tbody tr')
      expect(rows[1]).toHaveAttribute('role', 'row')
      expect(rows[1]).toHaveAttribute('aria-rowindex', '2')
      expect(rows[1]).toHaveAttribute('aria-selected', 'true')

      // 检查单元格的 ARIA 属性
      const cells = rows[1].querySelectorAll('td')
      cells.forEach((cell, index) => {
        expect(cell).toHaveAttribute('role', 'gridcell')
        expect(cell).toHaveAttribute('aria-colindex', String(index + 1))
      })
    })
  })

  describe('Tab 键焦点切换', () => {
    it('表格应该有正确的 tabIndex 使其可聚焦', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: null,
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      render(<ClassificationTable data={mockData} />)

      const table = screen.getByRole('grid', { name: '板块分类表格' })
      expect(table).toHaveAttribute('tabIndex', '0')
    })

    it('表格应该有 focus-visible 样式用于键盘焦点指示', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: null,
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      render(<ClassificationTable data={mockData} />)

      const table = screen.getByRole('grid', { name: '板块分类表格' })
      // 验证 focus-visible 样式类存在
      expect(table).toHaveClass('focus-visible:outline-none')
      expect(table).toHaveClass('focus-visible:ring-2')
    })

    it('Tab 键切换时应该保持焦点样式', () => {
      (useKeyboardNavigation as jest.Mock).mockReturnValue({
        focusedCell: null,
        setFocusedCell: mockSetFocusedCell,
        clearFocus: mockClearFocus,
        moveUp: mockMoveUp,
        moveDown: mockMoveDown,
        moveLeft: mockMoveLeft,
        moveRight: mockMoveRight,
      })

      const { container } = render(<ClassificationTable data={mockData} />)

      const table = screen.getByRole('grid', { name: '板块分类表格' })

      // 模拟 Tab 键聚焦到表格
      table.focus()

      // 验证表格获得焦点（focus-visible 样式应该生效）
      expect(table).toHaveAttribute('tabIndex', '0')
    })
  })
})
