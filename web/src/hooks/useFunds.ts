/**
 * 基金 SWR Hooks
 *
 * 提供基金列表、详情、持仓、反查等数据获取。
 * 默认 30s 重新校验。
 */
import useSWR from 'swr'
import {
  fundsApi,
  type FundListParams,
  type FundListResponse,
  type Fund,
  type PortfolioResponse,
  type ReverseLookupResponse,
} from '@/lib/api'

export type UseFundListParams = FundListParams

export function useFundList(params: UseFundListParams) {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: FundListResponse
  }>(
    ['fundList', params],
    () => fundsApi.getFunds(params).then(res => res.data as unknown as {
      success: boolean
      data: FundListResponse
    }),
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      dedupingInterval: 30000,
    }
  )

  return {
    funds: data?.data?.items || [],
    total: data?.data?.total || 0,
    page: data?.data?.page || params.page || 1,
    pageSize: data?.data?.pageSize || params.pageSize || 20,
    totalPages: data?.data?.totalPages || 0,
    isLoading,
    isError: error,
    mutate,
  }
}

export function useFundDetail(tsCode: string) {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: Fund
  }>(
    tsCode ? ['fundDetail', tsCode] : null,
    () => fundsApi.getFund(tsCode).then(res => res.data as unknown as {
      success: boolean
      data: Fund
    }),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
    }
  )

  return {
    fund: data?.data || null,
    isLoading,
    isError: error,
    mutate,
  }
}

export function useFundPortfolio(
  tsCode: string,
  params?: { page?: number; pageSize?: number }
) {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: PortfolioResponse
  }>(
    tsCode ? ['fundPortfolio', tsCode, params] : null,
    () => fundsApi.getFundPortfolio(tsCode, params).then(res => res.data as unknown as {
      success: boolean
      data: PortfolioResponse
    }),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
    }
  )

  return {
    portfolio: data?.data?.items || [],
    total: data?.data?.total || 0,
    page: data?.data?.page || params?.page || 1,
    pageSize: data?.data?.pageSize || params?.pageSize || 20,
    totalPages: data?.data?.totalPages || 0,
    isPortfolioEmpty: data?.data?.isPortfolioEmpty ?? true,
    hasPortfolio: data?.data?.hasPortfolio ?? false,
    latestReportPeriod: data?.data?.latestReportPeriod || null,
    latestAnnDate: data?.data?.latestAnnDate || null,
    isLoading,
    isError: error,
    mutate,
  }
}

export function useReverseLookup(
  symbol: string,
  params?: { page?: number; pageSize?: number }
) {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: ReverseLookupResponse
  }>(
    symbol ? ['reverseLookup', symbol, params] : null,
    () => fundsApi.reverseLookup(symbol, params).then(res => res.data as unknown as {
      success: boolean
      data: ReverseLookupResponse
    }),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
    }
  )

  return {
    items: data?.data?.items || [],
    total: data?.data?.total || 0,
    page: data?.data?.page || params?.page || 1,
    pageSize: data?.data?.pageSize || params?.pageSize || 20,
    totalPages: data?.data?.totalPages || 0,
    stockName: data?.data?.stockName || null,
    reportPeriod: data?.data?.reportPeriod || null,
    isLoading,
    isError: error,
    mutate,
  }
}
