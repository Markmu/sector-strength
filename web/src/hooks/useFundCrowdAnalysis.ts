/**
 * 基金扎堆分析 SWR Hooks（plan-02）
 *
 * 参照 useShareholderAnalysis.ts 模式：
 * - SWR 使用数组 key + fetcher 内部调用 fundCrowdAnalysisApi（经 apiClient，baseURL 已含 /api/v1）
 * - 不直接使用 lib/fetcher.ts（其 API_BASE 不含 /api/v1，与 apiClient 是两套 baseURL 体系）
 *
 * 解包层级：fetcher 的 `.then(res => res.data)` 解一层 —— res 是 fundCrowdAnalysisApi 方法
 * 返回的 AxiosResponse 对象，.data 取其 body { success, data }。
 * 故 hook 返回的 data 是该 body，组件再读 data.data 取业务对象。
 */
import useSWR from 'swr'
import {
  fundCrowdAnalysisApi,
  type CrowdRankingsResponse,
  type CrowdIndustryDistributionResponse,
  type CrowdScope,
} from '@/lib/api'
import type { SectorType } from '@/types/sectorTypes'

const SWR_OPTIONS = {
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  dedupingInterval: 30000,
} as const

export interface UseFundCrowdRankingsParams {
  scope: CrowdScope
  sectorType?: SectorType
  search?: string
  page?: number
  pageSize?: number
}

/**
 * 扎堆度排行榜（含环比 + 搜索 + 分页）
 *
 * 始终启用（scope 默认 'active'）—— 即使 hasData=false 也返回 hasData 标志供组件判断空状态。
 */
export function useFundCrowdRankings(params: UseFundCrowdRankingsParams) {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: CrowdRankingsResponse
  }>(
    ['fundCrowdRankings', params],
    () =>
      fundCrowdAnalysisApi
        .getRankings(params)
        .then((res) => res.data as unknown as {
          success: boolean
          data: CrowdRankingsResponse
        }),
    SWR_OPTIONS
  )

  return {
    rankings: data?.data ?? null,
    isLoading,
    isError: error,
    mutate,
  }
}

/**
 * 行业分布（与排行榜联动，scope 变化时同步重发）
 */
export function useFundCrowdIndustryDistribution(
  scope: CrowdScope,
  sectorType?: SectorType
) {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: CrowdIndustryDistributionResponse
  }>(
    ['fundCrowdIndustryDistribution', scope, sectorType],
    () =>
      fundCrowdAnalysisApi
        .getIndustryDistribution({ scope, sectorType })
        .then((res) => res.data as unknown as {
          success: boolean
          data: CrowdIndustryDistributionResponse
        }),
    SWR_OPTIONS
  )

  return {
    distribution: data?.data?.distribution ?? [],
    currentPeriod: data?.data?.currentPeriod ?? null,
    hasData: data?.data?.hasData ?? false,
    totalStockCount: data?.data?.totalStockCount ?? 0,
    isLoading,
    isError: error,
    mutate,
  }
}
