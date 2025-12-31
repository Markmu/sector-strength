/**
 * 板块等级表格数据获取 Hook
 */

'use client'

import useSWR from 'swr'
import { useMemo } from 'react'
import type { SectorType, SectorGradeTableResponse } from '@/types/gradeTable'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface UseSectorGradeTableParams {
  sectorType?: SectorType | null
  calcDate?: string | null
  enabled?: boolean
}

interface UseSectorGradeTableReturn {
  data: SectorGradeTableResponse | null
  isLoading: boolean
  isError: boolean
  isValidating: boolean
  error: Error | null
  mutate: () => void
}

const fetcher = async (url: string): Promise<SectorGradeTableResponse> => {
  const response = await fetch(url)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(error.detail || `API 请求失败: ${response.status}`)
  }

  const result = await response.json()
  return result.data
}

export function useSectorGradeTable({
  sectorType = null,
  calcDate = null,
  enabled = true,
}: UseSectorGradeTableParams = {}): UseSectorGradeTableReturn {
  // 构建 URL 查询参数
  const params = new URLSearchParams()

  if (sectorType) params.append('sector_type', sectorType)
  if (calcDate) params.append('calc_date', calcDate)

  const queryString = params.toString()
  const url = `${API_BASE}/api/v1/analysis/sector-grade-table${queryString ? `?${queryString}` : ''}`

  // SWR 配置
  const swrConfig = {
    revalidateOnFocus: false,
    revalidateOnReconnect: true,
    dedupingInterval: 30000, // 30 秒内相同请求去重
    errorRetryCount: 3,
    errorRetryInterval: 5000,
    shouldRetryOnError: true,
  }

  // 使用 SWR 获取数据
  const {
    data,
    error,
    isLoading,
    isValidating,
    mutate,
  } = useSWR<SectorGradeTableResponse>(
    enabled && typeof window !== 'undefined' ? url : null,
    fetcher,
    swrConfig,
  )

  return {
    data: data || null,
    isLoading,
    isError: !!error,
    isValidating,
    error,
    mutate,
  }
}
