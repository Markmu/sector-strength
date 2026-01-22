/**
 * 刷新按钮组件
 *
 * 用于手动刷新板块分类数据
 */

'use client'

import { memo, useCallback } from 'react'
import { RefreshCw } from 'lucide-react'
import { useDispatch, useSelector } from 'react-redux'
import { cn } from '@/lib/utils'
import Button from '@/components/ui/Button'
import { fetchClassifications, selectLoading } from '@/store'
import type { RootState, AppDispatch } from '@/store'

export interface RefreshButtonProps {
  /** 自定义类名 */
  className?: string
  /** 是否显示标签文本 */
  showLabel?: boolean
}

const DEFAULT_LABEL = '刷新'

/**
 * 刷新按钮组件
 *
 * @description
 * - 点击按钮触发数据刷新
 * - loading 状态时按钮禁用
 * - loading 状态时图标旋转
 * - 成功后数据自动更新（通过 Redux store）
 * - 失败后按钮恢复可重试
 */
export const RefreshButton = memo(function RefreshButton({
  className = '',
  showLabel = true,
}: RefreshButtonProps) {
  const dispatch = useDispatch<AppDispatch>()

  // 从 Redux store 获取 loading 状态
  const loading = useSelector((state: RootState) => selectLoading(state))

  /**
   * 处理刷新点击
   */
  const handleRefresh = useCallback(() => {
    dispatch(fetchClassifications())
  }, [dispatch])

  return (
    <Button
      onClick={handleRefresh}
      disabled={loading}
      variant="outline"
      size="sm"
      className={cn('gap-2', className)}
      aria-label="刷新数据"
      aria-busy={loading}
    >
      <RefreshCw
        className={cn('w-4 h-4', loading && 'animate-spin')}
        aria-hidden="true"
      />
      {showLabel && <span>{DEFAULT_LABEL}</span>}
    </Button>
  )
})
