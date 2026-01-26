import type { DataIntegrity } from '@/types/admin-monitoring'

/**
 * DataIntegrityCard 组件 Props
 */
export interface DataIntegrityCardProps {
  /** 数据完整性信息 */
  dataIntegrity: DataIntegrity | null
  /** 加载状态 */
  loading: boolean
}
