/**
 * AuditLogsFilters 组件类型定义
 */

import type { AuditLogsFilters } from "@/types/audit-logs"
import type { ActionType } from "@/types/audit-logs"

/**
 * 用户选项接口
 */
export interface UserOption {
  id: string
  username: string
}

/**
 * AuditLogsFilters 组件 Props 接口
 */
export interface AuditLogsFiltersProps {
  /** 筛选条件 */
  filters: AuditLogsFilters
  /** 更新筛选条件回调 */
  onUpdateFilters: (filters: AuditLogsFilters) => void
  /** 清除筛选条件回调 */
  onClearFilters: () => void
  /** 可用的操作类型列表 */
  actionTypes: ActionType[]
  /** 可用的用户列表 */
  users: UserOption[]
}
