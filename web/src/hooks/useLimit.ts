/**
 * 涨停专题（连板天梯）SWR Hooks
 *
 * 参照 useEtfMonitor.ts 模式：SWR 数组 key + fetcher 调 limitApi。
 * 深路径导入本文件，不改 hooks/index.ts。
 */
import useSWR from 'swr'
import { limitApi } from '@/lib/api'
import type {
  LimitLadderData,
  LimitMultiDaysData,
  LimitListData,
  LimitLatestDateData,
  LimitType,
} from '@/types/limitTypes'

const SWR_OPTIONS = {
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  dedupingInterval: 30000,
} as const

// ============== 单日连板天梯 ==============

export interface UseLimitLadderParams {
  tradeDate?: string | null
}

/** 单日连板天梯（板块统计 + 分层个股）。始终启用。 */
export function useLimitLadder(params: UseLimitLadderParams) {
  const { data, error, isLoading, mutate, isValidating } = useSWR<{
    success: boolean
    data: LimitLadderData
  }>(
    ['limitLadder', params.tradeDate ?? null],
    () =>
      limitApi
        .getLadder({ tradeDate: params.tradeDate })
        .then(
          (res) =>
            res.data as unknown as {
              success: boolean
              data: LimitLadderData
            }
        ),
    SWR_OPTIONS
  )

  return {
    ladder: data?.data ?? null,
    isLoading,
    isValidating,
    isError: error,
    mutate,
  }
}

// ============== 多日连板统计 ==============

export interface UseLimitMultiDaysParams {
  endDate?: string | null
  days?: number
}

/** 多日连板统计表格。始终启用。 */
export function useLimitMultiDays(params: UseLimitMultiDaysParams) {
  const { data, error, isLoading, mutate, isValidating } = useSWR<{
    success: boolean
    data: LimitMultiDaysData
  }>(
    ['limitMultiDays', params.endDate ?? null, params.days ?? 5],
    () =>
      limitApi
        .getMultiDays({ endDate: params.endDate, days: params.days })
        .then(
          (res) =>
            res.data as unknown as {
              success: boolean
              data: LimitMultiDaysData
            }
        ),
    SWR_OPTIONS
  )

  return {
    multiDays: data?.data ?? null,
    isLoading,
    isValidating,
    isError: error,
    mutate,
  }
}

// ============== 涨停个股列表（分页）==============

export interface UseLimitListParams {
  tradeDate?: string | null
  limitType?: LimitType | null
  page?: number
  pageSize?: number
}

/** 当日涨停个股平铺列表（分页）。始终启用。 */
export function useLimitList(params: UseLimitListParams) {
  const { data, error, isLoading, mutate, isValidating } = useSWR<{
    success: boolean
    data: LimitListData
  }>(
    [
      'limitList',
      params.tradeDate ?? null,
      params.limitType ?? null,
      params.page ?? 1,
      params.pageSize ?? 50,
    ],
    () =>
      limitApi
        .getList({
          tradeDate: params.tradeDate,
          limitType: params.limitType,
          page: params.page,
          pageSize: params.pageSize,
        })
        .then(
          (res) =>
            res.data as unknown as {
              success: boolean
              data: LimitListData
            }
        ),
    SWR_OPTIONS
  )

  return {
    list: data?.data ?? null,
    isLoading,
    isValidating,
    isError: error,
    mutate,
  }
}

// ============== 最新交易日 ==============

/** 最新有数据交易日。 */
export function useLimitLatestDate() {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: LimitLatestDateData
  }>(
    ['limitLatestDate'],
    () =>
      limitApi
        .getLatestDate()
        .then(
          (res) =>
            res.data as unknown as {
              success: boolean
              data: LimitLatestDateData
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
