/**
 * 板块类型分布数据获取 Hook
 */

'use client'

import useSWR from 'swr'
import type { SectorDistributionResponse } from '@/types/gradeTable'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface UseSectorDistributionReturn {
  data: SectorDistributionResponse | null
  isLoading: boolean
  isError: boolean
  isValidating: boolean
  error: Error | null
  mutate: () => void
}

const fetcher = async (url: string): Promise<SectorDistributionResponse> => {
  const response = await fetch(url)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(error.detail || `API 请求失败: ${response.status}`)
  }

  const result = await response.json()
  return result.data
}

export function useSectorDistribution(): UseSectorDistributionReturn {
  const url = `${API_BASE}/api/v1/analysis/sector-distribution`

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
  } = useSWR<SectorDistributionResponse>(
    typeof window !== 'undefined' ? url : null,
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
