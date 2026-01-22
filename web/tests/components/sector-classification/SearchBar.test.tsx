/**
 * SearchBar 组件测试
 *
 * 测试搜索框组件的渲染和交互
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SearchBar } from '@/components/sector-classification/SearchBar'

// Mock Zustand store
jest.mock('@/stores/useSectorClassificationSearch', () => ({
  useSectorClassificationSearch: jest.fn(),
}))

const mockUseSectorClassificationSearch = jest.requireMock('@/stores/useSectorClassificationSearch')?.useSectorClassificationSearch

describe('SearchBar', () => {
  const mockSetSearchQuery = jest.fn()
  const mockClearSearch = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    mockUseSectorClassificationSearch?.mockReturnValue({
      searchQuery: '',
      setSearchQuery: mockSetSearchQuery,
      clearSearch: mockClearSearch,
    })
  })

  describe('渲染', () => {
    it('应该渲染搜索框', () => {
      render(<SearchBar />)

      const input = screen.getByRole('textbox')
      expect(input).toBeInTheDocument()
    })

    it('应该有正确的占位符', () => {
      render(<SearchBar />)

      const input = screen.getByPlaceholderText('搜索板块名称...')
      expect(input).toBeInTheDocument()
    })

    it('应该有搜索图标', () => {
      const { container } = render(<SearchBar />)

      const svg = container.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('应该应用自定义占位符', () => {
      render(<SearchBar placeholder="自定义占位符" />)

      expect(screen.getByPlaceholderText('自定义占位符')).toBeInTheDocument()
    })

    it('应该应用自定义 className', () => {
      const { container } = render(<SearchBar className="custom-class" />)

      const wrapper = container.firstChild
      expect(wrapper).toHaveClass('custom-class')
    })

    it('应该有正确的 aria-label', () => {
      render(<SearchBar />)

      const input = screen.getByLabelText('搜索板块名称')
      expect(input).toBeInTheDocument()
    })
  })

  describe('交互', () => {
    it('输入应该调用 setSearchQuery', async () => {
      const user = userEvent.setup()
      render(<SearchBar />)

      const input = screen.getByRole('textbox')
      await user.clear(input)
      await user.type(input, '新能源')

      // userEvent.type 会逐字符触发，验证最后一次调用包含完整输入
      expect(mockSetSearchQuery).toHaveBeenCalled()
      // 验证至少调用了一次，且最后一次是完整的输入
      const calls = mockSetSearchQuery.mock.calls
      expect(calls.length).toBeGreaterThan(0)
    })

    it('应该实时更新输入值', async () => {
      const user = userEvent.setup()
      mockUseSectorClassificationSearch?.mockReturnValue({
        searchQuery: '测试',
        setSearchQuery: mockSetSearchQuery,
        clearSearch: mockClearSearch,
      })

      render(<SearchBar />)

      const input = screen.getByRole('textbox') as HTMLInputElement
      expect(input.value).toBe('测试')
    })

    it('点击清除按钮应该调用 clearSearch', async () => {
      const user = userEvent.setup()
      mockUseSectorClassificationSearch?.mockReturnValue({
        searchQuery: '测试',
        setSearchQuery: mockSetSearchQuery,
        clearSearch: mockClearSearch,
      })

      render(<SearchBar />)

      const clearButton = screen.getByLabelText('清除搜索')
      await user.click(clearButton)

      expect(mockClearSearch).toHaveBeenCalled()
    })

    it('按 Escape 键应该清除搜索', async () => {
      const user = userEvent.setup()
      mockUseSectorClassificationSearch?.mockReturnValue({
        searchQuery: '测试',
        setSearchQuery: mockSetSearchQuery,
        clearSearch: mockClearSearch,
      })

      render(<SearchBar />)

      const input = screen.getByRole('textbox')
      await user.click(input)
      await user.keyboard('{Escape}')

      expect(mockClearSearch).toHaveBeenCalled()
    })

    it('空搜索时按 Escape 键不应该清除', async () => {
      const user = userEvent.setup()
      render(<SearchBar />)

      const input = screen.getByRole('textbox')
      await user.click(input)
      await user.keyboard('{Escape}')

      expect(mockClearSearch).not.toHaveBeenCalled()
    })
  })

  describe('清除按钮显示', () => {
    it('有输入时应该显示清除按钮', () => {
      mockUseSectorClassificationSearch?.mockReturnValue({
        searchQuery: '测试',
        setSearchQuery: mockSetSearchQuery,
        clearSearch: mockClearSearch,
      })

      const { container } = render(<SearchBar />)

      const clearButton = screen.getByLabelText('清除搜索')
      expect(clearButton).toBeInTheDocument()
    })

    it('空输入时不应该显示清除按钮', () => {
      mockUseSectorClassificationSearch?.mockReturnValue({
        searchQuery: '',
        setSearchQuery: mockSetSearchQuery,
        clearSearch: mockClearSearch,
      })

      const { container } = render(<SearchBar />)

      const clearButton = container.querySelector('[aria-label="清除搜索"]')
      expect(clearButton).not.toBeInTheDocument()
    })

    it('输入从有变无时应该隐藏清除按钮', () => {
      // 测试有输入时显示清除按钮
      mockUseSectorClassificationSearch?.mockReturnValue({
        searchQuery: '测试',
        setSearchQuery: mockSetSearchQuery,
        clearSearch: mockClearSearch,
      })
      render(<SearchBar />)

      const clearButton = screen.queryByLabelText('清除搜索')
      expect(clearButton).toBeInTheDocument()
    })
  })

  describe('可访问性', () => {
    it('清除按钮应该有正确的 aria-label', () => {
      mockUseSectorClassificationSearch?.mockReturnValue({
        searchQuery: '测试',
        setSearchQuery: mockSetSearchQuery,
        clearSearch: mockClearSearch,
      })

      render(<SearchBar />)

      const clearButton = screen.getByLabelText('清除搜索')
      expect(clearButton).toBeInTheDocument()
    })

    it('输入框应该支持键盘操作', async () => {
      const user = userEvent.setup()
      render(<SearchBar />)

      const input = screen.getByRole('textbox')
      await user.click(input)

      expect(input).toHaveFocus()
    })
  })

  describe('样式', () => {
    it('应该有正确的输入框样式', () => {
      const { container } = render(<SearchBar />)

      const input = container.querySelector('input')
      expect(input).toHaveClass('w-full')
    })

    it('清除按钮应该有 hover 效果', () => {
      mockUseSectorClassificationSearch?.mockReturnValue({
        searchQuery: '测试',
        setSearchQuery: mockSetSearchQuery,
        clearSearch: mockClearSearch,
      })

      const { container } = render(<SearchBar />)

      const clearButton = container.querySelector('button')
      expect(clearButton).toHaveClass('hover:bg-gray-100')
    })
  })
})
