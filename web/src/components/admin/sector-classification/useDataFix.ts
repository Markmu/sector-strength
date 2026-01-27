'use client'

import { useState, useCallback } from 'react'
import { adminApiClient } from '@/lib/api'
import type {
  DataFixRequest,
  DataFixResponse,
} from '@/types/data-fix'
import { DataFixStatus as FixStatus } from '@/types/data-fix'
import type { UseDataFixReturn } from './useDataFix.types'

const FIX_ENDPOINT = '/admin/sector-classification/fix'

/**
 * 数据修复 Hook
 *
 * @description
 * Story 4.5: Task 3
 * 提供数据修复的状态管理和操作逻辑
 *
 * @returns {UseDataFixReturn} 修复状态和操作函数
 */
export function useDataFix(): UseDataFixReturn {
  const [status, setStatus] = useState<FixStatus>(FixStatus.IDLE)
  const [result, setResult] = useState<DataFixResponse['data'] | null>(null)
  const [error, setError] = useState<string | null>(null)

  /**
   * 执行数据修复
   */
  const fix = useCallback(async (request: DataFixRequest) => {
    setStatus(FixStatus.VALIDATING)
    setResult(null)
    setError(null)

    try {
      // 验证请求参数
      if (!request.sector_id && !request.sector_name) {
        throw new Error('请提供板块 ID 或板块名称')
      }

      if (request.sector_id && request.sector_name) {
        throw new Error('只能提供板块 ID 或板块名称其中之一')
      }

      if (request.days <= 0) {
        throw new Error('时间范围必须大于 0')
      }

      setStatus(FixStatus.FIXING)

      const response = await adminApiClient.post<DataFixResponse>(
        FIX_ENDPOINT,
        request
      )

      if (response.data) {
        setResult(response.data)
        setStatus(FixStatus.SUCCESS)
      } else {
        setError('数据修复失败')
        setStatus(FixStatus.ERROR)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '网络错误'
      setError(errorMessage)
      setStatus(FixStatus.ERROR)
    }
  }, [])

  /**
   * 重置状态
   */
  const reset = useCallback(() => {
    setStatus(FixStatus.IDLE)
    setResult(null)
    setError(null)
  }, [])

  const isFixing = status === FixStatus.VALIDATING ||
                   status === FixStatus.FIXING

  return {
    status,
    result,
    error,
    isFixing,
    fix,
    reset,
  }
}
