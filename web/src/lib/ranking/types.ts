// 排名列表类型定义 - 匹配后端 API 返回格式

export type TrendDirection = 1 | 0 | -1  // 1=上升, 0=横盘, -1=下降

export interface RankingItem {
  id: string
  name: string
  code: string
  strength_score: number
  trend_direction: TrendDirection
  rank: number
}

export interface RankingResponse {
  success: boolean
  data: RankingItem[]
  total: number
  top_n: number
}

export type SortBy = 'strength' | 'trend'
export type SortOrder = 'asc' | 'desc'

export interface RankingConfig {
  sortBy: SortBy
  sortOrder: SortOrder
  topN: number
}
