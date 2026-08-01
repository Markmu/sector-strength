/**
 * ETF 监控前端契约类型
 *
 * 对应架构 §7.2 输出视角 Schema（camelCase）。后端路由 _dict_to_camel 已把
 * snake_case 键转为 camelCase，这里只描述前端最终拿到的业务对象。
 *
 * query 参数保持 snake_case（trade_date / sort_by / target_type /
 * target_code / metric / days / end_date / page / page_size），响应字段 camelCase
 * （hasData / tradeDate / indexCode / indexName / etfCount / totalShare /
 * totalShareChange / totalNetInflow / tsCode / unitNav / share / shareChange /
 * netInflow / changePercent 等）。
 *
 * 特例（架构 §7.6）：sort_by 与 metric 参数的「值」用 camelCase（netInflow /
 * shareChange / share），与后端取值一致，不要下划线化。
 */

/**
 * 排序字段（camelCase 值，架构 §7.6 特例）。
 * 与后端 sort_by 取值一一对应：
 * - netInflow：净流入额（指数下所有 ETF 加总）
 * - shareChange：份额变化
 * - share：当前份额
 */
export type EtfSortBy = 'netInflow' | 'shareChange' | 'share'

/**
 * 趋势度量（camelCase 值，架构 §7.6 特例）。
 * - share：份额
 * - netInflow：净流入额
 */
export type EtfTrendMetric = 'share' | 'netInflow'

/** 趋势对象类型 */
export type EtfTargetType = 'index' | 'etf'

/** 趋势区间天数（与后端 days 白名单一致） */
export type EtfTrendDays = 7 | 30 | 90

/**
 * 指数排行单项。
 * 指数级数值 = 该指数下所有 ETF 加总（ADR-4）。按 index_code 聚合。
 */
export interface EtfIndexRankingItem {
  /** 跟踪指数代码（官方 etf_basic 接口 index_code，如 000300.SH） */
  indexCode: string
  /** 跟踪指数名（官方 etf_basic 接口 index_name，如 沪深300） */
  indexName: string
  /** 该指数下 ETF 只数 */
  etfCount: number
  /** 合计份额（亿份，ADR-7：存储万份 / 输出亿份 ÷10000），无数据为 null */
  totalShare: number | null
  /** 合计份额变化（亿份），无数据为 null */
  totalShareChange: number | null
  /** 合计净流入额（亿元，net_inflow = share_change × 单位净值 估算），无数据为 null */
  totalNetInflow: number | null
  /** 合计规模（亿元，share × unit_nav 聚合后 ÷10000 转亿元），无数据为 null */
  totalSize: number | null
}

/** 指数排行响应 data */
export interface EtfIndexRankingsData {
  /** 是否有数据（false 时 items 为空） */
  hasData: boolean
  /** 实际交易日（YYYY-MM-DD），无数据为 null */
  tradeDate: string | null
  items: EtfIndexRankingItem[]
  total: number
  page: number
  pageSize: number
}

/**
 * 指数明细单项（AC-04：展开指数查看 ETF 明细）。
 */
export interface EtfDetailItem {
  /** ETF 代码（如 510300.SH） */
  tsCode: string
  /** ETF 名称 */
  name: string
  /** 单位净值（元） */
  unitNav: number | null
  /** 份额（亿份） */
  share: number | null
  /** 合计份额（亿元，total_size ÷10000） */
  totalSize: number | null
  /** 份额变化（亿份） */
  shareChange: number | null
  /** 净流入额（亿元） */
  netInflow: number | null
  /** 涨跌幅（百分比） */
  changePercent: number | null
}

/** 指数明细响应 data */
export interface EtfIndexDetailData {
  /** 是否有数据（false 时 items 为空） */
  hasData: boolean
  items: EtfDetailItem[]
}

/** 趋势序列单个采样点（AC-06/07/08/09） */
export interface EtfTrendPoint {
  /** 交易日（YYYY-MM-DD） */
  tradeDate: string
  /** 度量值（份额=亿份 / 净流入额=亿元），无数据为 null */
  value: number | null
}

/** 历史趋势响应 data */
export interface EtfTrendData {
  /** 是否有数据（false 时 series 为空） */
  hasData: boolean
  /** 度量类型（回显，share / netInflow） */
  metric: string
  /** 单位文本（如 "亿份" / "亿元"） */
  unit: string
  /** 采样序列（按 tradeDate 升序） */
  series: EtfTrendPoint[]
}

/** 最新交易日响应 data */
export interface EtfLatestDateData {
  /** 是否有数据（false 时 tradeDate 为 null） */
  hasData: boolean
  /** 最新交易日（YYYY-MM-DD），无数据为 null */
  tradeDate: string | null
}
