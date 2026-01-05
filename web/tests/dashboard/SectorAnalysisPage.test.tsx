/**
 * 板块分析页面 E2E 测试
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { useSectorStrengthHistory, useSectorMAHistory } from '@/hooks'
import { useChartState } from '@/stores/useChartState'
import type { SectorStrengthHistoryResponse, SectorMAHistoryResponse } from '@/types'

// Mock next/navigation
const mockPush = jest.fn()
const mockBack = jest.fn()
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    back: mockBack,
  }),
}))

// Mock echarts-for-react
jest.mock('echarts-for-react', () => {
  return function MockReactECharts({ option, style }: any) {
    return (
      <div data-testid="echarts-mock" style={style}>
        <div data-testid="echarts-option">{JSON.stringify(option)}</div>
      </div>
    )
  }
})

// Mock hooks
jest.mock('@/hooks', () => ({
  useSectorStrengthHistory: jest.fn(),
  useSectorMAHistory: jest.fn(),
}))

// Mock store
jest.mock('@/stores/useChartState', () => ({
  useChartState: jest.fn(),
}))

// Mock DashboardLayout
jest.mock('@/components/dashboard', () => ({
  DashboardLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dashboard-layout">{children}</div>
  ),
  DashboardHeader: ({ title, subtitle }: { title: string; subtitle: string }) => (
    <div data-testid="dashboard-header">
      <div>{title}</div>
      <div>{subtitle}</div>
    </div>
  ),
  TimeRangeSelector: ({ value, onChange }: any) => (
    <div data-testid="time-range-selector">
      <div>当前选择: {value}</div>
      <button onClick={() => onChange('1m')}>1月</button>
      <button onClick={() => onChange('2m')}>2月</button>
      <button onClick={() => onChange('3m')}>3月</button>
    </div>
  ),
  MAToggleControls: ({ visibleMAs, onToggle }: any) => (
    <div data-testid="ma-toggle-controls">
      {Object.entries(visibleMAs).map(([key, visible]) => (
        <label key={key}>
          <input
            type="checkbox"
            checked={visible}
            onChange={() => onToggle(key)}
          />
          {key}
        </label>
      ))}
    </div>
  ),
  SectorStrengthChart: ({ data, sectorName }: any) => (
    <div data-testid="strength-chart">
      <div>{sectorName}</div>
      <div>数据点: {data.length}</div>
    </div>
  ),
  SectorMAChart: ({ data, sectorName, visibleMAs }: any) => (
    <div data-testid="ma-chart">
      <div>{sectorName}</div>
      <div>数据点: {data.length}</div>
      <div>可见均线: {Object.keys(visibleMAs).filter(k => visibleMAs[k as keyof typeof visibleMAs]).join(', ')}</div>
    </div>
  ),
  LoadingState: ({ message }: { message: string }) => (
    <div data-testid="loading-state">{message}</div>
  ),
  ErrorState: ({ message }: { message: string }) => (
    <div data-testid="error-state">{message}</div>
  ),
}))

// 动态导入页面
let SectorAnalysisPage: any
beforeAll(async () => {
  const module = await import('@/app/dashboard/sector-analysis/[sectorId]/page')
  SectorAnalysisPage = module.default
})

const mockStrengthData: SectorStrengthHistoryResponse = {
  sector_id: '1',
  sector_name: '测试板块',
  data: [
    {
      date: '2024-12-01',
      score: 65.5,
      current_price: 1234.56,
    },
    {
      date: '2024-12-02',
      score: 67.2,
      current_price: 1240.0,
    },
  ],
}

const mockMAData: SectorMAHistoryResponse = {
  sector_id: '1',
  sector_name: '测试板块',
  data: [
    {
      date: '2024-12-01',
      current_price: 1234.56,
      ma5: 1220.0,
      ma10: 1215.0,
      ma20: 1210.0,
      ma30: 1205.0,
      ma60: 1200.0,
      ma90: null,
      ma120: null,
      ma240: null,
    },
    {
      date: '2024-12-02',
      current_price: 1240.0,
      ma5: 1225.0,
      ma10: 1218.0,
      ma20: 1212.0,
      ma30: 1208.0,
      ma60: 1202.0,
      ma90: null,
      ma120: null,
      ma240: null,
    },
  ],
}

describe('板块分析页面', () => {
  beforeEach(() => {
    jest.clearAllMocks()

    // Mock useChartState
    ;(useChartState as jest.Mock).mockReturnValue({
      timeRange: '2m',
      visibleMAs: {
        ma5: true,
        ma10: true,
        ma20: true,
        ma30: true,
        ma60: true,
        ma90: false,
        ma120: false,
        ma240: false,
      },
      setTimeRange: jest.fn(),
      toggleMA: jest.fn(),
    })
  })

  it('应该正确加载和显示板块分析数据', async () => {
    // Mock hooks 返回数据
    ;(useSectorStrengthHistory as jest.Mock).mockReturnValue({
      data: mockStrengthData,
      isLoading: false,
      isError: false,
      error: null,
      mutate: jest.fn(),
    })

    ;(useSectorMAHistory as jest.Mock).mockReturnValue({
      data: mockMAData,
      isLoading: false,
      isError: false,
      error: null,
      mutate: jest.fn(),
    })

    render(<SectorAnalysisPage params={Promise.resolve({ sectorId: '1' })} />)

    // 等待页面加载
    await waitFor(() => {
      expect(screen.getByTestId('dashboard-header')).toBeInTheDocument()
    })

    // 验证标题
    expect(screen.getByText('测试板块 - 板块分析')).toBeInTheDocument()

    // 验证图表组件
    expect(screen.getByTestId('strength-chart')).toBeInTheDocument()
    expect(screen.getByTestId('ma-chart')).toBeInTheDocument()

    // 验证控制组件
    expect(screen.getByTestId('time-range-selector')).toBeInTheDocument()
    expect(screen.getByTestId('ma-toggle-controls')).toBeInTheDocument()
  })

  it('应该显示加载状态', async () => {
    // Mock hooks 返回加载状态
    ;(useSectorStrengthHistory as jest.Mock).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      mutate: jest.fn(),
    })

    ;(useSectorMAHistory as jest.Mock).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      mutate: jest.fn(),
    })

    render(<SectorAnalysisPage params={Promise.resolve({ sectorId: '1' })} />)

    await waitFor(() => {
      expect(screen.getByTestId('loading-state')).toBeInTheDocument()
    })

    expect(screen.getByText('加载板块分析数据...')).toBeInTheDocument()
  })

  it('应该显示错误状态', async () => {
    // Mock hooks 返回错误
    ;(useSectorStrengthHistory as jest.Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('API Error'),
      mutate: jest.fn(),
    })

    ;(useSectorMAHistory as jest.Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('API Error'),
      mutate: jest.fn(),
    })

    render(<SectorAnalysisPage params={Promise.resolve({ sectorId: '1' })} />)

    await waitFor(() => {
      expect(screen.getByTestId('error-state')).toBeInTheDocument()
    })

    expect(screen.getByText('加载板块分析数据失败，请稍后重试')).toBeInTheDocument()
  })

  it('应该支持时间范围切换', async () => {
    const mockSetTimeRange = jest.fn()

    ;(useChartState as jest.Mock).mockReturnValue({
      timeRange: '2m',
      visibleMAs: {
        ma5: true,
        ma10: true,
        ma20: true,
        ma30: true,
        ma60: true,
        ma90: false,
        ma120: false,
        ma240: false,
      },
      setTimeRange: mockSetTimeRange,
      toggleMA: jest.fn(),
    })

    ;(useSectorStrengthHistory as jest.Mock).mockReturnValue({
      data: mockStrengthData,
      isLoading: false,
      isError: false,
      error: null,
      mutate: jest.fn(),
    })

    ;(useSectorMAHistory as jest.Mock).mockReturnValue({
      data: mockMAData,
      isLoading: false,
      isError: false,
      error: null,
      mutate: jest.fn(),
    })

    render(<SectorAnalysisPage params={Promise.resolve({ sectorId: '1' })} />)

    await waitFor(() => {
      expect(screen.getByTestId('time-range-selector')).toBeInTheDocument()
    })

    // 点击时间范围按钮
    const monthButton = screen.getByText('1月')
    fireEvent.click(monthButton)

    expect(mockSetTimeRange).toHaveBeenCalledWith('1m')
  })

  it('应该支持均线显示切换', async () => {
    const mockToggleMA = jest.fn()

    ;(useChartState as jest.Mock).mockReturnValue({
      timeRange: '2m',
      visibleMAs: {
        ma5: true,
        ma10: true,
        ma20: true,
        ma30: true,
        ma60: true,
        ma90: false,
        ma120: false,
        ma240: false,
      },
      setTimeRange: jest.fn(),
      toggleMA: mockToggleMA,
    })

    ;(useSectorStrengthHistory as jest.Mock).mockReturnValue({
      data: mockStrengthData,
      isLoading: false,
      isError: false,
      error: null,
      mutate: jest.fn(),
    })

    ;(useSectorMAHistory as jest.Mock).mockReturnValue({
      data: mockMAData,
      isLoading: false,
      isError: false,
      error: null,
      mutate: jest.fn(),
    })

    render(<SectorAnalysisPage params={Promise.resolve({ sectorId: '1' })} />)

    await waitFor(() => {
      expect(screen.getByTestId('ma-toggle-controls')).toBeInTheDocument()
    })

    // 找到 MA5 的复选框
    const ma5Checkbox = screen.getByLabelText('ma5')
    expect(ma5Checkbox).toBeChecked()

    // 点击切换
    fireEvent.click(ma5Checkbox)

    expect(mockToggleMA).toHaveBeenCalledWith('ma5')
  })

  it('应该支持返回按钮', async () => {
    ;(useSectorStrengthHistory as jest.Mock).mockReturnValue({
      data: mockStrengthData,
      isLoading: false,
      isError: false,
      error: null,
      mutate: jest.fn(),
    })

    ;(useSectorMAHistory as jest.Mock).mockReturnValue({
      data: mockMAData,
      isLoading: false,
      isError: false,
      error: null,
      mutate: jest.fn(),
    })

    render(<SectorAnalysisPage params={Promise.resolve({ sectorId: '1' })} />)

    await waitFor(() => {
      expect(screen.getByText('返回')).toBeInTheDocument()
    })

    const backButton = screen.getByText('返回')
    fireEvent.click(backButton)

    expect(mockBack).toHaveBeenCalled()
  })

  it('应该正确处理空数据', async () => {
    const emptyData: SectorStrengthHistoryResponse = {
      sector_id: '1',
      sector_name: '测试板块',
      data: [],
    }

    ;(useSectorStrengthHistory as jest.Mock).mockReturnValue({
      data: emptyData,
      isLoading: false,
      isError: false,
      error: null,
      mutate: jest.fn(),
    })

    ;(useSectorMAHistory as jest.Mock).mockReturnValue({
      data: { ...mockMAData, data: [] },
      isLoading: false,
      isError: false,
      error: null,
      mutate: jest.fn(),
    })

    render(<SectorAnalysisPage params={Promise.resolve({ sectorId: '1' })} />)

    await waitFor(() => {
      expect(screen.getByTestId('strength-chart')).toBeInTheDocument()
    })

    // 验证显示空数据提示
    expect(screen.getByText('数据点: 0')).toBeInTheDocument()
  })
})
