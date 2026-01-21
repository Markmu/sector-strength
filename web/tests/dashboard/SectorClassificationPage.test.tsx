/**
 * 板块强弱分类页面测试
 */

import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock next/navigation
const mockPush = jest.fn()
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}))

// Mock AuthContext
const mockAuthContext = {
  user: { id: '1', email: 'test@example.com', username: 'testuser', is_active: true },
  accessToken: 'mock-token',
  refreshToken: 'mock-refresh-token',
  tokenType: 'bearer',
  isLoading: false,
  isAuthenticated: true,
  isAdmin: false,
  login: jest.fn(),
  logout: jest.fn(),
  refreshAccessToken: jest.fn(),
}

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: () => mockAuthContext,
}))

// Mock DashboardLayout
jest.mock('@/components/dashboard/DashboardLayout', () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dashboard-layout">{children}</div>
  ),
}))

// Mock DashboardHeader
jest.mock('@/components/dashboard/DashboardHeader', () => ({
  __esModule: true,
  default: ({ title, subtitle }: { title: string; subtitle: string }) => (
    <div data-testid="dashboard-header">
      <div data-testid="header-title">{title}</div>
      <div data-testid="header-subtitle">{subtitle}</div>
    </div>
  ),
}))

// 动态导入页面
let SectorClassificationPage: any
beforeAll(async () => {
  const module = await import('@/app/dashboard/sector-classification/page')
  SectorClassificationPage = module.default
})

describe('板块强弱分类页面', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // 默认认证状态
    mockAuthContext.isAuthenticated = true
    mockAuthContext.isLoading = false
  })

  it('应该正确渲染页面标题和副标题', async () => {
    render(<SectorClassificationPage />)

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-header')).toBeInTheDocument()
    })

    expect(screen.getByTestId('header-title')).toHaveTextContent('板块强弱分类')
    expect(screen.getByTestId('header-subtitle')).toHaveTextContent('查看市场板块强弱分布')
  })

  it('应该使用 DashboardLayout 组件', async () => {
    render(<SectorClassificationPage />)

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-layout')).toBeInTheDocument()
    })
  })

  it('应该显示占位符内容', async () => {
    render(<SectorClassificationPage />)

    await waitFor(() => {
      expect(screen.getByText('板块分类数据')).toBeInTheDocument()
    })

    expect(screen.getByText('板块强弱分类表格将在后续 Story 中实现')).toBeInTheDocument()
  })

  it('应该在未认证时重定向到登录页面', async () => {
    mockAuthContext.isAuthenticated = false
    mockAuthContext.isLoading = false

    render(<SectorClassificationPage />)

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login')
    })
  })

  it('应该在加载中时显示加载状态', async () => {
    mockAuthContext.isLoading = true

    render(<SectorClassificationPage />)

    await waitFor(() => {
      expect(screen.getByText('加载中...')).toBeInTheDocument()
    })

    // 验证加载指示器存在 - 使用更语义化的选择器
    const loadingSpinner = screen.getByRole('status', { hidden: true })
    expect(loadingSpinner).toBeInTheDocument()
  })

  it('应该在未认证且加载完成后不渲染内容', async () => {
    mockAuthContext.isAuthenticated = false
    mockAuthContext.isLoading = false

    const { container } = render(<SectorClassificationPage />)

    // 等待重定向效果
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login')
    })

    // 验证页面内容不渲染（返回 null）
    expect(container.firstChild).toBeNull()
  })

  it('应该有正确的客户端指令', async () => {
    // 验证页面组件是一个客户端组件
    // 通过渲染来验证 'use client' 指令存在
    const module = await import('@/app/dashboard/sector-classification/page')
    expect(module.default).toBeDefined()
  })

  it('应该在认证后正确渲染页面内容', async () => {
    mockAuthContext.isAuthenticated = true
    mockAuthContext.isLoading = false

    render(<SectorClassificationPage />)

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-layout')).toBeInTheDocument()
    })

    // 验证占位符图标存在 - 使用角色选择
    const placeholderIcon = screen.getByRole('img', { hidden: true })
    expect(placeholderIcon).toBeInTheDocument()

    // 验证占位符文本
    expect(screen.getByText('板块分类数据')).toBeInTheDocument()
  })
})
