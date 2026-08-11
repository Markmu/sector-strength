/**
 * 关键指数监控前端契约类型（第 15 期 plan-04）
 *
 * 对应 plan-03 §3 API 响应 Schema（camelCase，后端 _dict_to_camel 转换）。
 *
 * 响应外层统一 { success: boolean, data: {...} }，data 内字段 camelCase：
 * - tsCode / pctChg / peTtm / tradeDate / hasData / concentration 等
 *
 * query 参数保持 snake_case（ts_codes / start_date / end_date / ts_code /
 * index_code / top_n）。
 */

// ===================== /overview 总览 =====================

/** 总览卡片单项（plan-03 §3 #1） */
export interface IndexOverviewItem {
  /** 指数代码（如 000300.SH） */
  tsCode: string
  /** 指数名称（如 沪深300） */
  name: string
  /** 收盘价，无数据为 null */
  close: number | null
  /** 涨跌幅（百分比），无数据为 null */
  pctChg: number | null
  /** 成交额（亿元，后端已 ÷10000 转换），无数据为 null */
  amount: number | null
  /** PE TTM，无估值指数为 null */
  peTtm: number | null
}

/** /overview 响应 data */
export interface IndexOverviewData {
  /** 关注指数卡片列表 */
  indices: IndexOverviewItem[]
  /** 实际交易日（YYYY-MM-DD），无数据为 null */
  tradeDate: string | null
}

// ===================== /trend 多指数走势 =====================

/** 单只指数走势采样点 */
export interface IndexTrendPoint {
  /** 交易日（YYYY-MM-DD） */
  tradeDate: string
  /** 收盘价，无数据为 null */
  close: number | null
}

/** 单只指数走势序列 */
export interface IndexTrendSeries {
  /** 指数代码 */
  tsCode: string
  /** 指数名称 */
  name: string
  /** 采样序列（按 tradeDate 升序） */
  points: IndexTrendPoint[]
}

/** /trend 响应 data */
export interface IndexTrendData {
  /** 是否有数据（false 时 series 为空） */
  hasData: boolean
  /** 多指数序列（最多 6 只，超过后端截断） */
  series: IndexTrendSeries[]
}

// ===================== /valuation 单指数估值 =====================

/** 单指数估值采样点 */
export interface IndexValuationPoint {
  /** 交易日（YYYY-MM-DD） */
  tradeDate: string
  /** PE TTM，无估值指数为 null */
  peTtm: number | null
  /** PB，无估值指数为 null */
  pb: number | null
  /** 换手率（百分比） */
  turnoverRate: number | null
}

/** /valuation 响应 data */
export interface IndexValuationData {
  /** 指数代码（回显） */
  tsCode: string
  /** 采样序列（按 tradeDate 升序），无估值指数为空 */
  points: IndexValuationPoint[]
  /** 是否有估值数据（false 时 points 为空） */
  hasData: boolean
}

// ===================== /weights 成分权重 =====================

/** 权重股单项 */
export interface IndexWeightItem {
  /** 成分股代码（如 600519.SH） */
  conCode: string
  /** 成分股名称（JOIN stocks 取，无匹配为 null → 显示 conCode） */
  name: string | null
  /** 权重百分比 */
  weight: number
}

/** /weights 响应 data */
export interface IndexWeightData {
  /** 指数代码（回显） */
  indexCode: string
  /** 权重数据交易日（YYYY-MM-DD） */
  tradeDate: string | null
  /** 前 N 成分股权重（按 weight 降序） */
  weights: IndexWeightItem[]
  /** 集中度合计 */
  concentration: {
    /** 前 5 合计占比 */
    top5: number
    /** 前 10 合计占比 */
    top10: number
  }
}

// ===================== /watchlist 关注清单 =====================

/** 关注指数单项 */
export interface IndexWatchlistItem {
  /** 指数代码 */
  tsCode: string
  /** 指数名称 */
  name: string
  /** 市场（如 SSE/SZSE/CSI） */
  market: string | null
  /** 是否有估值数据（index_dailybasic 是否有记录） */
  hasValuation: boolean
}

/** /watchlist GET 响应 data */
export interface IndexWatchlistData {
  /** 关注指数列表 */
  watchlist: IndexWatchlistItem[]
}

/** /watchlist PUT 响应 data */
export interface IndexWatchlistUpdateData {
  /** 更新的指数条数 */
  updated: number
}
