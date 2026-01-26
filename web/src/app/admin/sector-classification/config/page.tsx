'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { DashboardLayout } from '@/components/dashboard/DashboardLayout'
import { DashboardHeader } from '@/components/dashboard/DashboardHeader'
import { AdminConfigDisplay } from '@/components/admin/sector-classification/AdminConfigDisplay'
import { CLASSIFICATION_CONFIG } from '@/types/admin-config'
import { useAuth } from '@/contexts/AuthContext'

/**
 * 管理员分类参数配置页面
 *
 * @description
 * 路由: /admin/sector-classification/config
 * 权限: 仅管理员可访问
 * 功能: 显示分类参数配置（只读）
 *
 * Acceptance Criteria:
 * - 页面显示"分类参数配置"标题
 * - 显示均线周期、判断基准天数、分类数量
 * - 显示分类级别定义（第 9 类到第 1 类）
 * - 参数显示在卡片组件中
 * - 仅管理员可访问（NFR-SEC-002, NFR-SEC-003）
 */
export default function AdminConfigPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading, isAdmin } = useAuth()

  // 未登录用户重定向到登录页面
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
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500"></div>
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
            <p className="text-[#6c757d] mb-6">您没有权限访问此页面。此功能仅限管理员使用。</p>
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
        title="分类参数配置"
        subtitle="查看和确认板块强弱分类的系统参数"
      />

      <div className="space-y-6">
        <AdminConfigDisplay config={CLASSIFICATION_CONFIG} />
      </div>
    </DashboardLayout>
  )
}
