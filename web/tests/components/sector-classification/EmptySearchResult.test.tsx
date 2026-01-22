/**
 * EmptySearchResult 组件测试
 *
 * 测试空搜索结果组件
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EmptySearchResult } from '@/components/sector-classification/EmptySearchResult'

// Mock Zustand store
jest.mock('@/stores/useSectorClassificationSearch', () => ({
  useSectorClassificationSearch: jest.fn(),
}))

const mockUseSectorClassificationSearch = jest.requireMock('@/stores/useSectorClassificationSearch')?.useSectorClassificationSearch

describe('EmptySearchResult', () => {
  const mockClearSearch = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    mockUseSectorClassificationSearch?.mockReturnValue({
      searchQuery: '测试搜索',
      clearSearch: mockClearSearch,
    })
  })

  describe('渲染', () => {
    it('应该渲染空结果容器', () => {
      const { container } = render(<EmptySearchResult />)

      expect(container.firstChild).toBeInTheDocument()
    })

    it('应该显示 SearchX 图标', () => {
      const { container } = render(<EmptySearchResult />)

      const svg = container.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('应该显示主标题', () => {
      render(<EmptySearchResult />)

      expect(screen.getByText('未找到匹配的板块')).toBeInTheDocument()
    })

    it('应该显示描述文本', () => {
      render(<EmptySearchResult />)

      expect(screen.getByText(/没有找到包含/)).toBeInTheDocument()
      expect(screen.getByText(/测试搜索/)).toBeInTheDocument()
    })

    it('应该显示清除搜索按钮', () => {
      render(<EmptySearchResult />)

      const button = screen.getByRole('button', { name: '清除搜索并显示所有板块' })
      expect(button).toBeInTheDocument()
    })

    it('应该应用自定义 className', () => {
      const { container } = render(<EmptySearchResult className="custom-class" />)

      expect(container.firstChild).toHaveClass('custom-class')
    })
  })

  describe('交互', () => {
    it('点击清除按钮应该调用 clearSearch', async () => {
      const user = userEvent.setup()
      render(<EmptySearchResult />)

      const button = screen.getByRole('button', { name: '清除搜索并显示所有板块' })
      await user.click(button)

      expect(mockClearSearch).toHaveBeenCalled()
    })

    it('清除按钮应该是可点击的', async () => {
      const user = userEvent.setup()
      render(<EmptySearchResult />)

      const button = screen.getByRole('button', { name: '清除搜索并显示所有板块' })
      expect(button).toHaveAttribute('type', 'button')
    })
  })

  describe('显示搜索关键词', () => {
    it('应该显示当前搜索关键词', () => {
      mockUseSectorClassificationSearch?.mockReturnValue({
        searchQuery: '新能源',
        clearSearch: mockClearSearch,
      })

      render(<EmptySearchResult />)

      expect(screen.getByText(/新能源/)).toBeInTheDocument()
    })

    it('应该显示特殊字符关键词', () => {
      mockUseSectorClassificationSearch?.mockReturnValue({
        searchQuery: '测试@#$%',
        clearSearch: mockClearSearch,
      })

      render(<EmptySearchResult />)

      // 使用函数匹配器来查找包含特定文本的元素
      const textElement = screen.getByText((content, element) => {
        return element?.textContent === '没有找到包含 "测试@#$%" 的板块'
      })
      expect(textElement).toBeInTheDocument()
    })

    it('应该显示空格处理后的关键词', () => {
      mockUseSectorClassificationSearch?.mockReturnValue({
        searchQuery: '  测试  ',
        clearSearch: mockClearSearch,
      })

      render(<EmptySearchResult />)

      // 应该显示原始搜索关键词（包括空格）
      // 使用函数匹配器来查找包含特定文本的元素
      const textElement = screen.getByText((content, element) => {
        return element?.textContent === '没有找到包含 "  测试  " 的板块'
      })
      expect(textElement).toBeInTheDocument()
    })
  })

  describe('可访问性', () => {
    it('清除按钮应该有正确的 aria-label', () => {
      render(<EmptySearchResult />)

      const button = screen.getByRole('button', { name: '清除搜索并显示所有板块' })
      expect(button).toBeInTheDocument()
    })

    it('图标应该有 aria-hidden', () => {
      const { container } = render(<EmptySearchResult />)

      const svg = container.querySelector('svg')
      expect(svg).toHaveAttribute('aria-hidden', 'true')
    })
  })

  describe('样式', () => {
    it('应该有正确的布局类', () => {
      const { container } = render(<EmptySearchResult />)

      const wrapper = container.firstChild
      expect(wrapper).toHaveClass('flex')
      expect(wrapper).toHaveClass('flex-col')
      expect(wrapper).toHaveClass('items-center')
    })

    it('图标应该有正确的样式', () => {
      const { container } = render(<EmptySearchResult />)

      const svg = container.querySelector('svg')
      expect(svg).toHaveClass('w-12')
      expect(svg).toHaveClass('h-12')
    })

    it('标题应该有正确的样式', () => {
      render(<EmptySearchResult />)

      const title = screen.getByText('未找到匹配的板块')
      expect(title).toHaveClass('text-lg')
      expect(title).toHaveClass('font-medium')
    })

    it('描述应该有正确的样式', () => {
      render(<EmptySearchResult />)

      const description = screen.getByText(/没有找到包含/)
      expect(description).toHaveClass('text-sm')
      expect(description).toHaveClass('text-gray-500')
    })

    it('按钮应该有正确的样式', () => {
      render(<EmptySearchResult />)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('text-blue-600')
      expect(button).toHaveClass('hover:text-blue-700')
    })
  })
})
