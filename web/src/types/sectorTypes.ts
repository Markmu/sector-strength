/**
 * 板块类型统一定义
 *
 * 集中管理所有板块类型的常量映射，作为前端唯一的类型真相源。
 * 与后端 server/src/services/data_acquisition/sector_types.py 保持一致。
 */

// 所有合法的板块类型 key
export const SECTOR_TYPES = [
  'industry',
  'concept',
  'region',
] as const

export type SectorType = (typeof SECTOR_TYPES)[number]

// 内部 key → 简短中文标签
export const SECTOR_TYPE_LABELS: Record<SectorType, string> = {
  industry: '行业',
  concept: '概念',
  region: '地域',
}

// 内部 key → 完整中文显示标签
export const SECTOR_TYPE_DISPLAY: Record<SectorType, string> = {
  industry: '行业板块',
  concept: '概念板块',
  region: '地域板块',
}

// 类型选项数组（用于 UI 遍历渲染）
export const SECTOR_TYPE_OPTIONS: {
  value: SectorType
  label: string
  display: string
}[] = SECTOR_TYPES.map((t) => ({
  value: t,
  label: SECTOR_TYPE_LABELS[t],
  display: SECTOR_TYPE_DISPLAY[t],
}))

/**
 * 基金扎堆分析支持的板块维度子集（行业/概念/地域）。
 *
 * 当前与全量 SECTOR_TYPES 一致；保留独立常量是为了扎堆页有稳定的
 * 维度类型边界，便于后续在全量类型调整时隔离影响。
 */
export const FUND_CROWD_SECTOR_TYPES = [
  'industry',
  'concept',
  'region',
] as const

export type FundCrowdSectorType = (typeof FUND_CROWD_SECTOR_TYPES)[number]

// 扎堆页板块选项（行业/概念/地域）
export const FUND_CROWD_SECTOR_OPTIONS: {
  value: FundCrowdSectorType
  label: string
  display: string
}[] = FUND_CROWD_SECTOR_TYPES.map((t) => ({
  value: t,
  label: SECTOR_TYPE_LABELS[t],
  display: SECTOR_TYPE_DISPLAY[t],
}))

// ============== 板块成分股契约（对齐后端 GET /sectors/{id}/stocks） ==============

/**
 * 成分股列表项。
 *
 * 字段与后端 sectors.py 的 get_sector_stocks 返回 items 一致（snake_case）。
 * 不复用 types/index.ts 的 SectorStock（其字段 sector_id/stock_id/weight 与后端不符）。
 */
export interface SectorStockItem {
  id: string
  symbol: string
  name: string
  current_price: number | null
  market_cap: number | null
  strength_score: number | null
  trend_direction: number | null // 1=上升, 0=横盘, -1=下降
}

/** 分页响应 data（对齐后端 PaginatedData） */
export interface SectorStocksData {
  items: SectorStockItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/** API 整体响应（对齐既有 { success, data } 包裹） */
export interface SectorStocksResponse {
  success: boolean
  data: SectorStocksData
}

/** 成分股表格排序/分页 UI 状态 */
export interface SectorStocksTableState {
  sort_by: 'strength_score' | 'market_cap'
  sort_order: 'asc' | 'desc'
  page: number
  page_size: 20 | 50 | 100
}
