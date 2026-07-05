import useSWR from 'swr'
import { useMemo } from 'react'
import { sectorsApi } from '@/lib/api'
import type { SectorStocksData } from '@/types/sectorTypes'

interface UseSectorStocksParams {
  sectorId: number
  sortBy: 'strength_score' | 'market_cap'
  sortOrder: 'asc' | 'desc'
  page: number
  pageSize: number
  enabled?: boolean
}

interface UseSectorStocksResult {
  data: SectorStocksData | undefined
  isLoading: boolean
  isError: boolean
  error: unknown
  mutate: () => void
}

/**
 * 板块成分股数据获取 hook。
 *
 * 仿 useSectorStrengthHistory 范式：参数透传后端（page/page_size/sort_by/sort_order），
 * 排序与分页完全由后端驱动。与板块详情页的图表 hook 相互独立，互不阻塞。
 */
export function useSectorStocks({
  sectorId,
  sortBy,
  sortOrder,
  page,
  pageSize,
  enabled = true,
}: UseSectorStocksParams): UseSectorStocksResult {
  // SWR fetcher：调用 sectorsApi.getSectorStocks，解包 .data（得 SectorStocksResponse）→ .data（得 SectorStocksData）
  const fetcher = async (url: string): Promise<SectorStocksData> => {
    // url 仅用作 cache key，实际参数由闭包持有
    const response = await sectorsApi.getSectorStocks(sectorId, {
      page,
      page_size: pageSize,
      sort_by: sortBy,
      sort_order: sortOrder,
    })
    const outer = response.data // SectorStocksResponse | undefined
    if (!outer || !outer.data) {
      throw new Error('Failed to fetch sector stocks')
    }
    return outer.data as SectorStocksData
  }

  // 构建查询键（含全部驱动参数，任一变化即重载）
  const queryKey = useMemo(() => {
    if (!sectorId) return null
    return `/sectors/${sectorId}/stocks?sort_by=${sortBy}&sort_order=${sortOrder}&page=${page}&page_size=${pageSize}`
  }, [sectorId, sortBy, sortOrder, page, pageSize])

  const { data, error, isLoading, mutate } = useSWR<SectorStocksData>(
    enabled && queryKey ? queryKey : null,
    fetcher,
    {
      refreshInterval: 0,
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      dedupingInterval: 10000,
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
