/**
 * AuditLogsTable 组件类型定义
 */

import type { AuditLog } from "@/types/audit-logs"

/**
 * AuditLogsTable 组件 Props 接口
 */
export interface AuditLogsTableProps {
  /** 审计日志数据 */
  logs: AuditLog[]
  /** 加载状态 */
  loading: boolean
  /** 当前页 */
  currentPage: number
  /** 总页数 */
  totalPages: number
  /** 下一页回调 */
  onNextPage: () => void
  /** 上一页回调 */
  onPrevPage: () => void
  /** 跳转到指定页回调 */
  onGoToPage: (page: number) => void
  /** 总记录数 */
  total: number
}
