/**
 * 管理员监控类型定义
 *
 * @description
 * Story 4.3: 创建运行状态监控面板
 * 定义监控状态相关的类型
 */

/**
 * 计算状态枚举
 */
export type CalculationStatusType = 'normal' | 'abnormal' | 'failed'

/**
 * 缺失数据的板块信息
 */
export interface MissingSector {
  /** 板块 ID */
  sector_id: string
  /** 板块名称 */
  sector_name: string
}

/**
 * 数据完整性信息
 */
export interface DataIntegrity {
  /** 总板块数 */
  total_sectors: number
  /** 有数据的板块数 */
  sectors_with_data: number
  /** 缺失数据的板块列表 */
  missing_sectors: MissingSector[]
}

/**
 * 分类计算状态
 */
export interface CalculationStatus {
  /** 最后计算时间（ISO 8601） */
  last_calculation_time: string
  /** 计算状态 */
  calculation_status: CalculationStatusType
  /** 最近一次计算耗时（毫秒） */
  last_calculation_duration_ms: number
  /** 今日计算次数 */
  today_calculation_count: number
  /** 数据完整性信息 */
  data_integrity: DataIntegrity
}

/**
 * 监控状态响应
 */
export interface MonitoringStatusResponse {
  success: boolean
  data?: CalculationStatus
  error?: {
    code: string
    message: string
  }
}
