/**
 * MonitoringStatusCard 组件测试
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { MonitoringStatusCard } from '@/components/admin/sector-classification/MonitoringStatusCard'
import type { CalculationStatus } from '@/types/admin-monitoring'

// Mock Card, Button 组件
jest.mock('@/components/ui/Card', () => {
  return {
    __esModule: true,
    Card: ({ children, className }: any) => <div className={className} data-testid="card">{children}</div>,
    CardHeader: ({ children }: any) => <div data-testid="card-header">{children}</div>,
    CardBody: ({ children }: any) => <div data-testid="card-body">{children}</div>,
  }
})

jest.mock('@/components/ui/Button', () => {
  return {
    __esModule: true,
    default: ({ children, onClick, disabled }: any) => (
      <button onClick={onClick} disabled={disabled} data-testid="refresh-button">
        {children}
      </button>
    ),
  }
})

describe('MonitoringStatusCard', () => {
  const mockStatus: CalculationStatus = {
    last_calculation_time: '2026-01-26T10:30:00Z',
    calculation_status: 'normal',
    last_calculation_duration_ms: 125,
    today_calculation_count: 5,
    data_integrity: {
      total_sectors: 15,
      sectors_with_data: 15,
      missing_sectors: []
    }
  }

  const mockOnRefresh = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('应该显示正常状态', () => {
    render(
      <MonitoringStatusCard
        status={mockStatus}
        loading={false}
        error={null}
        onRefresh={mockOnRefresh}
      />
    )

    expect(screen.getByText('运行状态监控')).toBeInTheDocument()
    expect(screen.getByText('正常')).toBeInTheDocument()
    expect(screen.getByText(/125 ms/)).toBeInTheDocument()
    expect(screen.getByText(/5 次/)).toBeInTheDocument()
  })

  it('应该显示异常状态', () => {
    const abnormalStatus: CalculationStatus = {
      ...mockStatus,
      calculation_status: 'abnormal'
    }

    render(
      <MonitoringStatusCard
        status={abnormalStatus}
        loading={false}
        error={null}
        onRefresh={mockOnRefresh}
      />
    )

    expect(screen.getByText('异常')).toBeInTheDocument()
  })

  it('应该显示失败状态', () => {
    const failedStatus: CalculationStatus = {
      ...mockStatus,
      calculation_status: 'failed'
    }

    render(
      <MonitoringStatusCard
        status={failedStatus}
        loading={false}
        error={null}
        onRefresh={mockOnRefresh}
      />
    )

    expect(screen.getByText('失败')).toBeInTheDocument()
  })

  it('应该显示错误状态', () => {
    render(
      <MonitoringStatusCard
        status={null}
        loading={false}
        error="获取状态失败"
        onRefresh={mockOnRefresh}
      />
    )

    expect(screen.getByText('获取状态失败')).toBeInTheDocument()
  })

  it('应该显示加载中状态', () => {
    render(
      <MonitoringStatusCard
        status={null}
        loading={true}
        error={null}
        onRefresh={mockOnRefresh}
      />
    )

    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('点击刷新按钮应该调用 onRefresh', () => {
    render(
      <MonitoringStatusCard
        status={mockStatus}
        loading={false}
        error={null}
        onRefresh={mockOnRefresh}
      />
    )

    const refreshButton = screen.getByTestId('refresh-button')
    fireEvent.click(refreshButton)

    expect(mockOnRefresh).toHaveBeenCalledTimes(1)
  })

  it('加载中时刷新按钮应该禁用', () => {
    render(
      <MonitoringStatusCard
        status={null}
        loading={true}
        error={null}
        onRefresh={mockOnRefresh}
      />
    )

    const refreshButton = screen.getByTestId('refresh-button')
    expect(refreshButton).toBeDisabled()
  })

  it('应该正确格式化时间', () => {
    render(
      <MonitoringStatusCard
        status={mockStatus}
        loading={false}
        error={null}
        onRefresh={mockOnRefresh}
      />
    )

    // 应该包含格式化的日期时间
    expect(screen.getByText(/2026/)).toBeInTheDocument()
    expect(screen.getByText(/01/)).toBeInTheDocument()
    expect(screen.getByText(/26/)).toBeInTheDocument()
  })
})
