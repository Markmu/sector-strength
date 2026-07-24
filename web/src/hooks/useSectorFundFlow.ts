/**
 * 板块资金流 SWR Hooks（13 期 plan-03）
 *
 * 参照 useFundCrowdAnalysis.ts 模式：
 * - SWR 数组 key + fetcher 调 sectorFundFlowApi（经 apiClient，baseURL 已含 /api/v1）
 * - 不直接用 lib/fetcher.ts（其 API_BASE 不含 /api/v1，与 apiClient 是两套 baseURL 体系）
 *
 * 解包层级：fetcher 的 `.then(res => res.data)` 解一层 —— res 是 ApiResponse<T>
 * （{ data?: T }），.data 取其 body { success, data }。故 hook 返回的 data 是
 * 该 body，组件再读 data.data 取业务对象（camelCase）。
 */
import useSWR from 'swr'
import { sectorFundFlowApi } from '@/lib/api'
import type { SectorType } from '@/types/sectorTypes'
import type {
  FundFlowRankingsData,
  FundFlowTimeseriesData,
  FundFlowLatestDateData,
  FundFlowSortBy,
  FundFlowOrder,
} from '@/types/fundFlowTypes'

const SWR_OPTIONS = {
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  dedupingInterval: 30000,
} as const

// ============== 排行榜 ==============

export interface UseFundFlowRankingsParams {
  sectorType?: SectorType
  tradeDate?: string | null
  sortBy?: FundFlowSortBy
  order?: FundFlowOrder
  page?: number
  pageSize?: number
}

/** 资金流排行榜（最新采样点）。始终启用，hasData=false 时返回空 items 供空态判断。 */
export function useFundFlowRankings(params: UseFundFlowRankingsParams) {
  const { data, error, isLoading, mutate, isValidating } = useSWR<{
    success: boolean
    data: FundFlowRankingsData
  }>(
    ['fundFlowRankings', params],
    () =>
      sectorFundFlowApi
        .getRankings(params)
        .then(
          (res) =>
            res.data as unknown as {
              success: boolean
              data: FundFlowRankingsData
            }
        ),
    SWR_OPTIONS
  )

  return {
    rankings: data?.data ?? null,
    isLoading,
    isValidating,
    isError: error,
    mutate,
  }
}

// ============== 板块候选清单（变化视图用，全量，不受排行分页影响）==============

/**
 * 变化曲线视图的板块选择候选：拉取当前维度下全部板块名。
 * 与排行视图的分页解耦——用足够大的 page_size 一次取全，保证用户最多可叠加 50 个。
 */
export function useFundFlowSectorCandidates(
  sectorType: SectorType | undefined,
  tradeDate?: string | null
) {
  const { data, error, isLoading } = useSWR<{
    success: boolean
    data: FundFlowRankingsData
  }>(
    ['fundFlowCandidates', sectorType, tradeDate],
    () =>
      sectorFundFlowApi
        .getRankings({
          sectorType,
          tradeDate,
          // 全量取：行业≈90、概念≈386，一次拉完覆盖所有可选板块
          pageSize: 500,
        })
        .then(
          (res) =>
            res.data as unknown as {
              success: boolean
              data: FundFlowRankingsData
            }
        ),
    SWR_OPTIONS
  )

  return {
    candidates: (data?.data?.items ?? []).map((i) => i.sectorName),
    isLoading,
    isError: error,
  }
}

// ============== 盘中变化曲线 ==============

export interface UseFundFlowTimeseriesParams {
  sectorNames: string[]
  sectorType?: SectorType
  tradeDate?: string | null
}

/**
 * 盘中变化曲线（按板块名分组）。
 * sectorNames 为空时仍发请求（fetcher 内置 undefined 占位），后端返回空 series。
 * 这样依赖 key 稳定，便于"未选板块"引导态与"无采样数据"空态分别呈现。
 */
export function useFundFlowTimeseries(params: UseFundFlowTimeseriesParams) {
  const { data, error, isLoading, mutate, isValidating } = useSWR<{
    success: boolean
    data: FundFlowTimeseriesData
  }>(
    ['fundFlowTimeseries', params],
    () =>
      sectorFundFlowApi
        .getTimeseries(params)
        .then(
          (res) =>
            res.data as unknown as {
              success: boolean
              data: FundFlowTimeseriesData
            }
        ),
    SWR_OPTIONS
  )

  return {
    timeseries: data?.data ?? null,
    isLoading,
    isValidating,
    isError: error,
    mutate,
  }
}

// ============== 最新交易日 ==============

export interface UseFundFlowLatestDateParams {
  sectorType?: SectorType
}

/** 最新交易日（日期选择器默认值 + 判断是否有任何数据）。 */
export function useFundFlowLatestDate(params: UseFundFlowLatestDateParams) {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: FundFlowLatestDateData
  }>(
    ['fundFlowLatestDate', params.sectorType],
    () =>
      sectorFundFlowApi
        .getLatestDate({ sectorType: params.sectorType })
        .then(
          (res) =>
            res.data as unknown as {
              success: boolean
              data: FundFlowLatestDateData
            }
        ),
    SWR_OPTIONS
  )

  return {
    latestDate: data?.data?.latestDate ?? null,
    isLoading,
    isError: error,
    mutate,
  }
}
