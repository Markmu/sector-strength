'use client'

import { useState, useCallback } from 'react'
import { apiClient } from '@/lib/apiClient'
import type {
  ClassificationTestResult,
  UseClassificationTestReturn,
} from './useClassificationTest.types'

const TEST_ENDPOINT = '/api/v1/admin/sector-classification/test'

/**
 * useClassificationTest Hook
 *
 * @description
 * 管理分类算法测试的状态和逻辑：
 * - 执行测试调用
 * - 管理加载、成功和错误状态
 * - 提供重置功能
 *
 * @returns 测试状态和控制函数
 */
export function useClassificationTest(): UseClassificationTestReturn {
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<ClassificationTestResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  /**
   * 执行分类算法测试
   */
  const runTest = useCallback(async () => {
    setTesting(true)
    setError(null)
    setTestResult(null)

    try {
      const response = await apiClient.post<any, TestApiResponse>(
        TEST_ENDPOINT
      )

      if (response.success && response.data) {
        setTestResult(response.data)
      } else {
        setError(response.error?.message || '测试失败')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '网络错误，请重试')
    } finally {
      setTesting(false)
    }
  }, [])

  /**
   * 重置测试状态
   */
  const reset = useCallback(() => {
    setTesting(false)
    setTestResult(null)
    setError(null)
  }, [])

  return {
    testing,
    testResult,
    error,
    runTest,
    reset,
  }
}
