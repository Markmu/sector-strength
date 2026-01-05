import useSWR from 'swr'
import { sectorsApi } from '@/lib/api'
import type { SectorStrengthHistoryResponse, TimeRangeOption } from '@/types'

interface UseSectorStrengthHistoryParams {
  sectorId: number
  timeRange?: TimeRangeOption
  startDate?: string
  endDate?: string
  enabled?: boolean
}

interface UseSectorStrengthHistoryResult {
  data: SectorStrengthHistoryResponse | undefined
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
}

export function useSectorStrengthHistory({
  sectorId,
  timeRange = '2m',
  startDate,
  endDate,
  enabled = true,
}: UseSectorStrengthHistoryParams): UseSectorStrengthHistoryResult {
  // SWR fetcher
  const fetcher = async (url: string): Promise<SectorStrengthHistoryResponse> => {
    const response = await sectorsApi.getSectorStrengthHistory(sectorId, {
      start_date: startDate,
      end_date: endDate,
    })
    if (!response.data) {
      throw new Error('Failed to fetch strength history data')
    }
    return response.data
  }

  // 计算日期范围 (如果未提供具体日期)
  let finalStartDate = startDate
  let finalEndDate = endDate

  if (!finalStartDate || !finalEndDate) {
    const end = finalEndDate ? new Date(finalEndDate) : new Date()
    const days = TIME_RANGE_DAYS[timeRange]
    const start = new Date(end)
    start.setDate(start.getDate() - days)

    finalStartDate = finalStartDate || start.toISOString().split('T')[0]
    finalEndDate = finalEndDate || end.toISOString().split('T')[0]
  }

  // 构建查询键
  const queryKey = `/sectors/${sectorId}/strength-history?start_date=${finalStartDate}&end_date=${finalEndDate}`

  const { data, error, isLoading, mutate } = useSWR<SectorStrengthHistoryResponse>(
    enabled && sectorId ? queryKey : null,
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
