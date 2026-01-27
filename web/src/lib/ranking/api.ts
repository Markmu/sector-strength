// 排名 API 客户端
import { apiClient } from '../api'
import type { RankingResponse, SortOrder } from './types'

export interface RankingParams {
  top_n?: number
  order?: SortOrder
  sector_type?: 'industry' | 'concept'
  sector_id?: string
}

// 板块排名 API
export const sectorsRankingApi = {
  getRankings: (params: RankingParams = {}) => {
    const { top_n = 10, order = 'desc', sector_type } = params
    return apiClient.get<RankingResponse>('/rankings/sectors', {
      top_n,
      order,
      ...(sector_type && { sector_type }),
    })
  },
}

// 个股排名 API
export const stocksRankingApi = {
  getRankings: (params: RankingParams = {}) => {
    const { top_n = 20, order = 'desc', sector_id } = params
    return apiClient.get<RankingResponse>('/rankings/stocks', {
      top_n,
      order,
      ...(sector_id && { sector_id }),
    })
  },
}
