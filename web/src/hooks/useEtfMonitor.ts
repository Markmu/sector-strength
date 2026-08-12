/**
 * ETF 监控 SWR Hooks（14 期 plan-04）
 *
 * 参照 useSectorFundFlow.ts 模式：
 * - SWR 数组 key + fetcher 调 etfMonitorApi（经 apiClient，baseURL 已含 /api/v1）
 * - 不直接用 lib/fetcher.ts（其 API_BASE 不含 /api/v1，与 apiClient 是两套 baseURL 体系）
 *
 * 解包层级：fetcher 的 `.then(res => res.data)` 解一层 -- res 是 ApiResponse<T>
 * （{ data?: T }），.data 取其 body { success, data }。故 hook 返回的 data 是
 * 该 body，组件再读 data.data 取业务对象（camelCase）。
 *
 * 深路径导入本文件，不改 hooks/index.ts（与 useSectorFundFlow 一致）。
 */
import useSWR from 'swr'
import { etfMonitorApi } from '@/lib/api'
import type {
  EtfSortBy,
  EtfTrendMetric,
  EtfTargetType,
  EtfTrendDays,
  EtfIndexRankingsData,
  EtfIndexDetailData,
  EtfTrendData,
  EtfLatestDateData,
} from '@/types/etfMonitorTypes'

const SWR_OPTIONS = {
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  dedupingInterval: 30000,
} as const

// ============== 指数排行 ==============

export interface UseEtfIndexRankingsParams {
  tradeDate?: string | null
  sortBy?: EtfSortBy
  order?: 'desc' | 'asc'
  page?: number
  pageSize?: number
}

/** 指数排行（最新采样点或历史日期）。始终启用，hasData=false 时返回空 items 供空态判断。 */
export function useEtfIndexRankings(params: UseEtfIndexRankingsParams) {
  const { data, error, isLoading, mutate, isValidating } = useSWR<{
    success: boolean
    data: EtfIndexRankingsData
  }>(
    ['etfIndexRankings', params],
    () =>
      etfMonitorApi
        .getIndexRankings(params)
        .then(
          (res) =>
            res.data as unknown as {
              success: boolean
              data: EtfIndexRankingsData
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

// ============== 指数明细（条件 hook）==============

export interface UseEtfIndexDetailParams {
  indexCode: string | null
  tradeDate?: string | null
}

/**
 * 指数明细（展开指数查看其下 ETF 明细）。
 * 条件 hook：indexCode 为 null 时传 null key，SWR 不发请求（展开前不预取）。
 */
export function useEtfIndexDetail(params: UseEtfIndexDetailParams) {
  // indexCode 缺失 → key=null，SWR 跳过请求（不进入 fetcher）
  const key =
    params.indexCode != null
      ? ['etfIndexDetail', params.indexCode, params.tradeDate ?? null]
      : null

  const { data, error, isLoading, mutate, isValidating } = useSWR<{
    success: boolean
    data: EtfIndexDetailData
  }>(
    key,
    () =>
      etfMonitorApi
        .getIndexDetail({
          indexCode: params.indexCode as string,
          tradeDate: params.tradeDate,
        })
        .then(
          (res) =>
            res.data as unknown as {
              success: boolean
              data: EtfIndexDetailData
            }
        ),
    SWR_OPTIONS
  )

  return {
    detail: data?.data ?? null,
    isLoading,
    isValidating,
    isError: error,
    mutate,
  }
}

// ============== 历史趋势（条件 hook）==============

export interface UseEtfTrendParams {
  targetType: EtfTargetType
  targetCode: string | null
  metric: EtfTrendMetric
  days: EtfTrendDays
  endDate?: string | null
}

/**
 * 历史趋势（指数或 ETF 的份额/净流入额曲线）。
 * 条件 hook：targetCode 为 null 时传 null key，SWR 不发请求（未选对象前不预取）。
 */
export function useEtfTrend(params: UseEtfTrendParams) {
  // targetCode 缺失 → key=null，SWR 跳过请求
  const key =
    params.targetCode != null
      ? [
          'etfTrend',
          params.targetType,
          params.targetCode,
          params.metric,
          params.days,
          params.endDate ?? null,
        ]
      : null

  const { data, error, isLoading, mutate, isValidating } = useSWR<{
    success: boolean
    data: EtfTrendData
  }>(
    key,
    () =>
      etfMonitorApi
        .getTrend({
          targetType: params.targetType,
          targetCode: params.targetCode as string,
          metric: params.metric,
          days: params.days,
          endDate: params.endDate,
        })
        .then(
          (res) =>
            res.data as unknown as {
              success: boolean
              data: EtfTrendData
            }
        ),
    SWR_OPTIONS
  )

  return {
    trend: data?.data ?? null,
    isLoading,
    isValidating,
    isError: error,
    mutate,
  }
}

// ============== 最新交易日 ==============

/** 最新交易日（日期选择器默认值 + 判断是否有任何数据）。 */
export function useEtfLatestDate() {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: EtfLatestDateData
  }>(
    ['etfLatestDate'],
    () =>
      etfMonitorApi
        .getLatestDate()
        .then(
          (res) =>
            res.data as unknown as {
              success: boolean
              data: EtfLatestDateData
            }
        ),
    SWR_OPTIONS
  )

  return {
    latestDate: data?.data?.tradeDate ?? null,
    hasData: data?.data?.hasData ?? false,
    isLoading,
    isError: error,
    mutate,
  }
}
