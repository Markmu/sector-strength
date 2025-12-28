// 市场指数数据 Hook
import useSWR from 'swr'
import type { MarketIndexResponse } from '@/lib/market/types'

const fetcher = async (url: string): Promise<MarketIndexResponse> => {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

export function useMarketIndex() {
  const { data, error, isLoading, mutate } = useSWR<MarketIndexResponse>(
    '/api/v1/market-index',
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
