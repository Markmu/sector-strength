/**
 * AuditLogsFilters 组件测试
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { AuditLogsFilters } from '@/components/admin/audit-logs/AuditLogsFilters'
import { ActionType } from '@/types/audit-logs'
import type { AuditLogsFilters as AuditLogsFiltersType } from '@/types/audit-logs'

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
  X: () => <span data-testid="x-icon" />,
}))

describe('AuditLogsFilters', () => {
  const mockFilters: AuditLogsFiltersType = {}
  const mockOnUpdateFilters = jest.fn()
  const mockOnClearFilters = jest.fn()
  const mockActionTypes = Object.values(ActionType)
  const mockUsers = [
    { id: '1', username: 'admin' },
    { id: '2', username: 'user1' },
  ]

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('应该渲染筛选条件表单', () => {
    render(
      <AuditLogsFilters
        filters={mockFilters}
        onUpdateFilters={mockOnUpdateFilters}
        onClearFilters={mockOnClearFilters}
        actionTypes={mockActionTypes}
        users={mockUsers}
      />
    )

    expect(screen.getByText('筛选条件')).toBeInTheDocument()
    expect(screen.getByText('操作类型')).toBeInTheDocument()
    expect(screen.getByText('操作人')).toBeInTheDocument()
    expect(screen.getByText('开始日期')).toBeInTheDocument()
    expect(screen.getByText('结束日期')).toBeInTheDocument()
  })

  it('应该显示操作类型选项', () => {
    render(
      <AuditLogsFilters
        filters={mockFilters}
        onUpdateFilters={mockOnUpdateFilters}
        onClearFilters={mockOnClearFilters}
        actionTypes={mockActionTypes}
        users={mockUsers}
      />
    )

    // 检查是否有"全部"选项
    const selectElement = screen.getByLabelText('操作类型') || screen.getAllByRole('combobox')[0]
    expect(selectElement).toBeInTheDocument()
  })

  it('应该显示用户选项', () => {
    render(
      <AuditLogsFilters
        filters={mockFilters}
        onUpdateFilters={mockOnUpdateFilters}
        onClearFilters={mockOnClearFilters}
        actionTypes={mockActionTypes}
        users={mockUsers}
      />
    )

    // 检查是否有"全部"选项
    const selectElement = screen.getByLabelText('操作人') || screen.getAllByRole('combobox')[1]
    expect(selectElement).toBeInTheDocument()
  })

  it('应该有激活筛选条件时显示清除按钮', () => {
    const activeFilters: AuditLogsFiltersType = {
      action_type: ActionType.TEST_CLASSIFICATION,
    }

    render(
      <AuditLogsFilters
        filters={activeFilters}
        onUpdateFilters={mockOnUpdateFilters}
        onClearFilters={mockOnClearFilters}
        actionTypes={mockActionTypes}
        users={mockUsers}
      />
    )

    expect(screen.getByText('清除筛选')).toBeInTheDocument()
  })

  it('应该没有激活筛选条件时不显示清除按钮', () => {
    render(
      <AuditLogsFilters
        filters={mockFilters}
        onUpdateFilters={mockOnUpdateFilters}
        onClearFilters={mockOnClearFilters}
        actionTypes={mockActionTypes}
        users={mockUsers}
      />
    )

    expect(screen.queryByText('清除筛选')).not.toBeInTheDocument()
  })

  it('点击清除按钮应该调用 onClearFilters', () => {
    const activeFilters: AuditLogsFiltersType = {
      action_type: ActionType.TEST_CLASSIFICATION,
    }

    render(
      <AuditLogsFilters
        filters={activeFilters}
        onUpdateFilters={mockOnUpdateFilters}
        onClearFilters={mockOnClearFilters}
        actionTypes={mockActionTypes}
        users={mockUsers}
      />
    )

    const clearButton = screen.getByText('清除筛选')
    fireEvent.click(clearButton)

    expect(mockOnClearFilters).toHaveBeenCalledTimes(1)
  })
})
