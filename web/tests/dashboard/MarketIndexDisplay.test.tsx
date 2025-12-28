/**
 * MarketIndexDisplay 组件测试
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MarketIndexDisplay } from '@/components/dashboard/MarketIndexDisplay'

// Mock ECharts 组件（避免 Canvas 错误）
jest.mock('echarts-for-react', () => ({
  __esModule: true,
  default: () => null, // 返回 null 跳过渲染
}))

// Mock SWR hook
jest.mock('@/hooks/useMarketIndex', () => ({
  useMarketIndex: jest.fn(),
}))

import { useMarketIndex } from '@/hooks/useMarketIndex'

const mockMarketIndexData = {
  index: {
    value: 68.5,
    change: 2.3,
    timestamp: '2025-12-28T10:30:00Z',
    color: '#10B981',
  },
  stats: {
    totalSectors: 45,
    upSectors: 28,
    downSectors: 15,
    neutralSectors: 2,
  },
  trend: [
    { timestamp: '2025-12-27T10:00:00Z', value: 65.2 },
    { timestamp: '2025-12-27T11:00:00Z', value: 66.8 },
    { timestamp: '2025-12-27T12:00:00Z', value: 68.5 },
  ],
}

describe('MarketIndexDisplay', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('渲染', () => {
    it('应该显示加载状态', () => {
      (useMarketIndex as jest.Mock).mockReturnValue({
        index: null,
        stats: null,
        trend: [],
        isLoading: true,
        isError: false,
      })

      render(<MarketIndexDisplay />)
      expect(screen.getByText(/加载市场指数/i)).toBeInTheDocument()
    })

    it('应该显示错误状态', () => {
      (useMarketIndex as jest.Mock).mockReturnValue({
        index: null,
        stats: null,
        trend: [],
        isLoading: false,
        isError: true,
      })

      render(<MarketIndexDisplay />)
      expect(screen.getByText(/加载市场指数失败/i)).toBeInTheDocument()
    })

    it('应该正确渲染市场指数数据', () => {
      (useMarketIndex as jest.Mock).mockReturnValue({
        ...mockMarketIndexData,
        isLoading: false,
        isError: false,
      })

      render(<MarketIndexDisplay />)

      expect(screen.getByText('68.5')).toBeInTheDocument()
      expect(screen.getByText('28')).toBeInTheDocument() // upSectors
      expect(screen.getByText('15')).toBeInTheDocument() // downSectors
      expect(screen.getByText('2')).toBeInTheDocument() // neutralSectors
    })

    it('应该显示上涨变化', () => {
      (useMarketIndex as jest.Mock).mockReturnValue({
        ...mockMarketIndexData,
        isLoading: false,
        isError: false,
      })

      render(<MarketIndexDisplay />)
      expect(screen.getByText(/\+2\.30/)).toBeInTheDocument()
    })

    it('应该显示下跌变化', () => {
      (useMarketIndex as jest.Mock).mockReturnValue({
        ...mockMarketIndexData,
        index: { ...mockMarketIndexData.index, change: -1.5 },
        isLoading: false,
        isError: false,
      })

      render(<MarketIndexDisplay />)
      expect(screen.getByText(/-1\.50/)).toBeInTheDocument()
    })
  })

  describe('交互', () => {
    it('点击详情按钮应该显示弹窗', async () => {
      (useMarketIndex as jest.Mock).mockReturnValue({
        ...mockMarketIndexData,
        isLoading: false,
        isError: false,
      })

      render(<MarketIndexDisplay />)

      const detailButton = screen.getByText(/查看计算方法和详情/i)
      fireEvent.click(detailButton)

      await waitFor(() => {
        expect(screen.getByText(/市场强度指数计算方法/i)).toBeInTheDocument()
      })
    })

    it('点击弹窗外部应该关闭弹窗', async () => {
      (useMarketIndex as jest.Mock).mockReturnValue({
        ...mockMarketIndexData,
        isLoading: false,
        isError: false,
      })

      render(<MarketIndexDisplay />)

      const detailButton = screen.getByText(/查看计算方法和详情/i)
      fireEvent.click(detailButton)

      await waitFor(() => {
        const modal = screen.getByText(/市场强度指数计算方法/i).closest('.bg-black\\/50')
        expect(modal).toBeInTheDocument()
      })

      const modal = screen.getByText(/市场强度指数计算方法/i).closest('.bg-black\\/50')
      fireEvent.click(modal!)

      await waitFor(() => {
        expect(screen.queryByText(/市场强度指数计算方法/i)).not.toBeInTheDocument()
      })
    })

    it('点击关闭按钮应该关闭弹窗', async () => {
      (useMarketIndex as jest.Mock).mockReturnValue({
        ...mockMarketIndexData,
        isLoading: false,
        isError: false,
      })

      render(<MarketIndexDisplay />)

      const detailButton = screen.getByText(/查看计算方法和详情/i)
      fireEvent.click(detailButton)

      await waitFor(() => {
        const closeButton = screen.getByText(/关闭/i)
        fireEvent.click(closeButton)
      })

      await waitFor(() => {
        expect(screen.queryByText(/市场强度指数计算方法/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('边界情况', () => {
    it('应该处理空趋势数据', () => {
      (useMarketIndex as jest.Mock).mockReturnValue({
        ...mockMarketIndexData,
        trend: [],
        isLoading: false,
        isError: false,
      })

      render(<MarketIndexDisplay />)
      expect(screen.queryByText(/24小时趋势/i)).not.toBeInTheDocument()
    })

    it('应该处理零值指数', () => {
      (useMarketIndex as jest.Mock).mockReturnValue({
        index: { value: 0, change: 0, timestamp: '2025-12-28T10:30:00Z', color: '#EF4444' },
        stats: { totalSectors: 0, upSectors: 0, downSectors: 0, neutralSectors: 0 },
        trend: [],
        isLoading: false,
        isError: false,
      })

      render(<MarketIndexDisplay />)
      expect(screen.getByText('0.0')).toBeInTheDocument()
    })

    it('应该正确计算百分比', () => {
      (useMarketIndex as jest.Mock).mockReturnValue({
        ...mockMarketIndexData,
        isLoading: false,
        isError: false,
      })

      render(<MarketIndexDisplay />)
      expect(screen.getByText('62%')).toBeInTheDocument() // 28/45
      expect(screen.getByText('4%')).toBeInTheDocument() // 2/45
    })
  })
})
