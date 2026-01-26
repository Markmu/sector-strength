/**
 * 管理员测试相关类型定义
 *
 * @description
 * 定义分类算法测试相关的所有类型：
 * - 测试结果类型
 * - 测试失败详情
 * - API 响应类型
 * - Hook 返回类型
 */

/** 测试失败详情 */
export interface TestFailure {
  /** 板块 ID */
  sector_id: string
  /** 板块名称 */
  sector_name: string
  /** 错误信息 */
  error: string
}

/** 分类测试结果 */
export interface ClassificationTestResult {
  /** 总板块数 */
  total_count: number
  /** 成功计算数 */
  success_count: number
  /** 失败计算数 */
  failure_count: number
  /** 计算耗时（毫秒） */
  duration_ms: number
  /** 测试时间戳 */
  timestamp: string
  /** 失败的板块列表（如果有） */
  failures?: TestFailure[]
}

/** 测试 API 错误响应 */
export interface TestApiError {
  /** 错误代码 */
  code: string
  /** 错误消息 */
  message: string
  /** 错误详情 */
  details?: any
}

/** 测试 API 响应 */
export interface TestApiResponse {
  /** 是否成功 */
  success: boolean
  /** 测试结果数据 */
  data?: ClassificationTestResult
  /** 错误信息 */
  error?: TestApiError
}

/** useClassificationTest Hook 返回类型 */
export interface UseClassificationTestReturn {
  /** 测试状态 */
  testing: boolean
  /** 测试结果 */
  testResult: ClassificationTestResult | null
  /** 错误信息 */
  error: string | null
  /** 执行测试函数 */
  runTest: () => Promise<void>
  /** 重置测试状态 */
  reset: () => void
}
