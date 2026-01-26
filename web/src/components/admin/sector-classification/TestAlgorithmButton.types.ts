/**
 * TestAlgorithmButton 组件类型定义
 *
 * @description
 * 测试按钮组件的 Props 接口
 */
export interface TestAlgorithmButtonProps {
  /** 是否正在测试 */
  testing: boolean
  /** 测试按钮点击回调 */
  onTest: () => void
  /** 是否禁用（可选） */
  disabled?: boolean
}
