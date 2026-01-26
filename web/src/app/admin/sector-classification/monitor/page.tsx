'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { DashboardLayout } from '@/components/dashboard/DashboardLayout'
import { DashboardHeader } from '@/components/dashboard/DashboardHeader'
import { MonitoringStatusCard } from '@/components/admin/sector-classification/MonitoringStatusCard'
import { DataIntegrityCard } from '@/components/admin/sector-classification/DataIntegrityCard'
import { useMonitoringStatus } from '@/components/admin/sector-classification/useMonitoringStatus'
import { Button } from '@/components/ui/Button'
import { Play } from 'lucide-react'

/**
 * 管理员分类运行状态监控页面
 *
 * @description
 * 路由: /admin/sector-classification/monitor
 * 权限: 仅管理员可访问
 * 功能: 显示分类计算的运行状态和数据完整性
 *
 * Acceptance Criteria:
 * - 页面显示"分类运行状态监控"标题
 * - 显示最后计算时间、计算状态、耗时、今日计算次数
 * - 显示数据完整性信息
 * - 提供立即测试按钮
 * - 页面每 30 秒自动刷新状态
 * - 仅管理员可访问（NFR-SEC-002, NFR-SEC-003）
 */
export function MonitoringPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading, isAdmin } = useAuth()
  const { status, loading, error, refresh } = useMonitoringStatus()

  // 检查管理员权限
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  // 加载中
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
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
            <h2 className="text-2xl font-semibold text-[#1a1a2e] mb-2">
              权限不足
            </h2>
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
        title="分类运行状态监控"
        subtitle="实时监控板块分类计算的运行状态和数据完整性"
      />

      <div className="space-y-6">
        {/* 运行状态卡片 */}
        <MonitoringStatusCard
          status={status}
          loading={loading}
          error={error}
          onRefresh={refresh}
        />

        {/* 数据完整性卡片 */}
        {status && (
          <DataIntegrityCard
            dataIntegrity={status.data_integrity}
            loading={loading}
          />
        )}

        {/* 立即测试按钮 */}
        <div className="flex justify-end">
          <Button
            onClick={() => router.push('/admin/sector-classification/config')}
            variant="primary"
            className="inline-flex items-center gap-2"
          >
            <Play className="w-4 h-4" />
            <span>立即测试分类算法</span>
          </Button>
        </div>
      </div>
    </DashboardLayout>
  )
}
