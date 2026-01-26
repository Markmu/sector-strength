'use client'

import { useEffect, useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { DashboardLayout } from '@/components/dashboard/DashboardLayout'
import { DashboardHeader } from '@/components/dashboard/DashboardHeader'
import { MonitoringStatusCard } from '@/components/admin/sector-classification/MonitoringStatusCard'
import { DataIntegrityCard } from '@/components/admin/sector-classification/DataIntegrityCard'
import { DataFixDialog } from '@/components/admin/sector-classification/DataFixDialog'
import { DataFixStatus } from '@/components/admin/sector-classification/DataFixStatus'
import { useMonitoringStatus } from '@/components/admin/sector-classification/useMonitoringStatus'
import { useDataFix } from '@/components/admin/sector-classification/useDataFix'
import { Button } from '@/components/ui/Button'
import { Play, Wrench } from 'lucide-react'
import type { DataFixRequest } from '@/types/data-fix'
import { DataFixStatus as FixStatus } from '@/types/data-fix'

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

  // 数据修复相关状态
  const [fixDialogOpen, setFixDialogOpen] = useState(false)
  const [fixRequest, setFixRequest] = useState<DataFixRequest | null>(null)
  const { fixStatus, fixResult, fixError, isFixing, fix, reset: resetFix } = useDataFix()

  // 从监控状态提取可用板块列表（用于修复弹窗）
  const availableSectors = useMemo(() => {
    if (!status?.data_integrity) return []

    // 合并已有数据的板块和缺失的板块，返回所有板块
    const allSectors = [
      ...(status.data_integrity.missing_sectors || []).map(s => ({
        id: s.sector_id,
        name: s.sector_name
      })),
    ]

    // 去重
    const uniqueSectors = Array.from(
      new Map(allSectors.map(s => [s.id, s])).values()
    )

    return uniqueSectors
  }, [status])

  // 执行修复
  const handleFix = async (request: DataFixRequest) => {
    setFixRequest(request)
    await fix(request)
  }

  // 监听修复状态变化
  useEffect(() => {
    if (fixStatus === FixStatus.SUCCESS && fixRequest) {
      // 修复完成后刷新监控状态
      refresh()
      // 延迟关闭弹窗和重置状态，让用户看到成功消息
      setTimeout(() => {
        setFixDialogOpen(false)
        resetFix()
        setFixRequest(null)
      }, 3000)
    }
  }, [fixStatus, fixRequest, refresh, resetFix])

  // 重置修复状态并关闭弹窗
  const handleCloseFixDialog = () => {
    setFixDialogOpen(false)
    resetFix()
    setFixRequest(null)
  }

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

        {/* 数据修复状态 */}
        {fixStatus !== FixStatus.IDLE && (
          <DataFixStatus
            status={fixStatus}
            result={fixResult}
            error={fixError}
          />
        )}

        {/* 操作按钮 */}
        <div className="flex justify-end gap-3">
          <Button
            onClick={() => setFixDialogOpen(true)}
            variant="outline"
            className="inline-flex items-center gap-2"
            disabled={isFixing}
          >
            <Wrench className="w-4 h-4" />
            <span>数据修复</span>
          </Button>
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

      {/* 数据修复弹窗 */}
      <DataFixDialog
        open={fixDialogOpen}
        onClose={handleCloseFixDialog}
        onComplete={handleFix}
        sectors={availableSectors}
      />
    </DashboardLayout>
  )
}
