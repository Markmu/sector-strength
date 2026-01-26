/**
 * 数据修复弹窗组件类型定义
 *
 * @description
 * Story 4.5: Task 1
 * DataFixDialog 组件的 Props 类型
 */

import type { DataFixResponse } from '@/types/data-fix'

/**
 * 板块信息（用于下拉选择）
 */
export interface SectorOption {
  /** 板块 ID */
  id: string
  /** 板块名称 */
  name: string
}

/**
 * DataFixDialog 组件 Props
 */
export interface DataFixDialogProps {
  /** 是否打开弹窗 */
  open: boolean
  /** 关闭弹窗回调 */
  onClose: () => void
  /** 修复完成回调 */
  onComplete?: (result: DataFixResponse['data']) => void
  /** 可用的板块列表 */
  sectors: SectorOption[]
}
