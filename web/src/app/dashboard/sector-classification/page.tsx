/**
 * 板块强弱分类页面
 *
 * 显示市场板块强弱分类结果
 */

'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { DashboardLayout, DashboardHeader } from '@/components/dashboard'
import { useAuth } from '@/contexts/AuthContext'
import Loading from '@/components/ui/Loading'

// 页面文本常量
const PAGE_TEXT = {
  title: '板块强弱分类',
  subtitle: '查看市场板块强弱分布',
  placeholder: {
    title: '板块分类数据',
    description: '板块强弱分类表格将在后续 Story 中实现',
  },
  loading: '加载中...',
} as const
  const router = useRouter()
  const { isAuthenticated, isLoading } = useAuth()

  // 认证保护：未登录用户重定向到登录页面
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  // 加载中显示状态
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[400px]" role="status" aria-live="polite">
          <Loading size="lg" text={PAGE_TEXT.loading} />
        </div>
      </DashboardLayout>
    )
  }

  // 未认证时不渲染内容（等待重定向）
  if (!isAuthenticated) {
    return null
  }

  return (
    <DashboardLayout>
      <DashboardHeader
        title={PAGE_TEXT.title}
        subtitle={PAGE_TEXT.subtitle}
      />

      <div className="space-y-6">
        {/* 占位符内容 - 用于后续 Story 实现 */}
        <div className="bg-white rounded-xl border border-[#e9ecef] shadow-sm p-8">
          <div className="text-center py-12">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-cyan-50 mb-4">
              <svg className="w-8 h-8 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" role="img" aria-label="图表图标">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{PAGE_TEXT.placeholder.title}</h3>
            <p className="text-sm text-gray-500">{PAGE_TEXT.placeholder.description}</p>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
