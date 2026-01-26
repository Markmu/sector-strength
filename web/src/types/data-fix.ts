/**
 * 数据修复类型定义
 *
 * @description
 * Story 4.5: 实现管理员数据修复功能
 * 定义数据修复相关的类型
 */

/**
 * 数据修复请求
 */
export interface DataFixRequest {
  /** 板块 ID（可选，与 sector_name 二选一） */
  sector_id?: string
  /** 板块名称（可选，与 sector_id 二选一） */
  sector_name?: string
  /** 时间范围（最近 N 天） */
  days: number
  /** 是否覆盖已有数据 */
  overwrite: boolean
}

/**
 * 板块修复结果
 */
export interface DataFixSectorResult {
  /** 板块 ID */
  sector_id: string
  /** 板块名称 */
  sector_name: string
  /** 是否成功 */
  success: boolean
  /** 错误信息（如果失败） */
  error?: string
}

/**
 * 数据修复响应
 */
export interface DataFixResponse {
  success: boolean
  data?: {
    /** 成功修复的板块数量 */
    success_count: number
    /** 失败的板块数量 */
    failed_count: number
    /** 修复耗时（秒） */
    duration_seconds: number
    /** 修复的板块列表 */
    sectors: DataFixSectorResult[]
  }
  error?: {
    code: string
    message: string
  }
}

/**
 * 数据修复状态枚举
 */
export enum DataFixStatus {
  /** 未开始 */
  IDLE = 'idle',
  /** 验证中 */
  VALIDATING = 'validating',
  /** 修复中 */
  FIXING = 'fixing',
  /** 成功 */
  SUCCESS = 'success',
  /** 失败 */
  ERROR = 'error',
}
