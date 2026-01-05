// 板块排名数据 Hook
import useSWR from 'swr'
import type { RankingResponse, SortOrder } from '@/lib/ranking/types'
import { fetcher } from '@/lib/fetcher'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface UseSectorRankingParams {
  topN?: number
  order?: SortOrder
  sortBy?: 'strength' | 'trend'
  sectorType?: 'industry' | 'concept'
  refreshInterval?: number
}

export function useSectorRanking({
  topN = 10,
  order = 'desc',
  sortBy = 'strength',
  sectorType,
  refreshInterval = 5000,
}: UseSectorRankingParams = {}) {
  const params = new URLSearchParams({
    top_n: topN.toString(),
    order,
    sort_by: sortBy,
  })

  if (sectorType) {
    params.append('sector_type', sectorType)
  }

  const { data, error, isLoading, mutate } = useSWR<RankingResponse>(
    `${API_BASE}/api/v1/rankings/sectors?${params}`,
    fetcher,
    {
      refreshInterval: 0, // 禁用自动轮询，使用手动刷新
      revalidateOnFocus: false, // 禁用窗口聚焦时刷新
      revalidateOnReconnect: true, // 网络重连时刷新
    }
  )

  return {
    sectors: data?.data || [],
    total: data?.total || 0,
    isLoading,
    isError: error,
    mutate,
  }
}
