/**
 * 数据修复状态显示组件类型定义
 *
 * @description
 * Story 4.5: Task 2
 * DataFixStatus 组件的 Props 类型
 */

import type { DataFixResponse } from '@/types/data-fix'
import type { DataFixStatus as FixStatus } from '@/types/data-fix'

/**
 * DataFixStatus 组件 Props
 */
export interface DataFixStatusProps {
  /** 修复状态 */
  status: FixStatus
  /** 修复结果 */
  result: DataFixResponse['data'] | null
  /** 错误信息 */
  error: string | null
}
