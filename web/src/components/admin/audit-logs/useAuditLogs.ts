'use client'

/**
 * useAuditLogs Hook
 *
 * @description
 * 管理审计日志数据的自定义 Hook，提供筛选、分页和刷新功能。
 *
 * Acceptance Criteria:
 * - 管理日志数据和筛选状态
 * - 实现筛选条件应用
 * - 实现分页状态管理
 */

import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/apiClient'
import type {
  AuditLog,
  AuditLogsFilters,
  AuditLogsResponse,
} from '@/types/audit-logs'
import type {
  UseAuditLogsReturn,
  UseAuditLogsConfig,
} from './useAuditLogs.types'

const AUDIT_LOGS_ENDPOINT = '/admin/audit-logs'
const DEFAULT_PAGE_SIZE = 20

/**
 * 审计日志 Hook
 *
 * 用于管理审计日志数据、筛选和分页
 *
 * @param config - Hook 配置选项
 * @returns Hook 返回值，包含日志数据和操作方法
 */
export function useAuditLogs(config: UseAuditLogsConfig = {}): UseAuditLogsReturn {
  const { pageSize = DEFAULT_PAGE_SIZE, initialPage = 1 } = config

  const [logs, setLogs] = useState<AuditLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(initialPage)
  const [totalPages, setTotalPages] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFiltersState] = useState<AuditLogsFilters>({})

  /**
   * 获取审计日志
   */
  const fetchLogs = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      })

      // 添加筛选参数
      if (filters.action_type) {
        params.append('action_type', filters.action_type)
      }
      if (filters.user_id) {
        params.append('user_id', filters.user_id)
      }
      if (filters.start_date) {
        params.append('start_date', filters.start_date)
      }
      if (filters.end_date) {
        params.append('end_date', filters.end_date)
      }

      const response = await apiClient.get<AuditLogsResponse>(
        `${AUDIT_LOGS_ENDPOINT}?${params.toString()}`
      )

      if (response.data && response.data.success && response.data.data) {
        setLogs(response.data.data.items)
        setTotal(response.data.data.total)
        setTotalPages(response.data.data.total_pages)
      } else {
        setError(response.data?.error?.message || '获取审计日志失败')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '网络错误')
    } finally {
      setLoading(false)
    }
  }, [page, filters, pageSize])

  /**
   * 设置筛选条件
   *
   * @param newFilters - 新的筛选条件
   */
  const setFilters = useCallback((newFilters: AuditLogsFilters) => {
    setFiltersState(newFilters)
    setPage(1) // 重置到第一页
  }, [])

  /**
   * 清除筛选条件
   */
  const clearFilters = useCallback(() => {
    setFiltersState({})
    setPage(1)
  }, [])

  /**
   * 跳转到指定页
   *
   * @param targetPage - 目标页码
   */
  const goToPage = useCallback((targetPage: number) => {
    if (targetPage >= 1 && targetPage <= totalPages) {
      setPage(targetPage)
    }
  }, [totalPages])

  /**
   * 下一页
   */
  const nextPage = useCallback(() => {
    if (page < totalPages) {
      setPage(page + 1)
    }
  }, [page, totalPages])

  /**
   * 上一页
   */
  const prevPage = useCallback(() => {
    if (page > 1) {
      setPage(page - 1)
    }
  }, [page])

  /**
   * 刷新数据
   */
  const refresh = useCallback(async () => {
    await fetchLogs()
  }, [fetchLogs])

  // 初始加载和筛选/分页变化时重新获取
  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  return {
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
    refresh,
  }
}
