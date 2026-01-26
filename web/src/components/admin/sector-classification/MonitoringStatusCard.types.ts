import type { CalculationStatus } from '@/types/admin-monitoring'

/**
 * MonitoringStatusCard 组件 Props
 */
export interface MonitoringStatusCardProps {
  /** 监控状态数据 */
  status: CalculationStatus | null
  /** 加载状态 */
  loading: boolean
  /** 错误信息 */
  error: string | null
  /** 刷新回调 */
  onRefresh: () => void
}
