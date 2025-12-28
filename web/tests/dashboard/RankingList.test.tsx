/**
 * RankingList 组件测试
 * 测试板块和个股排名列表组件
 */

import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { RankingItemComponent } from '@/components/dashboard/RankingItem'
import { SectorRankingList } from '@/components/dashboard/SectorRankingList'
import { StockRankingList } from '@/components/dashboard/StockRankingList'
import { RankingSection } from '@/components/dashboard/RankingSection'
import { RankingTabs } from '@/components/dashboard/RankingTabs'
import type { RankingItem } from '@/lib/ranking/types'

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}))

// Mock SWR hooks
jest.mock('@/hooks/useSectorRanking', () => ({
  useSectorRanking: jest.fn(),
}))

jest.mock('@/hooks/useStockRanking', () => ({
  useStockRanking: jest.fn(),
}))

import { useSectorRanking } from '@/hooks/useSectorRanking'
import { useStockRanking } from '@/hooks/useStockRanking'

const mockUseSectorRanking = useSectorRanking as jest.MockedFunction<typeof useSectorRanking>
const mockUseStockRanking = useStockRanking as jest.MockedFunction<typeof useStockRanking>

describe('RankingItem', () => {
  const mockSectorData: RankingItem = {
    id: 'sector-1',
    name: '银行',
    code: 'BK01',
    strength_score: 85.5,
    trend_direction: 1,
    rank: 1,
  }

  it('应该正确渲染板块列表项', () => {
    render(<RankingItemComponent data={mockSectorData} type="sector" />)

    expect(screen.getByText('银行')).toBeInTheDocument()
    expect(screen.getByText('BK01')).toBeInTheDocument()
    expect(screen.getByText('85.5')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
  })

  it('应该正确显示趋势图标', () => {
    const { rerender } = render(<RankingItemComponent data={mockSectorData} type="sector" />)
    expect(screen.getByText('↑')).toBeInTheDocument()

    const trendDownData: RankingItem = { ...mockSectorData, trend_direction: -1 }
    rerender(<RankingItemComponent data={trendDownData} type="sector" />)
    expect(screen.getByText('↓')).toBeInTheDocument()
  })

  it('应该正确应用颜色编码', () => {
    const { container } = render(<RankingItemComponent data={mockSectorData} type="sector" />)

    // 高强度 (>= 80) 应该是绿色
    const scoreElement = screen.getByText('85.5')
    expect(scoreElement).toHaveClass('text-green-600')

    // 上升趋势应该是绿色
    const trendIcon = screen.getByText('↑')
    expect(trendIcon).toHaveClass('text-green-600')
  })
})

describe('SectorRankingList', () => {
  const mockSectors: RankingItem[] = [
    {
      id: 'sector-1',
      name: '银行',
      code: 'BK01',
      strength_score: 85.5,
      trend_direction: 1,
      rank: 1,
    },
    {
      id: 'sector-2',
      name: '科技',
      code: 'TC01',
      strength_score: 78.2,
      trend_direction: 0,
      rank: 2,
    },
  ]

  it('加载状态应该显示 LoadingState', () => {
    mockUseSectorRanking.mockReturnValue({
      sectors: [],
      total: 0,
      isLoading: true,
      isError: false,
      mutate: jest.fn(),
    })

    render(<SectorRankingList />)
    expect(screen.getByText(/加载板块排名/)).toBeInTheDocument()
  })

  it('错误状态应该显示 ErrorState', () => {
    mockUseSectorRanking.mockReturnValue({
      sectors: [],
      total: 0,
      isLoading: false,
      isError: true,
      mutate: jest.fn(),
    })

    render(<SectorRankingList />)
    expect(screen.getByText(/加载板块排名失败/)).toBeInTheDocument()
  })

  it('应该正确渲染板块列表', () => {
    mockUseSectorRanking.mockReturnValue({
      sectors: mockSectors,
      total: 45,
      isLoading: false,
      isError: false,
      mutate: jest.fn(),
    })

    render(<SectorRankingList topN={10} />)

    expect(screen.getByText('板块强度排名 TOP 10')).toBeInTheDocument()
    expect(screen.getByText('共 45 个板块')).toBeInTheDocument()
    expect(screen.getByText('银行')).toBeInTheDocument()
    expect(screen.getByText('科技')).toBeInTheDocument()
  })

  it('空数据状态应该显示提示', () => {
    mockUseSectorRanking.mockReturnValue({
      sectors: [],
      total: 0,
      isLoading: false,
      isError: false,
      mutate: jest.fn(),
    })

    render(<SectorRankingList />)
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })
})

describe('StockRankingList', () => {
  const mockStocks: RankingItem[] = [
    {
      id: 'stock-1',
      name: '平安银行',
      code: '000001',
      strength_score: 92.3,
      trend_direction: 1,
      rank: 1,
    },
    {
      id: 'stock-2',
      name: '腾讯控股',
      code: '00700',
      strength_score: 88.7,
      trend_direction: 0,
      rank: 2,
    },
  ]

  it('加载状态应该显示 LoadingState', () => {
    mockUseStockRanking.mockReturnValue({
      stocks: [],
      total: 0,
      isLoading: true,
      isError: false,
      mutate: jest.fn(),
    })

    render(<StockRankingList />)
    expect(screen.getByText(/加载个股排名/)).toBeInTheDocument()
  })

  it('应该正确渲染个股列表', () => {
    mockUseStockRanking.mockReturnValue({
      stocks: mockStocks,
      total: 5000,
      isLoading: false,
      isError: false,
      mutate: jest.fn(),
    })

    render(<StockRankingList topN={20} />)

    expect(screen.getByText('个股强度排名 TOP 20')).toBeInTheDocument()
    expect(screen.getByText('共 5000 只个股')).toBeInTheDocument()
    expect(screen.getByText('平安银行')).toBeInTheDocument()
    expect(screen.getByText('腾讯控股')).toBeInTheDocument()
  })
})

describe('RankingSection', () => {
  it('应该正确渲染桌面端布局', () => {
    mockUseSectorRanking.mockReturnValue({
      sectors: [],
      total: 0,
      isLoading: false,
      isError: false,
      mutate: jest.fn(),
    })

    mockUseStockRanking.mockReturnValue({
      stocks: [],
      total: 0,
      isLoading: false,
      isError: false,
      mutate: jest.fn(),
    })

    render(<RankingSection />)

    expect(screen.getByText('排序:')).toBeInTheDocument()
    expect(screen.getByText('强度')).toBeInTheDocument()
    expect(screen.getByText('趋势')).toBeInTheDocument()
  })
})

describe('RankingTabs', () => {
  it('应该正确渲染 Tab 切换', () => {
    mockUseSectorRanking.mockReturnValue({
      sectors: [],
      total: 0,
      isLoading: false,
      isError: false,
      mutate: jest.fn(),
    })

    mockUseStockRanking.mockReturnValue({
      stocks: [],
      total: 0,
      isLoading: false,
      isError: false,
      mutate: jest.fn(),
    })

    render(<RankingTabs />)

    expect(screen.getByText('板块排名')).toBeInTheDocument()
    expect(screen.getByText('个股排名')).toBeInTheDocument()
  })

  it('点击 Tab 应该切换内容', async () => {
    mockUseSectorRanking.mockReturnValue({
      sectors: [],
      total: 0,
      isLoading: false,
      isError: false,
      mutate: jest.fn(),
    })

    mockUseStockRanking.mockReturnValue({
      stocks: [],
      total: 0,
      isLoading: false,
      isError: false,
      mutate: jest.fn(),
    })

    render(<RankingTabs />)

    const stocksTab = screen.getByText('个股排名')
    fireEvent.click(stocksTab)

    await waitFor(() => {
      expect(screen.getByText('个股排名')).toHaveClass('text-blue-600')
    })
  })
})
