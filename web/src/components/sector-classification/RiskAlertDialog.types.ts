export interface RiskAlertDialogProps {
  /**
   * 弹窗是否打开
   */
  open: boolean
  /**
   * 弹窗开关状态变更回调
   */
  onOpenChange: (open: boolean) => void
  /**
   * 用户确认回调（保存到 localStorage）
   */
  onConfirm: () => void
}
