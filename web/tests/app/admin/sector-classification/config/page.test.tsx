/**
 * AdminConfigPage 测试
 *
 * 测试管理员配置页面的权限控制和功能
 */

import { render, screen, waitFor } from '@testing-library/react'
import { useRouter } from 'next/navigation'
import AdminConfigPage from '@/app/admin/sector-classification/config/page'

// Mock dependencies
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}))

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}))

describe('AdminConfigPage - 权限控制', () => {
  const mockPush = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
    })
  })

  it('管理员用户应该能够访问页面', async () => {
    const { useAuth } = require('@/contexts/AuthContext')
    useAuth.mockReturnValue({
      user: { id: '1', username: 'admin', email: 'admin@test.com', role: 'admin' },
      isAuthenticated: true,
      isLoading: false,
      isAdmin: true,
    })

    render(<AdminConfigPage />)

    await waitFor(() => {
      expect(screen.getByText('分类参数配置')).toBeInTheDocument()
      expect(screen.getByText('均线周期配置')).toBeInTheDocument()
    })
  })

  it('普通用户不应该能够访问页面 - 应显示权限不足', async () => {
    const { useAuth } = require('@/contexts/AuthContext')
    useAuth.mockReturnValue({
      user: { id: '2', username: 'user', email: 'user@test.com', role: 'user' },
      isAuthenticated: true,
      isLoading: false,
      isAdmin: false,
    })

    render(<AdminConfigPage />)

    await waitFor(() => {
      expect(screen.getByText('权限不足')).toBeInTheDocument()
      expect(screen.getByText(/您没有权限访问此页面/)).toBeInTheDocument()
    })
  })

  it('未登录用户应该被重定向到登录页面', async () => {
    const { useAuth } = require('@/contexts/AuthContext')
    useAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      isAdmin: false,
    })

    render(<AdminConfigPage />)

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login')
    })
  })

  it('加载中状态应该显示加载动画', async () => {
    const { useAuth } = require('@/contexts/AuthContext')
    useAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      isAdmin: false,
    })

    render(<AdminConfigPage />)

    await waitFor(() => {
      const loader = document.querySelector('.animate-spin')
      expect(loader).toBeInTheDocument()
    })
  })
})

describe('AdminConfigPage - 配置展示', () => {
  beforeEach(() => {
    const { useAuth } = require('@/contexts/AuthContext')
    useAuth.mockReturnValue({
      user: { id: '1', username: 'admin', email: 'admin@test.com', role: 'admin' },
      isAuthenticated: true,
      isLoading: false,
      isAdmin: true,
    })
  })

  it('应该显示所有配置卡片', async () => {
    render(<AdminConfigPage />)

    await waitFor(() => {
      expect(screen.getByText('均线周期配置')).toBeInTheDocument()
      expect(screen.getByText('判断基准天数')).toBeInTheDocument()
      expect(screen.getByText('分类数量')).toBeInTheDocument()
      expect(screen.getByText('分类级别定义')).toBeInTheDocument()
    })
  })

  it('应该显示所有均线周期', async () => {
    render(<AdminConfigPage />)

    await waitFor(() => {
      expect(screen.getByText('5 日线')).toBeInTheDocument()
      expect(screen.getByText('10 日线')).toBeInTheDocument()
      expect(screen.getByText('20 日线')).toBeInTheDocument()
      expect(screen.getByText('30 日线')).toBeInTheDocument()
      expect(screen.getByText('60 日线')).toBeInTheDocument()
      expect(screen.getByText('90 日线')).toBeInTheDocument()
      expect(screen.getByText('120 日线')).toBeInTheDocument()
      expect(screen.getByText('240 日线')).toBeInTheDocument()
    })
  })

  it('应该显示判断基准天数和分类数量', async () => {
    render(<AdminConfigPage />)

    await waitFor(() => {
      expect(screen.getByText('5 天')).toBeInTheDocument()
      expect(screen.getByText('9 类')).toBeInTheDocument()
    })
  })
})
