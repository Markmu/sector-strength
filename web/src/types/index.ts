import { z } from 'zod'

// 热力图 Zod Schema 用于输入验证
export const HeatmapSectorSchema = z.object({
  id: z.string(),
  name: z.string(),
  value: z.number().min(0).max(100),
  color: z.string().regex(/^#[0-9A-Fa-f]{6}$/),
})

export const HeatmapDataSchema = z.object({
  sectors: z.array(HeatmapSectorSchema),
  timestamp: z.string(),
})

export const HeatmapResponseSchema = z.object({
  success: z.boolean(),
  data: HeatmapDataSchema,
})

// 基础类型
export interface BaseEntity {
  id?: string
  created_at?: string
  updated_at?: string
}

// 股票相关类型
export interface Stock extends BaseEntity {
  code: string
  name: string
  market?: string
  industry?: string
  area?: string
  pe?: number
  outstanding?: number
  total_assets?: number
  liquid_assets?: number
  fixed_assets?: number
  reserved?: number
  reserved_per_share?: number
  eps?: number
  bvps?: number
  pb?: number
  time_to_market?: string
}

// 股票筛选器类型
export interface StockFilter {
  sector?: string
  search?: string
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

// 板块相关类型
export interface Sector extends BaseEntity {
  code: string
  name: string
  type: 'industry' | 'concept'
  parent_code?: string
  level?: number
  description?: string
  strength_score?: number
  trend_direction?: number
}

// 市场数据类型
export interface DailyMarketData extends BaseEntity {
  stock_id: string
  trade_date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  turnover: number
  turnover_rate: number
  pe_ratio?: number
  pb_ratio?: number
}

// 强度得分类型
export interface StrengthScore extends BaseEntity {
  stock_id?: string
  sector_id?: string
  period: string // '5d', '10d', '20d', '30d', '60d'
  score: number
  rank?: number
  percentile?: number
  calculated_at: string
}

// 强度筛选器类型
export interface StrengthFilter {
  sector_id?: string
  stock_id?: string
  period?: string
  date_from?: string
  date_to?: string
}

// 均线数据类型
export interface MovingAverageData extends BaseEntity {
  stock_id: string
  period: number // 5, 10, 20, 30, 60
  date: string
  price: number
}

// 周期配置类型
export interface PeriodConfig extends BaseEntity {
  code: string
  name: string
  days: number
  description?: string
  enabled: boolean
  sort_order?: number
}

// 板块-股票关联类型
export interface SectorStock extends BaseEntity {
  sector_id: string
  stock_id: string
  weight?: number
}

// API 响应类型
export interface PaginatedResponse<T> {
  data: T[]
  total: number
  skip: number
  limit: number
  hasMore: boolean
}

// 组件 Props 类型
export interface BaseComponentProps {
  className?: string
  children?: React.ReactNode
}

// 表单相关类型
export interface FormFieldProps {
  label?: string
  placeholder?: string
  required?: boolean
  disabled?: boolean
  error?: string
}

// 图表相关类型
export interface ChartDataPoint {
  x: string | number
  y: number
  label?: string
}

export interface ChartConfig {
  title?: string
  xAxis?: {
    label?: string
    format?: (value: any) => string
  }
  yAxis?: {
    label?: string
    format?: (value: any) => string
    min?: number
    max?: number
  }
  color?: string
}

// 筛选器类型
export interface FilterOption {
  value: string | number
  label: string
}

export interface DateRange {
  start?: string
  end?: string
}

// 排序类型
export interface SortOption {
  field: string
  direction: 'asc' | 'desc'
}

// 分页类型
export interface Pagination {
  skip: number
  limit: number
  total?: number
}

// UI 状态类型
export interface LoadingState {
  isLoading: boolean
  error?: string | null
}

// 表格相关类型
export interface TableColumn<T = any> {
  key: keyof T
  title: string
  width?: number | string
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
  render?: (value: any, record: T) => React.ReactNode
}

// 导出所有类型
// export * from './api'
// export * from './chart'

// 热力图相关类型
export interface HeatmapSector {
  id: string
  name: string
  value: number        // 强度得分 (0-100)
  color: string        // 后端计算的颜色
}

export interface HeatmapData {
  sectors: HeatmapSector[]
  timestamp: string
}

export interface HeatmapResponse {
  success: boolean
  data: HeatmapData
}

export interface HeatmapConfig {
  refreshInterval: number  // ms，默认 5000
  minBlockSize: number     // 最小区块大小
}

// 板块分析图表相关类型
export interface SectorStrengthHistoryPoint {
  date: string
  score: number | null
  short_term_score: number | null
  medium_term_score: number | null
  long_term_score: number | null
  current_price: number | null
}

export interface SectorStrengthHistoryResponse {
  sector_id: string
  sector_name: string
  data: SectorStrengthHistoryPoint[]
}

export interface SectorMAHistoryPoint {
  date: string
  current_price: number | null
  ma5: number | null
  ma10: number | null
  ma20: number | null
  ma30: number | null
  ma60: number | null
  ma90: number | null
  ma120: number | null
  ma240: number | null
}

export interface SectorMAHistoryResponse {
  sector_id: string
  sector_name: string
  data: SectorMAHistoryPoint[]
}

// 时间范围选项
export type TimeRangeOption = '1w' | '1m' | '2m' | '3m' | '6m' | '1y' | 'custom'

export interface TimeRangeConfig {
  label: string
  days: number
  value: TimeRangeOption
}

// 均线显示选项
export type MAPeriod = 'ma5' | 'ma10' | 'ma20' | 'ma30' | 'ma60' | 'ma90' | 'ma120' | 'ma240'

export interface MAConfig {
  key: MAPeriod
  label: string
  color: string
  lineType: 'solid' | 'dashed' | 'dotted'
  defaultVisible: boolean
}

// 金叉/死叉点
export interface CrossPoint {
  date: string
  type: 'golden' | 'death'
  value: number
}