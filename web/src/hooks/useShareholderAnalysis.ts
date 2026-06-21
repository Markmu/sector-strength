/**
 * 股东分析面板 SWR Hooks（plan-04）
 *
 * 参照 useFunds.ts 模式：
 * - SWR 使用数组 key + fetcher 内部调用 shareholderAnalysisApi（经 apiClient，baseURL 已含 /api/v1）
 * - 不直接使用 lib/fetcher.ts（其 API_BASE 不含 /api/v1，与 apiClient 是两套 baseURL 体系）
 *
 * 解包层级：fetcher 的 `.then(res => res.data)` 解一层 —— res 是 shareholderAnalysisApi 方法
 * 返回的 ApiResponse 对象，.data 取其 data 字段即整个 body { success, data }。
 * 故 hook 返回的 data 是该 body，组件再读 data.data 取业务对象（与 useFunds.ts 读
 * data?.data?.items 一致，见 plan-02 §3.6 的 ApiResponse[T] 包裹契约）。
 */
import useSWR from 'swr'
import {
  shareholderAnalysisApi,
  type ShareholderOverviewResponse,
  type ShareholderSummaryResponse,
  type ShareholderIndustryDistributionResponse,
  type ShareholderHoldingsResponse,
} from '@/lib/api'

const SWR_OPTIONS = {
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  dedupingInterval: 30000,
} as const

export interface UseShareholderSummaryParams {
  group_ids?: string
  holder_name?: string
  report_period: string
  industry?: string
  change_direction?: string
}

export interface UseShareholderIndustryDistributionParams {
  group_ids?: string
  holder_name?: string
  report_period: string
  change_direction?: string
}

export interface UseShareholderHoldingsParams {
  group_ids?: string
  holder_name?: string
  report_period: string
  industry?: string
  change_direction?: string
  page?: number
  pageSize?: number
}

/**
 * 监控组概览（含报告期列表 + hasPrevPeriod + 各组汇总）
 */
export function useShareholderOverview(reportPeriod?: string) {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: ShareholderOverviewResponse
  }>(
    ['shareholderOverview', reportPeriod ?? null],
    () =>
      shareholderAnalysisApi
        .getOverview(
          reportPeriod ? { report_period: reportPeriod } : undefined
        )
        .then((res) => res.data as unknown as {
          success: boolean
          data: ShareholderOverviewResponse
        }),
    SWR_OPTIONS
  )

  return {
    overview: data?.data ?? null,
    isLoading,
    isError: error,
    mutate,
  }
}

/**
 * 持仓汇总 + 变动趋势
 */
export function useShareholderSummary(params: UseShareholderSummaryParams | null) {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: ShareholderSummaryResponse
  }>(
    params ? ['shareholderSummary', params] : null,
    () =>
      shareholderAnalysisApi
        .getSummary(params!)
        .then((res) => res.data as unknown as {
          success: boolean
          data: ShareholderSummaryResponse
        }),
    SWR_OPTIONS
  )

  return {
    summary: data?.data ?? null,
    isLoading,
    isError: error,
    mutate,
  }
}

/**
 * 行业分布
 */
export function useShareholderIndustryDistribution(
  params: UseShareholderIndustryDistributionParams | null
) {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: ShareholderIndustryDistributionResponse
  }>(
    params ? ['shareholderIndustryDist', params] : null,
    () =>
      shareholderAnalysisApi
        .getIndustryDistribution(params!)
        .then((res) => res.data as unknown as {
          success: boolean
          data: ShareholderIndustryDistributionResponse
        }),
    SWR_OPTIONS
  )

  return {
    distribution: data?.data?.distribution ?? [],
    isLoading,
    isError: error,
    mutate,
  }
}

/**
 * 持仓股票分页列表（含退出股票）
 */
export function useShareholderHoldings(params: UseShareholderHoldingsParams | null) {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: ShareholderHoldingsResponse
  }>(
    params ? ['shareholderHoldings', params] : null,
    () =>
      shareholderAnalysisApi
        .getHoldings(params!)
        .then((res) => res.data as unknown as {
          success: boolean
          data: ShareholderHoldingsResponse
        }),
    SWR_OPTIONS
  )

  return {
    holdings: data?.data?.holdings ?? [],
    total: data?.data?.total ?? 0,
    isLoading,
    isError: error,
    mutate,
  }
}
