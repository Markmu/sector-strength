/**
 * useAuditLogs Hook 类型定义
 */

import type { AuditLog, AuditLogsFilters } from "@/types/audit-logs"

/**
 * useAuditLogs Hook 返回值接口
 */
export interface UseAuditLogsReturn {
  /** 审计日志数据 */
  logs: AuditLog[]
  /** 总记录数 */
  total: number
  /** 当前页 */
  page: number
  /** 总页数 */
  totalPages: number
  /** 加载状态 */
  loading: boolean
  /** 错误信息 */
  error: string | null
  /** 筛选条件 */
  filters: AuditLogsFilters
  /** 设置筛选条件 */
  setFilters: (filters: AuditLogsFilters) => void
  /** 清除筛选条件 */
  clearFilters: () => void
  /** 跳转到指定页 */
  goToPage: (page: number) => void
  /** 下一页 */
  nextPage: () => void
  /** 上一页 */
  prevPage: () => void
  /** 刷新数据 */
  refresh: () => Promise<void>
}

/**
 * useAuditLogs Hook 配置接口
 */
export interface UseAuditLogsConfig {
  /** 每页大小 */
  pageSize?: number
  /** 初始页码 */
  initialPage?: number
}
