/**
 * TestResultDisplay 组件测试
 *
 * 测试测试结果展示组件的功能
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TestResultDisplay } from '@/components/admin/sector-classification/TestResultDisplay'
import type { TestResultDisplayProps } from '@/components/admin/sector-classification/TestResultDisplay.types'
import type { ClassificationTestResult } from '@/types/admin-test'

describe('TestResultDisplay', () => {
  const mockOnRetry = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  const defaultProps: TestResultDisplayProps = {
    result: null,
    error: null,
    onRetry: mockOnRetry,
    testing: false,
  }

  describe('初始状态', () => {
    it('无结果、无错误、非测试状态下应返回 null', () => {
      const { container } = render(<TestResultDisplay {...defaultProps} />)

      expect(container.firstChild).toBeNull()
    })
  })

  describe('测试中状态', () => {
    it('应该显示加载状态', () => {
      render(<TestResultDisplay {...defaultProps} testing={true} />)

      expect(screen.getByText('正在测试分类算法...')).toBeInTheDocument()
    })

    it('应该显示旋转加载图标', () => {
      render(<TestResultDisplay {...defaultProps} testing={true} />)

      const loader = document.querySelector('.animate-spin')
      expect(loader).toBeInTheDocument()
    })
  })

  describe('成功状态', () => {
    const successResult: ClassificationTestResult = {
      total_count: 50,
      success_count: 50,
      failure_count: 0,
      duration_ms: 1234,
      timestamp: '2026-01-26T10:00:00Z',
    }

    it('应该显示成功结果', () => {
      render(<TestResultDisplay {...defaultProps} result={successResult} />)

      expect(screen.getByText('测试完成')).toBeInTheDocument()
      expect(screen.getByText(/共计算 50 个板块分类/)).toBeInTheDocument()
    })

    it('应该显示成功数量', () => {
      render(<TestResultDisplay {...defaultProps} result={successResult} />)

      expect(screen.getByText('成功数量')).toBeInTheDocument()
      expect(screen.getByText('50')).toBeInTheDocument()
    })

    it('应该显示失败数量（成功时为0）', () => {
      render(<TestResultDisplay {...defaultProps} result={successResult} />)

      expect(screen.getByText('失败数量')).toBeInTheDocument()
      expect(screen.getByText('0')).toBeInTheDocument()
    })

    it('应该显示计算耗时', () => {
      render(<TestResultDisplay {...defaultProps} result={successResult} />)

      expect(screen.getByText('计算耗时')).toBeInTheDocument()
      expect(screen.getByText('1234')).toBeInTheDocument()
    })

    it('应该显示测试时间', () => {
      render(<TestResultDisplay {...defaultProps} result={successResult} />)

      expect(screen.getByText('测试时间')).toBeInTheDocument()
      expect(screen.getByText(/2026/)).toBeInTheDocument()
    })

    it('成功状态卡片应有绿色样式', () => {
      const { container } = render(
        <TestResultDisplay {...defaultProps} result={successResult} />
      )

      const card = container.querySelector('.border-green-200')
      expect(card).toBeInTheDocument()
    })
  })

  describe('部分失败状态', () => {
    const partialFailureResult: ClassificationTestResult = {
      total_count: 50,
      success_count: 45,
      failure_count: 5,
      duration_ms: 2345,
      timestamp: '2026-01-26T11:00:00Z',
      failures: [
        { sector_id: '1', sector_name: '测试板块A', error: '数据不足' },
        { sector_id: '2', sector_name: '测试板块B', error: '计算错误' },
      ],
    }

    it('应该显示部分完成标题', () => {
      render(<TestResultDisplay {...defaultProps} result={partialFailureResult} />)

      expect(screen.getByText('测试完成（部分失败）')).toBeInTheDocument()
    })

    it('应该显示失败的板块列表', () => {
      render(<TestResultDisplay {...defaultProps} result={partialFailureResult} />)

      expect(screen.getByText('失败的板块：')).toBeInTheDocument()
      expect(screen.getByText(/测试板块A.*数据不足/)).toBeInTheDocument()
      expect(screen.getByText(/测试板块B.*计算错误/)).toBeInTheDocument()
    })

    it('部分失败卡片应有琥珀色样式', () => {
      const { container } = render(
        <TestResultDisplay {...defaultProps} result={partialFailureResult} />
      )

      const card = container.querySelector('.border-amber-200')
      expect(card).toBeInTheDocument()
    })
  })

  describe('错误状态', () => {
    const errorMessage = '网络连接失败，请检查网络设置'

    it('应该显示错误消息', () => {
      render(<TestResultDisplay {...defaultProps} error={errorMessage} />)

      expect(screen.getByText('测试失败')).toBeInTheDocument()
      expect(screen.getByText(errorMessage)).toBeInTheDocument()
    })

    it('应该显示重试按钮', () => {
      render(<TestResultDisplay {...defaultProps} error={errorMessage} />)

      expect(screen.getByRole('button', { name: /重试/ })).toBeInTheDocument()
    })

    it('点击重试按钮应该调用 onRetry', async () => {
      const user = userEvent.setup()
      render(<TestResultDisplay {...defaultProps} error={errorMessage} />)

      const retryButton = screen.getByRole('button', { name: /重试/ })
      await user.click(retryButton)

      expect(mockOnRetry).toHaveBeenCalledTimes(1)
    })

    it('错误卡片应有红色样式', () => {
      const { container } = render(
        <TestResultDisplay {...defaultProps} error={errorMessage} />
      )

      const card = container.querySelector('.border-red-200')
      expect(card).toBeInTheDocument()
    })
  })

  describe('完全失败状态', () => {
    const totalFailureResult: ClassificationTestResult = {
      total_count: 10,
      success_count: 0,
      failure_count: 10,
      duration_ms: 500,
      timestamp: '2026-01-26T12:00:00Z',
      failures: Array.from({ length: 10 }, (_, i) => ({
        sector_id: String(i + 1),
        sector_name: `板块${i + 1}`,
        error: '全部失败',
      })),
    }

    it('应该显示正确的统计信息', () => {
      render(<TestResultDisplay {...defaultProps} result={totalFailureResult} />)

      expect(screen.getByText(/共计算 10 个板块分类/)).toBeInTheDocument()
      expect(screen.getByText('0')).toBeInTheDocument() // 成功数
      expect(screen.getByText('10')).toBeInTheDocument() // 失败数
    })

    it('应该显示所有失败的板块', () => {
      render(<TestResultDisplay {...defaultProps} result={totalFailureResult} />)

      expect(screen.getByText('失败的板块：')).toBeInTheDocument()
      // 验证至少有一个失败项
      expect(screen.getByText(/板块1.*全部失败/)).toBeInTheDocument()
    })
  })
})
