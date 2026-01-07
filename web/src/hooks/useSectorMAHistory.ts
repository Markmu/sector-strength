import useSWR from 'swr'
import { sectorsApi } from '@/lib/api'
import type { SectorMAHistoryResponse, TimeRangeOption } from '@/types'
import { useMemo } from 'react'

interface UseSectorMAHistoryParams {
  sectorId: number
  timeRange?: TimeRangeOption
  startDate?: string
  endDate?: string
  enabled?: boolean
}

interface UseSectorMAHistoryResult {
  data: SectorMAHistoryResponse | undefined
  isLoading: boolean
  isError: boolean
  error: unknown
  mutate: () => void
}

// 时间范围映射 (天数)
const TIME_RANGE_DAYS: Record<TimeRangeOption, number> = {
  '1w': 7,
  '1m': 30,
  '2m': 60,
  '3m': 90,
  '6m': 180,
  '1y': 365,
  'custom': 0,
}

// 辅助函数：获取今天日期
const getTodayDate = () => {
  return new Date().toISOString().split('T')[0]
}

export function useSectorMAHistory({
  sectorId,
  timeRange = '2m',
  startDate,
  endDate,
  enabled = true,
}: UseSectorMAHistoryParams): UseSectorMAHistoryResult {
  // 使用 useMemo 计算日期范围，确保 timeRange 变化时重新计算
  const { finalStartDate, finalEndDate } = useMemo(() => {
    // 如果是自定义时间范围且提供了具体日期，使用提供的日期
    if (timeRange === 'custom' && startDate && endDate) {
      return { finalStartDate: startDate, finalEndDate: endDate }
    }

    // 否则根据 timeRange 计算日期
    const end = new Date()
    const days = TIME_RANGE_DAYS[timeRange] || 60
    const start = new Date(end)
    start.setDate(start.getDate() - days)

    return {
      finalStartDate: start.toISOString().split('T')[0],
      finalEndDate: end.toISOString().split('T')[0]
    }
  }, [timeRange, startDate, endDate])

  // SWR fetcher
  const fetcher = async (url: string): Promise<SectorMAHistoryResponse> => {
    const response = await sectorsApi.getSectorMAHistory(sectorId, {
      start_date: finalStartDate,
      end_date: finalEndDate,
    })
    if (!response.data) {
      throw new Error('Failed to fetch MA history data')
    }
    return response.data
  }

  // 构建查询键
  const queryKey = useMemo(() => {
    if (!sectorId) return null
    return `/sectors/${sectorId}/ma-history?start_date=${finalStartDate}&end_date=${finalEndDate}`
  }, [sectorId, finalStartDate, finalEndDate])

  const { data, error, isLoading, mutate } = useSWR<SectorMAHistoryResponse>(
    enabled && queryKey ? queryKey : null,
    fetcher,
    {
      refreshInterval: 0, // 禁用自动轮询
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      dedupingInterval: 10000, // 10秒内相同请求去重
    }
  )

  return {
    data,
    isLoading,
    isError: !!error,
    error,
    mutate,
  }
}
