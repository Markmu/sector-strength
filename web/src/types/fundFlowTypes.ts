/**
 * 板块资金流前端契约类型（plan-03，13 期）
 *
 * 对应架构 §7.2 响应视角（camelCase）。后端路由 _dict_to_camel 已把
 * snake_case 键转为 camelCase，这里只描述前端最终拿到的业务对象。
 *
 * query 参数保持 snake_case（sector_type / trade_date / sort_by / page_size），
 * 响应字段 camelCase（netInflow / sectorName / sampleTime / hasData / tradeDate 等）。
 */

/** 排序字段白名单（与后端 _SORT_COLUMN_MAP 一致） */
export type FundFlowSortBy = 'net_inflow' | 'inflow' | 'outflow'

/** 排序方向 */
export type FundFlowOrder = 'asc' | 'desc'

/**
 * 资金流排行榜单项（最新采样点）。
 * sectorId 通过 LEFT JOIN sectors 按 sector_name 匹配取，匹配不上为 null。
 */
export interface FundFlowRankingItem {
  /** 全局排名（按当前排序结果 offset + 页内序号 + 1） */
  rank: number
  /** 板块名（sector_fund_flow.sector_name） */
  sectorName: string
  /** 关联板块主键 id，null 表示未匹配到 sectors 表（不可跳转） */
  sectorId: number | null
  /** 涨跌幅（百分比） */
  changePercent: number | null
  /** 流入额（元） */
  inflow: number | null
  /** 流出额（元） */
  outflow: number | null
  /** 净额 = 流入 - 流出（元） */
  netInflow: number | null
  /** 公司家数 */
  companyCount: number | null
  /** 领涨股名称 */
  leadingStock: string | null
  /** 领涨股涨跌幅（百分比） */
  leadingStockChange: number | null
  /** 领涨股最新价 */
  currentPrice: number | null
}

/** 排行榜响应 data */
export interface FundFlowRankingsData {
  /** 是否有数据（false 时 items 为空） */
  hasData: boolean
  /** 实际交易日（YYYY-MM-DD），无数据为 null */
  tradeDate: string | null
  items: FundFlowRankingItem[]
  total: number
  page: number
  pageSize: number
}

/** 盘中变化曲线单个采样点 */
export interface FundFlowSeriesPoint {
  /** 采样时间（ISO 字符串，交易时段内） */
  sampleTime: string
  /** 净额（元） */
  netInflow: number | null
}

/** 单板块盘中变化序列 */
export interface FundFlowSeriesItem {
  /** 板块名 */
  sectorName: string
  /** 采样点（按 sample_time 升序） */
  data: FundFlowSeriesPoint[]
}

/** 盘中变化曲线响应 data */
export interface FundFlowTimeseriesData {
  /** 是否有数据（false 时 series 为空） */
  hasData: boolean
  /** 实际交易日（YYYY-MM-DD），无数据为 null */
  tradeDate: string | null
  series: FundFlowSeriesItem[]
}

/** 最新交易日响应 data */
export interface FundFlowLatestDateData {
  /** 最新交易日（YYYY-MM-DD），无数据为 null */
  latestDate: string | null
}
