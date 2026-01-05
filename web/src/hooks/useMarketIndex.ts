// 市场指数数据 Hook
import useSWR from 'swr'
import type { MarketIndexResponse } from '@/lib/market/types'
import { fetcher } from '@/lib/fetcher'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function useMarketIndex() {
  const { data, error, isLoading, mutate } = useSWR<MarketIndexResponse>(
    `${API_BASE}/api/v1/market-index`,
    fetcher,
    {
      refreshInterval: 0, // 禁用自动轮询，使用手动刷新
      revalidateOnFocus: false, // 禁用窗口聚焦时刷新
      revalidateOnReconnect: true, // 网络重连时刷新
    }
  )

  return {
    index: data?.data?.index,
    stats: data?.data?.stats,
    trend: data?.data?.trend || [],
    isLoading,
    isError: error,
    mutate,
  }
}
