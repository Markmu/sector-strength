/**
 * 数据修复 Hook 类型定义
 *
 * @description
 * Story 4.5: Task 3
 * useDataFix Hook 的返回类型
 */

import type { DataFixRequest, DataFixResponse, DataFixStatus as FixStatus } from '@/types/data-fix'

/**
 * useDataFix Hook 返回类型
 */
export interface UseDataFixReturn {
  /** 修复状态 */
  status: FixStatus
  /** 修复结果 */
  result: DataFixResponse['data'] | null
  /** 错误信息 */
  error: string | null
  /** 是否正在修复 */
  isFixing: boolean
  /** 执行修复 */
  fix: (request: DataFixRequest) => Promise<void>
  /** 重置状态 */
  reset: () => void
}
