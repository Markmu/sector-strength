'use client'

import { useState } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'
import { useDataStatus } from '@/hooks/useDataStatus'
import { postFetcher } from '@/lib/fetcher'
import DataTypeCard from './DataTypeCard'
import type { DataTypeStatus } from '@/hooks/useDataStatus'

/**
 * 数据状态面板组件
 *
 * - 调用 useDataStatus() 获取状态数据
 * - 加载中：3 张骨架屏卡片
 * - 错误态：错误信息 + 重试按钮
 * - 正常态：渲染 3 张 DataTypeCard
 * - 轮询由 useDataStatus hook 内的 SWR 条件式 refreshInterval 自动管理（ADR-4）
 */
export default function DataStatusPanel() {
  const { data, isLoading, error, mutate } = useDataStatus()
  const [backfillingType, setBackfillingType] = useState<string | null>(null)

  const handleBackfill = async (type: 'history' | 'ma' | 'strength') => {
    setBackfillingType(type)
    try {
      await postFetcher(`/api/v1/admin/data/backfill/${type}`)
      mutate()
    } catch (err) {
      // 错误由 DataTypeCard 的 backfilling 状态和按钮恢复处理
      console.error('补齐请求失败:', err)
    } finally {
      setBackfillingType(null)
    }
  }

  // 加载中：骨架屏
  if (isLoading) {
    return (
      <div data-testid="data-status-panel" className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            data-testid="skeleton"
            className="border rounded-lg p-4 space-y-3 animate-pulse"
          >
            <div className="flex items-center justify-between">
              <div className="h-4 bg-gray-200 rounded w-24" />
              <div className="h-5 bg-gray-200 rounded-full w-12" />
            </div>
            <div className="h-3 bg-gray-200 rounded w-32" />
            <div className="h-3 bg-gray-200 rounded w-20" />
          </div>
        ))}
      </div>
    )
  }

  // 错误态
  if (error) {
    return (
      <div data-testid="data-status-panel">
        <div
          data-testid="error-state"
          className="border rounded-lg p-6 text-center space-y-3"
        >
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto" />
          <p className="text-sm text-red-600">
            加载数据状态失败：{(error as Error).message || '未知错误'}
          </p>
          <button
            data-testid="retry-button"
            onClick={() => mutate()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            重试
          </button>
        </div>
      </div>
    )
  }

  // 正常态：渲染 3 张卡片
  return (
    <div data-testid="data-status-panel" className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {data.map((item: DataTypeStatus) => (
        <DataTypeCard
          key={item.type}
          data={item}
          onBackfill={handleBackfill}
          backfilling={backfillingType === item.type}
        />
      ))}
    </div>
  )
}
