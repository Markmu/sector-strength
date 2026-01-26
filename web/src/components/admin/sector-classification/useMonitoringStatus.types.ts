import type { CalculationStatus } from '@/types/admin-monitoring'

/**
 * useMonitoringStatus Hook 类型定义
 *
 * @description
 * Hook 返回值类型
 */
export interface UseMonitoringStatusReturn {
  /** 监控状态数据 */
  status: CalculationStatus | null
  /** 加载状态 */
  loading: boolean
  /** 错误信息 */
  error: string | null
  /** 刷新状态函数 */
  refresh: () => Promise<void>
}
