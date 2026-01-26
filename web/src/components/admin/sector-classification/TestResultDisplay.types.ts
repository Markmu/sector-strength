/**
 * TestResultDisplay 组件类型定义
 *
 * @description
 * 测试结果展示组件的 Props 接口
 */
export interface TestResultDisplayProps {
  /** 测试结果 */
  result: import('@/types/admin-test').ClassificationTestResult | null
  /** 错误信息 */
  error: string | null
  /** 重试回调 */
  onRetry: () => void
  /** 是否正在测试 */
  testing: boolean
}
