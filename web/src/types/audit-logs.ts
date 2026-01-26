/**
 * 审计日志类型定义
 *
 * @description
 * 定义操作审计日志相关的类型，用于管理员查看系统操作历史。
 * 满足 NFR-SEC-006, NFR-SEC-007, NFR-SEC-008 要求。
 */

/**
 * 操作类型枚举
 *
 * 定义系统支持的所有操作类型
 */
export enum ActionType {
  /** 测试分类算法 */
  TEST_CLASSIFICATION = "test_classification",
  /** 测试分类结果 */
  TEST_CLASSIFICATION_RESULT = "test_classification_result",
  /** 查看配置 */
  VIEW_CONFIG = "view_config",
  /** 修改配置 */
  UPDATE_CONFIG = "update_config",
  /** 查看运行状态 */
  VIEW_STATUS = "view_status",
  /** 查看审计日志 */
  VIEW_AUDIT_LOGS = "view_audit_logs",
  /** 修复数据 */
  FIX_DATA = "fix_data",
}

/**
 * 审计日志接口
 *
 * 单条审计日志记录
 */
export interface AuditLog {
  /** 日志 ID */
  id: string
  /** 操作类型 */
  action_type: ActionType
  /** 操作详情（纯文本格式） */
  action_details: string
  /** 用户 ID */
  user_id: string
  /** 用户名 */
  username: string
  /** IP 地址 */
  ip_address: string
  /** 操作时间（ISO 8601 格式） */
  created_at: string
  /** 关联的资源类型 */
  resource_type?: string
  /** 关联的资源 ID */
  resource_id?: string
  /** 操作状态 */
  status?: "success" | "failed" | "partial"
}

/**
 * 审计日志筛选条件接口
 */
export interface AuditLogsFilters {
  /** 操作类型筛选 */
  action_type?: ActionType
  /** 操作人 ID 筛选 */
  user_id?: string
  /** 开始日期（ISO 8601 格式） */
  start_date?: string
  /** 结束日期（ISO 8601 格式） */
  end_date?: string
}

/**
 * 审计日志分页接口
 */
export interface AuditLogsPagination {
  /** 当前页 */
  page: number
  /** 每页大小 */
  page_size: number
}

/**
 * 审计日志响应接口
 */
export interface AuditLogsResponse {
  success: boolean
  data?: {
    /** 审计日志列表 */
    items: AuditLog[]
    /** 总记录数 */
    total: number
    /** 当前页 */
    page: number
    /** 每页大小 */
    page_size: number
    /** 总页数 */
    total_pages: number
  }
  error?: {
    code: string
    message: string
  }
}

/**
 * 操作类型显示名称映射
 */
export const ACTION_TYPE_NAMES: Record<ActionType, string> = {
  [ActionType.TEST_CLASSIFICATION]: "测试分类",
  [ActionType.TEST_CLASSIFICATION_RESULT]: "测试结果",
  [ActionType.VIEW_CONFIG]: "查看配置",
  [ActionType.UPDATE_CONFIG]: "修改配置",
  [ActionType.VIEW_STATUS]: "查看状态",
  [ActionType.VIEW_AUDIT_LOGS]: "查看日志",
  [ActionType.FIX_DATA]: "修复数据",
}

/**
 * 操作类型颜色映射
 *
 * 用于 UI 中显示不同颜色的标签
 */
export const ACTION_TYPE_COLORS: Record<ActionType, string> = {
  [ActionType.TEST_CLASSIFICATION]: "bg-blue-100 text-blue-700",
  [ActionType.TEST_CLASSIFICATION_RESULT]: "bg-green-100 text-green-700",
  [ActionType.VIEW_CONFIG]: "bg-gray-100 text-gray-700",
  [ActionType.UPDATE_CONFIG]: "bg-amber-100 text-amber-700",
  [ActionType.VIEW_STATUS]: "bg-cyan-100 text-cyan-700",
  [ActionType.VIEW_AUDIT_LOGS]: "bg-purple-100 text-purple-700",
  [ActionType.FIX_DATA]: "bg-red-100 text-red-700",
}
