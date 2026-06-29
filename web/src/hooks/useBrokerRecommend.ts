/**
 * 券商月度金股分析 SWR Hooks（09 期 plan-03）
 *
 * 参照 useFundCrowdAnalysis.ts 模式：
 * - SWR 使用数组 key + fetcher 内部调用 brokerRecommendApi（经 apiClient，baseURL 已含 /api/v1）
 * - fetcher 的 `.then(res => res.data)` 解一层 AxiosResponse → { success, data } body
 * - hook 返回 data?.data 取业务对象
 */
import useSWR from 'swr'
import {
  brokerRecommendApi,
  type BrokerRankingResponse,
  type BrokerMonthsResponse,
  type BrokerDetailResponse,
  type BrokerSectorRankingsResponse,
  type BrokerStockRankingItem,
  type BrokerGroupItem,
} from '@/lib/api'

const SWR_OPTIONS = {
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  dedupingInterval: 30000,
} as const

// ========== 月份列表 ==========

export function useBrokerMonths() {
  const { data, error, isLoading } = useSWR<{
    success: boolean
    data: BrokerMonthsResponse
  }>(
    'brokerRecommendMonths',
    () =>
      brokerRecommendApi
        .getMonths()
        .then((res) => res.data as unknown as {
          success: boolean
          data: BrokerMonthsResponse
        }),
    SWR_OPTIONS
  )

  return {
    monthsData: data?.data ?? null,
    isLoading,
    isError: error,
  }
}

// ========== 股票维度排行 ==========

export interface UseBrokerStockRankingParams {
  month?: string
  search?: string
  page?: number
  pageSize?: number
  /** 板块类型筛选：industry/concept/region（默认 industry） */
  sectorType?: string
  /** 板块名筛选（按 sectorType 精确匹配板块名，undefined 表示全部） */
  sectorName?: string
  /** false 时不发起请求（避免非激活视图产生多余请求触发 401） */
  enabled?: boolean
}

export function useBrokerStockRanking(params: UseBrokerStockRankingParams) {
  const { enabled = true, ...query } = params
  const key = enabled ? ['brokerStockRanking', query] : null
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: BrokerRankingResponse
  }>(
    key,
    () =>
      brokerRecommendApi
        .getStockRanking(query)
        .then((res) => res.data as unknown as {
          success: boolean
          data: BrokerRankingResponse
        }),
    SWR_OPTIONS
  )

  const body = data?.data ?? null
  return {
    ranking: body
      ? {
          ...body,
          items: body.items as BrokerStockRankingItem[],
        }
      : null,
    isLoading,
    isError: error,
    mutate,
  }
}

// ========== 券商维度分组 ==========

export interface UseBrokerListParams {
  month?: string
  search?: string
  page?: number
  pageSize?: number
  /** false 时不发起请求（避免非激活视图产生多余请求触发 401） */
  enabled?: boolean
}

export function useBrokerList(params: UseBrokerListParams) {
  const { enabled = true, ...query } = params
  const key = enabled ? ['brokerList', query] : null
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: BrokerRankingResponse
  }>(
    key,
    () =>
      brokerRecommendApi
        .getBrokerList(query)
        .then((res) => res.data as unknown as {
          success: boolean
          data: BrokerRankingResponse
        }),
    SWR_OPTIONS
  )

  const body = data?.data ?? null
  return {
    list: body
      ? {
          ...body,
          items: body.items as BrokerGroupItem[],
        }
      : null,
    isLoading,
    isError: error,
    mutate,
  }
}

// ========== 板块排行榜（行业/概念/地域，各 Top5）==========

export function useBrokerSectorRankings(
  month: string | undefined,
  enabled = true
) {
  const key = enabled ? ['brokerSectorRankings', month ?? null] : null
  const { data, error, isLoading } = useSWR<{
    success: boolean
    data: BrokerSectorRankingsResponse
  }>(
    key,
    () =>
      brokerRecommendApi
        .getSectorRankings({ month })
        .then((res) => res.data as unknown as {
          success: boolean
          data: BrokerSectorRankingsResponse
        }),
    SWR_OPTIONS
  )

  return {
    rankings: data?.data ?? null,
    isLoading,
    isError: error,
  }
}

// ========== 券商明细懒加载 ==========

/**
 * 券商明细懒加载（AC-13）
 *
 * key 为 null 时不发起请求（折叠态）；展开时传入 month+broker 才请求。
 */
export function useBrokerDetail(month: string | null, broker: string | null) {
  const key = month && broker ? ['brokerDetail', month, broker] : null
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: BrokerDetailResponse
  }>(
    key,
    () =>
      brokerRecommendApi
        .getBrokerDetail({ month: month!, broker: broker! })
        .then((res) => res.data as unknown as {
          success: boolean
          data: BrokerDetailResponse
        }),
    {
      ...SWR_OPTIONS,
      revalidateOnMount: true,
    }
  )

  return {
    detail: data?.data ?? null,
    isLoading,
    isError: error,
    mutate,
  }
}
