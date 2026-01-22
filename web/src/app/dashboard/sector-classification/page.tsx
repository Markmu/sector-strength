/**
 * 板块强弱分类页面
 *
 * 显示市场板块强弱分类结果
 */

'use client'

import { useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useDispatch, useSelector } from 'react-redux'
import { DashboardLayout, DashboardHeader } from '@/components/dashboard'
import { useAuth } from '@/contexts/AuthContext'
import Loading from '@/components/ui/Loading'
import {
  ClassificationTable,
  ClassificationSkeleton,
  ClassificationError,
  UpdateTimeDisplay,
  Disclaimer,
} from '@/components/sector-classification'
import {
  fetchClassifications,
  selectClassifications,
  selectLoading,
  selectError,
  selectLastFetch,
  type RootState,
  type AppDispatch,
} from '@/store'

// 页面文本常量
const PAGE_TEXT = {
  title: '板块强弱分类',
  subtitle: '查看市场板块强弱分布',
  loading: '加载中...',
  empty: '暂无分类数据',
} as const

/**
 * 板块分类页面组件
 *
 * @description
 * - 自动获取最新的分类数据
 * - 显示加载状态（骨架屏）
 * - 显示错误状态和重试按钮
 * - 显示分类表格
 */
export default function SectorClassificationPage() {
  const router = useRouter()
  const dispatch = useDispatch<AppDispatch>()
  const { isAuthenticated, isLoading: authLoading } = useAuth()

  // 从 Redux store 获取状态
  const classifications = useSelector((state: RootState) =>
    selectClassifications(state)
  )
  const loading = useSelector((state: RootState) =>
    selectLoading(state)
  )
  const error = useSelector((state: RootState) =>
    selectError(state)
  )
  const lastFetch = useSelector((state: RootState) =>
    selectLastFetch(state)
  )

  /**
   * 获取分类数据
   */
  const fetchData = useCallback(() => {
    dispatch(fetchClassifications())
  }, [dispatch])

  // 认证保护：未登录用户重定向到登录页面
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, authLoading, router])

  // 页面挂载时自动获取数据
  useEffect(() => {
    if (isAuthenticated) {
      fetchData()
    }
  }, [isAuthenticated, fetchData])

  /**
   * 重试获取数据
   */
  const handleRetry = () => {
    fetchData()
  }

  // 认证加载中显示状态
  if (authLoading) {
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
        {/* 更新时间显示 - 仅在数据加载成功且无错误时显示 */}
        {!loading && !error && lastFetch && (
          <UpdateTimeDisplay lastFetch={lastFetch} />
        )}

        {/* 根据状态显示不同内容 */}
        {loading && classifications.length === 0 ? (
          // 加载状态：显示骨架屏
          <ClassificationSkeleton />
        ) : error ? (
          // 错误状态：显示错误提示和重试按钮
          <ClassificationError
            error={error}
            onRetry={handleRetry}
            isRetrying={loading}
          />
        ) : (
          // 成功状态：显示表格
          <ClassificationTable
            data={classifications}
            loading={loading}
            emptyText={PAGE_TEXT.empty}
          />
        )}

        {/* 免责声明 - 始终显示 */}
        <Disclaimer showSeparator={true} />
      </div>
    </DashboardLayout>
  )
}
