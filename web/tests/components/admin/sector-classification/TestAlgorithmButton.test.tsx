/**
 * TestAlgorithmButton 组件测试
 *
 * 测试测试分类算法按钮的功能
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TestAlgorithmButton } from '@/components/admin/sector-classification/TestAlgorithmButton'
import type { TestAlgorithmButtonProps } from '@/components/admin/sector-classification/TestAlgorithmButton.types'

describe('TestAlgorithmButton', () => {
  const mockOnTest = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  const defaultProps: TestAlgorithmButtonProps = {
    testing: false,
    onTest: mockOnTest,
    disabled: false,
  }

  describe('渲染测试', () => {
    it('应该渲染按钮和图标', () => {
      render(<TestAlgorithmButton {...defaultProps} />)

      expect(screen.getByRole('button')).toBeInTheDocument()
      expect(screen.getByText('测试分类算法')).toBeInTheDocument()
    })

    it('非测试状态下应该显示 Play 图标', () => {
      render(<TestAlgorithmButton {...defaultProps} testing={false} />)

      const button = screen.getByRole('button')
      expect(button).toContainHTML('lucide-react')
      expect(screen.getByText('测试分类算法')).toBeInTheDocument()
    })

    it('测试状态下应该显示加载状态', () => {
      render(<TestAlgorithmButton {...defaultProps} testing={true} />)

      expect(screen.getByText('测试中...')).toBeInTheDocument()
      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
    })
  })

  describe('交互测试', () => {
    it('点击按钮应该调用 onTest 回调', async () => {
      const user = userEvent.setup()
      render(<TestAlgorithmButton {...defaultProps} />)

      const button = screen.getByRole('button')
      await user.click(button)

      expect(mockOnTest).toHaveBeenCalledTimes(1)
    })

    it('disabled=true 时应该禁用按钮', () => {
      render(<TestAlgorithmButton {...defaultProps} disabled={true} />)

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
    })

    it('testing=true 时应该禁用按钮', () => {
      render(<TestAlgorithmButton {...defaultProps} testing={true} />)

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
    })

    it('disabled 且 testing 时按钮应该禁用', () => {
      render(
        <TestAlgorithmButton {...defaultProps} disabled={true} testing={true} />
      )

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
    })

    it('禁用状态下点击不应调用 onTest', async () => {
      const user = userEvent.setup()
      render(<TestAlgorithmButton {...defaultProps} disabled={true} />)

      const button = screen.getByRole('button')
      await user.click(button)

      expect(mockOnTest).not.toHaveBeenCalled()
    })

    it('测试状态下点击不应调用 onTest', async () => {
      const user = userEvent.setup()
      render(<TestAlgorithmButton {...defaultProps} testing={true} />)

      const button = screen.getByRole('button')
      await user.click(button)

      expect(mockOnTest).not.toHaveBeenCalled()
    })
  })

  describe('样式测试', () => {
    it('应该使用 primary variant', () => {
      render(<TestAlgorithmButton {...defaultProps} />)

      const button = screen.getByRole('button')
      expect(button).toHaveClass('variant-primary')
    })

    it('测试状态下应该显示旋转动画', () => {
      render(<TestAlgorithmButton {...defaultProps} testing={true} />)

      const button = screen.getByRole('button')
      expect(button.innerHTML).toContain('animate-spin')
    })
  })
})
