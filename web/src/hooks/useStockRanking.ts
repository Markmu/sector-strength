// 个股排名数据 Hook
import useSWR from 'swr'
import type { RankingResponse, SortOrder } from '@/lib/ranking/types'
import { fetcher } from '@/lib/fetcher'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface UseStockRankingParams {
  topN?: number
  order?: SortOrder
  sortBy?: 'strength' | 'trend'
  sectorId?: string
  refreshInterval?: number
}

export function useStockRanking({
  topN = 20,
  order = 'desc',
  sortBy = 'strength',
  sectorId,
  refreshInterval = 5000,
}: UseStockRankingParams = {}) {
  const params = new URLSearchParams({
    top_n: topN.toString(),
    order,
    sort_by: sortBy,
  })

  if (sectorId) {
    params.append('sector_id', sectorId)
  }

  const { data, error, isLoading, mutate } = useSWR<RankingResponse>(
    `${API_BASE}/api/v1/rankings/stocks?${params}`,
    fetcher,
    {
      refreshInterval: 0, // 禁用自动轮询，使用手动刷新
      revalidateOnFocus: false, // 禁用窗口聚焦时刷新
      revalidateOnReconnect: true, // 网络重连时刷新
    }
  )

  return {
    stocks: data?.data || [],
    total: data?.total || 0,
    isLoading,
    isError: error,
    mutate,
  }
}
