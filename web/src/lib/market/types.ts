/**
 * 市场指数类型定义
 */

export interface MarketIndexData {
  index: {
    value: number
    change: number
    timestamp: string
    color: string  // 指数颜色（基于强度值）
  }
  stats: {
    totalSectors: number
    upSectors: number
    downSectors: number
    neutralSectors: number
  }
  trend: Array<{
    timestamp: string
    value: number
  }>
}

export interface MarketIndexResponse {
  success: boolean
  data: MarketIndexData
}
