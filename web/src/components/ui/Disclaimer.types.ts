/**
 * Disclaimer 组件类型定义
 */

/**
 * Disclaimer 组件属性
 */
export interface DisclaimerProps {
  /**
   * 自定义类名（可选）
   */
  className?: string
  /**
   * 免责声明文本（可选，默认使用标准文本）
   * @default 包含主声明、风险提示、缠论说明三部分
   */
  text?: string
  /**
   * 是否显示分隔线
   * @default false
   */
  showSeparator?: boolean
}
