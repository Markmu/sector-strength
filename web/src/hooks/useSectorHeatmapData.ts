import useSWR from 'swr'
import { heatmapApi } from '@/lib/api'
import type { HeatmapResponse, HeatmapSector } from '@/types'
import { HeatmapResponseSchema } from '@/types'

const HEATMAP_REFRESH_INTERVAL = 5000 // 5秒自动刷新

interface UseSectorHeatmapDataParams {
  sectorType?: 'industry' | 'concept'
  enabled?: boolean
}

interface UseSectorHeatmapDataResult {
  sectors: HeatmapSector[]
  timestamp: string | undefined
  isLoading: boolean
  isError: boolean
  error: unknown
  mutate: () => void
}

export function useSectorHeatmapData({
  sectorType,
  enabled = true,
}: UseSectorHeatmapDataParams = {}): UseSectorHeatmapDataResult {
  // SWR fetcher with Zod validation
  const fetcher = async (url: string) => {
    const response = await heatmapApi.getHeatmap(
      sectorType ? { sector_type: sectorType } : undefined
    )

    // 使用 Zod 验证 API 响应
    const validationResult = HeatmapResponseSchema.safeParse(response.data)

    if (!validationResult.success) {
      console.error('热力图数据验证失败:', validationResult.error)
      // 返回空数据作为降级处理
      return {
        success: true,
        data: { sectors: [], timestamp: new Date().toISOString() },
      }
    }

    return response.data
  }

  // 构建查询键
  const queryKey = sectorType
    ? `/api/v1/heatmap?sector_type=${sectorType}`
    : '/api/v1/heatmap'

  const { data, error, isLoading, mutate } = useSWR<HeatmapResponse>(
    enabled ? queryKey : null,
    fetcher,
    {
      refreshInterval: 0, // 禁用自动轮询，使用手动刷新
      revalidateOnFocus: false, // 禁用窗口聚焦时刷新
      revalidateOnReconnect: true, // 网络重连时刷新
      dedupingInterval: 1000,
    }
  )

  return {
    sectors: data?.data?.sectors || [],
    timestamp: data?.data?.timestamp,
    isLoading,
    isError: !!error,
    error,
    mutate,
  }
}
