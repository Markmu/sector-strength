'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { adminApi } from '@/lib/api'
import type {
  CalculationStatus,
} from '@/types/admin-monitoring'
import type { UseMonitoringStatusReturn } from './useMonitoringStatus.types'

const POLL_INTERVAL = 30000 // 30 秒

/**
 * useMonitoringStatus Hook
 *
 * @description
 * 管理监控状态的数据和自动刷新：
 * - 初始加载状态数据
 * - 每 30 秒自动轮询状态
 * - 提供手动刷新功能
 * - 组件卸载时清除定时器
 *
 * @returns 监控状态和控制函数
 */
export function useMonitoringStatus(): UseMonitoringStatusReturn {
  const [status, setStatus] = useState<CalculationStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 使用 ref 存储 timer，避免闭包问题
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      const response = await adminApi.getMonitoringStatus()

      if (response.data) {
        setStatus(response.data)
        setError(null)
      } else {
        setError('获取状态失败')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '网络错误')
    } finally {
      setLoading(false)
    }
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    await fetchStatus()
  }, [fetchStatus])

  // 设置自动轮询（仅设置一次，避免依赖 fetchStatus 导致的重新创建）
  useEffect(() => {
    // 清理之前的定时器
    if (timerRef.current) {
      clearInterval(timerRef.current)
    }

    timerRef.current = setInterval(() => {
      // 直接调用 API，避免依赖 fetchStatus
      adminApi.getMonitoringStatus()
        .then((response) => {
          if (response.data) {
            setStatus(response.data)
            setError(null)
          } else {
            setError('获取状态失败')
          }
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : '网络错误')
        })
        .finally(() => {
          setLoading(false)
        })
    }, POLL_INTERVAL)

    // 清理定时器
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
  }, []) // 空依赖数组，只在组件挂载时设置一次

  // 初始加载
  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  return {
    status,
    loading,
    error,
    refresh,
  }
}
