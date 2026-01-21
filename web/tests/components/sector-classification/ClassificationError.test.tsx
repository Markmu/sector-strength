/**
 * ClassificationError 组件测试
 *
 * 测试错误状态显示和重试功能
 */

import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { ClassificationError } from '@/components/sector-classification/ClassificationError'

// Mock Button 组件
jest.mock('@/components/ui/Button', () => ({
  __esModule: true,
  default: ({
    children,
    onClick,
    loading,
    icon,
    ...props
  }: any) => (
    <button
      onClick={onClick}
      disabled={loading}
      data-loading={loading}
      {...props}
    >
      {icon && <span data-testid="button-icon">{icon}</span>}
      {children}
    </button>
  ),
})

describe('ClassificationError', () => {
  const mockRetry = jest.fn()

  beforeEach(() => {
    mockRetry.mockClear()
  })

  describe('渲染', () => {
    it('应显示错误消息', () => {
      render(<ClassificationError error="网络错误" onRetry={mockRetry} />)

      expect(screen.getByText('获取分类数据失败')).toBeInTheDocument()
      expect(screen.getByText('网络错误')).toBeInTheDocument()
    })

    it('应显示重试按钮', () => {
      render(<ClassificationError error="网络错误" onRetry={mockRetry} />)

      expect(screen.getByRole('button', { name: '重新加载' })).toBeInTheDocument()
    })

    it('应使用默认错误消息当 error 为 null', () => {
      render(<ClassificationError error={null} onRetry={mockRetry} />)

      expect(screen.getByText('获取数据失败，请重试')).toBeInTheDocument()
    })

    it('应映射已知错误类型到友好消息', () => {
      const knownErrors = [
        ['NETWORK_ERROR', '网络连接失败，请检查网络设置'],
        ['TIMEOUT', '请求超时，请稍后重试'],
        ['UNAUTHORIZED', '未授权，请重新登录'],
        ['FORBIDDEN', '无权限访问'],
        ['NOT_FOUND', '未找到分类数据'],
        ['SERVER_ERROR', '服务器错误，请稍后重试'],
      ]

      knownErrors.forEach(([errorType, expectedMessage]) => {
        const { rerender } = render(
          <ClassificationError error={errorType} onRetry={mockRetry} />
        )
        expect(screen.getByText(expectedMessage)).toBeInTheDocument()
        rerender(<div />)
      })
    })

    it('应显示正确的 ARIA 属性', () => {
      render(<ClassificationError error="网络错误" onRetry={mockRetry} />)

      const alertRegion = screen.getByRole('alert')
      expect(alertRegion).toHaveAttribute('aria-live', 'assertive')
      expect(alertRegion).toHaveAttribute('aria-atomic', 'true')
    })
  })

  describe('交互', () => {
    it('点击重试按钮应调用 onRetry', () => {
      render(<ClassificationError error="网络错误" onRetry={mockRetry} />)

      const retryButton = screen.getByRole('button', { name: '重新加载' })
      fireEvent.click(retryButton)

      expect(mockRetry).toHaveBeenCalledTimes(1)
    })

    it('isRetrying 为 true 时应禁用按钮', () => {
      render(
        <ClassificationError
          error="网络错误"
          onRetry={mockRetry}
          isRetrying={true}
        />
      )

      const retryButton = screen.getByRole('button', { name: '重新加载' })
      expect(retryButton).toBeDisabled()
      expect(retryButton).toHaveAttribute('data-loading', 'true')
    })

    it('isRetrying 为 false 时应启用按钮', () => {
      render(
        <ClassificationError
          error="网络错误"
          onRetry={mockRetry}
          isRetrying={false}
        />
      )

      const retryButton = screen.getByRole('button', { name: '重新加载' })
      expect(retryButton).not.toBeDisabled()
      expect(retryButton).toHaveAttribute('data-loading', 'false')
    })
  })

  describe('可访问性', () => {
    it('应有正确的 role 属性', () => {
      render(<ClassificationError error="网络错误" onRetry={mockRetry} />)

      expect(screen.getByRole('alert')).toBeInTheDocument()
    })

    it('重试按钮应有 aria-label', () => {
      render(<ClassificationError error="网络错误" onRetry={mockRetry} />)

      expect(
        screen.getByRole('button', { name: '重新获取分类数据' })
      ).toBeInTheDocument()
    })
  })
})
