/**
 * 板块散点图数据获取 Hook
 */

'use client'

import useSWR from 'swr'
import { useMemo } from 'react'
import type { AxisType, SectorType, SectorScatterResponse } from '@/types/scatter'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface UseSectorScatterDataParams {
  xAxis?: AxisType
  yAxis?: AxisType
  sectorType?: SectorType
  minGrade?: string | null
  maxGrade?: string | null
  offset?: number
  limit?: number
  calcDate?: string | null
  enabled?: boolean
}

interface UseSectorScatterDataReturn {
  data: SectorScatterResponse | null
  isLoading: boolean
  isError: boolean
  isValidating: boolean
  error: Error | null
  mutate: () => void
}

const fetcher = async (url: string): Promise<SectorScatterResponse> => {
  const response = await fetch(url)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(error.detail || `API 请求失败: ${response.status}`)
  }

  const result = await response.json()
  return result.data
}

export function useSectorScatterData({
  xAxis = 'short',
  yAxis = 'medium',
  sectorType = 'industry',
  minGrade = null,
  maxGrade = null,
  offset = 0,
  limit = 200,
  calcDate = null,
  enabled = true,
}: UseSectorScatterDataParams = {}): UseSectorScatterDataReturn {
  // 构建 URL 查询参数
  const params = new URLSearchParams({
    x_axis: xAxis,
    y_axis: yAxis,
    offset: String(offset),
    limit: String(limit),
  })

  // sectorType 是必填的，但为了兼容性保留条件检查
  params.append('sector_type', sectorType)
  if (minGrade) params.append('min_grade', minGrade)
  if (maxGrade) params.append('max_grade', maxGrade)
  if (calcDate) params.append('calc_date', calcDate)

  const queryString = params.toString()
  const url = `${API_BASE}/api/v1/analysis/sector-scatter?${queryString}`

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
  } = useSWR<SectorScatterResponse>(
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
