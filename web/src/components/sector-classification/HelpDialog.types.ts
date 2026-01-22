/**
 * HelpDialog 组件类型定义
 */

export interface HelpDialogProps {
  /**
   * 弹窗是否打开
   */
  open: boolean
  /**
   * 弹窗开关状态变更回调
   */
  onOpenChange: (open: boolean) => void
}
