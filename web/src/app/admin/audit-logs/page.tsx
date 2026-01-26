'use client'

/**
 * 审计日志页面
 *
 * @description
 * 管理员查看操作审计日志的页面。
 *
 * 路由: /admin/audit-logs
 * 权限: 仅管理员可访问
 * 功能: 显示审计日志表格，支持筛选和分页
 *
 * Acceptance Criteria:
 * - 页面显示"操作审计日志"标题
 * - 显示审计日志表格（操作时间、操作人、操作类型、操作内容、IP 地址）
 * - 表格按操作时间降序排列（最新在前）
 * - 提供筛选功能（操作类型、操作人、日期范围）
 * - 支持分页（每页 20 条）
 * - 审计日志保留至少 6 个月（NFR-SEC-008）
 * - 只能管理员查看审计日志（NFR-SEC-003）
 */

import { useEffect, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { DashboardLayout } from '@/components/dashboard/DashboardLayout'
import { DashboardHeader } from '@/components/dashboard/DashboardHeader'
import { AuditLogsTable } from '@/components/admin/audit-logs/AuditLogsTable'
import { AuditLogsFilters } from '@/components/admin/audit-logs/AuditLogsFilters'
import { useAuditLogs } from '@/components/admin/audit-logs/useAuditLogs'
import { ActionType } from '@/types/audit-logs'
import type { UserOption } from '@/components/admin/audit-logs/AuditLogsFilters.types'

// 可用的操作类型列表
const AVAILABLE_ACTION_TYPES = Object.values(ActionType)

// 可用的用户列表（从实际数据获取，这里先硬编码一些示例数据）
// TODO: 后续可以从用户列表 API 获取
const AVAILABLE_USERS: UserOption[] = [
  { id: '1', username: 'admin' },
]

/**
 * 审计日志页面组件
 */
export default function AuditLogsPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading, isAdmin } = useAuth()

  const {
    logs,
    total,
    page,
    totalPages,
    loading,
    error,
    filters,
    setFilters,
    clearFilters,
    goToPage,
    nextPage,
    prevPage,
  } = useAuditLogs()

  // 未登录用户重定向到登录页面
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  // 从日志中提取唯一的用户列表（动态更新）
  const availableUsers = useMemo(() => {
    const userMap = new Map<string, string>()
    // 添加默认管理员
    AVAILABLE_USERS.forEach((u) => userMap.set(u.id, u.username))
    // 从日志中提取用户
    logs.forEach((log) => {
      userMap.set(log.user_id, log.username)
    })
    return Array.from(userMap.entries()).map(([id, username]) => ({
      id,
      username,
    }))
  }, [logs])

  // 加载中状态
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-600"></div>
        </div>
      </DashboardLayout>
    )
  }

  // 权限不足 - 非管理员用户
  if (!isAdmin) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-full min-h-[400px]">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 mb-4">
              <svg
                className="w-8 h-8 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-[#1a1a2e] mb-2">权限不足</h2>
            <p className="text-[#6c757d] mb-6">
              您没有权限访问此页面。此功能仅限管理员使用。
            </p>
            <button
              onClick={() => router.push('/dashboard')}
              className="inline-flex items-center px-4 py-2 bg-cyan-500 text-white rounded-lg hover:bg-cyan-600 transition-colors"
            >
              返回仪表板
            </button>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  // 管理员页面
  return (
    <DashboardLayout>
      <DashboardHeader
        title="操作审计日志"
        subtitle="查看系统操作历史和审计记录"
      />

      <div className="space-y-6">
        {/* 错误提示 */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* 筛选条件 */}
        <AuditLogsFilters
          filters={filters}
          onUpdateFilters={setFilters}
          onClearFilters={clearFilters}
          actionTypes={AVAILABLE_ACTION_TYPES}
          users={availableUsers}
        />

        {/* 审计日志表格 */}
        <AuditLogsTable
          logs={logs}
          loading={loading}
          currentPage={page}
          totalPages={totalPages}
          total={total}
          onNextPage={nextPage}
          onPrevPage={prevPage}
          onGoToPage={goToPage}
        />
      </div>
    </DashboardLayout>
  )
}
