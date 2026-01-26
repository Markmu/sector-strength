/**
 * AuditLogsTable 组件测试
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { AuditLogsTable } from '@/components/admin/audit-logs/AuditLogsTable'
import { ActionType } from '@/types/audit-logs'

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
      <button onClick={onClick} disabled={disabled} data-testid="button">
        {children}
      </button>
    ),
  }
})

// Mock lucide-react 图标
jest.mock('lucide-react', () => ({
  ChevronLeft: () => <span data-testid="chevron-left" />,
  ChevronRight: () => <span data-testid="chevron-right" />,
  ChevronsLeft: () => <span data-testid="chevrons-left" />,
  ChevronsRight: () => <span data-testid="chevrons-right" />,
  Eye: () => <span data-testid="eye" />,
  EyeOff: () => <span data-testid="eye-off" />,
}))

describe('AuditLogsTable', () => {
  const mockLogs = [
    {
      id: '1',
      action_type: ActionType.TEST_CLASSIFICATION,
      action_details: '测试完成：成功15个，失败0个，耗时125ms',
      user_id: 'user-1',
      username: 'admin',
      ip_address: '192.168.1.100',
      created_at: '2026-01-27T10:30:00Z',
    },
    {
      id: '2',
      action_type: ActionType.VIEW_CONFIG,
      action_details: '查看分类参数配置',
      user_id: 'user-1',
      username: 'admin',
      ip_address: '192.168.1.100',
      created_at: '2026-01-27T09:15:00Z',
    },
  ]

  const mockOnNextPage = jest.fn()
  const mockOnPrevPage = jest.fn()
  const mockOnGoToPage = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('应该渲染审计日志表格', () => {
    render(
      <AuditLogsTable
        logs={mockLogs}
        loading={false}
        currentPage={1}
        totalPages={5}
        total={100}
        onNextPage={mockOnNextPage}
        onPrevPage={mockOnPrevPage}
        onGoToPage={mockOnGoToPage}
      />
    )

    expect(screen.getByText('审计日志列表')).toBeInTheDocument()
    expect(screen.getByText('admin')).toBeInTheDocument()
    expect(screen.getByText(/测试完成/)).toBeInTheDocument()
    expect(screen.getByText('共 100 条记录，当前第 1/5 页')).toBeInTheDocument()
  })

  it('应该显示操作类型标签', () => {
    render(
      <AuditLogsTable
        logs={mockLogs}
        loading={false}
        currentPage={1}
        totalPages={1}
        total={2}
        onNextPage={mockOnNextPage}
        onPrevPage={mockOnPrevPage}
        onGoToPage={mockOnGoToPage}
      />
    )

    expect(screen.getByText('测试分类')).toBeInTheDocument()
    expect(screen.getByText('查看配置')).toBeInTheDocument()
  })

  it('应该支持展开/收起长文本', () => {
    const longTextLog = {
      ...mockLogs[0],
      action_details: 'A'.repeat(100),
    }

    render(
      <AuditLogsTable
        logs={[longTextLog]}
        loading={false}
        currentPage={1}
        totalPages={1}
        total={1}
        onNextPage={mockOnNextPage}
        onPrevPage={mockOnPrevPage}
        onGoToPage={mockOnGoToPage}
      />
    )

    const expandButton = screen.getByText('展开')
    fireEvent.click(expandButton)

    expect(screen.getByText('收起')).toBeInTheDocument()
  })

  it('应该支持分页', () => {
    render(
      <AuditLogsTable
        logs={mockLogs}
        loading={false}
        currentPage={2}
        totalPages={5}
        total={100}
        onNextPage={mockOnNextPage}
        onPrevPage={mockOnPrevPage}
        onGoToPage={mockOnGoToPage}
      />
    )

    const nextButton = screen.getAllByText('下一页')[0]
    fireEvent.click(nextButton)

    expect(mockOnNextPage).toHaveBeenCalledTimes(1)
  })

  it('应该显示加载中状态', () => {
    render(
      <AuditLogsTable
        logs={[]}
        loading={true}
        currentPage={1}
        totalPages={1}
        total={0}
        onNextPage={mockOnNextPage}
        onPrevPage={mockOnPrevPage}
        onGoToPage={mockOnGoToPage}
      />
    )

    expect(screen.getByTestId('card-body').querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('应该显示空数据状态', () => {
    render(
      <AuditLogsTable
        logs={[]}
        loading={false}
        currentPage={1}
        totalPages={1}
        total={0}
        onNextPage={mockOnNextPage}
        onPrevPage={mockOnPrevPage}
        onGoToPage={mockOnGoToPage}
      />
    )

    expect(screen.getByText('暂无审计日志')).toBeInTheDocument()
  })

  it('应该正确格式化时间', () => {
    render(
      <AuditLogsTable
        logs={mockLogs}
        loading={false}
        currentPage={1}
        totalPages={1}
        total={2}
        onNextPage={mockOnNextPage}
        onPrevPage={mockOnPrevPage}
        onGoToPage={mockOnGoToPage}
      />
    )

    // 应该包含格式化的日期时间
    expect(screen.getByText(/2026/)).toBeInTheDocument()
    expect(screen.getByText(/01/)).toBeInTheDocument()
    expect(screen.getByText(/27/)).toBeInTheDocument()
  })
})
