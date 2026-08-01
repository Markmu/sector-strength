/**
 * 涨停专题（连板天梯）前端契约类型
 *
 * 对应后端 src/api/v1/limit.py，响应字段经 _dict_to_camel 转 camelCase。
 * query 参数保持 snake_case（trade_date / end_date / days / limit_type /
 * page / page_size）。
 */

/** 涨跌停类型：U涨停 / D跌停 / Z炸板 */
export type LimitType = 'U' | 'D' | 'Z'

/** 涨停个股明细（limit_list_d 单条） */
export interface LimitStockItem {
  /** TS 代码（如 603221.SH） */
  tsCode: string
  /** 股票名称 */
  name: string
  /** 申万行业（所属板块展示） */
  industry: string | null
  /** 收盘价（元） */
  close: number | null
  /** 涨跌幅(%) */
  pctChg: number | null
  /** 封单成交额（元） */
  fdAmount: number | null
  /** 首次封板时间（HH:MM:SS） */
  firstTime: string | null
  /** 最后封板时间（HH:MM:SS） */
  lastTime: string | null
  /** 炸板次数（0=未炸板） */
  openTimes: number | null
  /** 连板统计描述（如"7天4板"） */
  upStat: string | null
  /** 连板数（1=首板） */
  limitTimes: number | null
  /** 涨跌停类型 */
  limitType: LimitType | null
  /** 成交额（元） */
  amount: number | null
}

/** 涨停最强板块统计（limit_cpt_list 单条） */
export interface LimitCptItem {
  /** 板块名称 */
  name: string
  /** 涨停家数 */
  upNums: number | null
  /** 连板家数 */
  consNums: number | null
  /** 连续活跃天数 */
  days: number | null
  /** 板块连板统计描述（如"5天5板"） */
  upStat: string | null
  /** 板块涨跌幅(%) */
  pctChg: number | null
}

/** 单日天梯的某一层（按连板数分层） */
export interface LimitLadderLevel {
  /** 连板数 */
  limitTimes: number
  /** 该层个股数 */
  count: number
  /** 该层个股列表 */
  stocks: LimitStockItem[]
}

/** 单日天梯响应 data */
export interface LimitLadderData {
  /** 是否有数据 */
  hasData: boolean
  /** 实际交易日（YYYY-MM-DD），无数据为 null */
  tradeDate: string | null
  /** 涨停最强板块统计（按 rank 升序） */
  sectors: LimitCptItem[]
  /** 按连板数降序分层的涨停个股 */
  levels: LimitLadderLevel[]
}

/** 多日统计单行 */
export interface LimitMultiDaysItem {
  /** 交易日（YYYY-MM-DD） */
  tradeDate: string
  /** 涨停总数 */
  totalUp: number
  /** 当日最高连板数 */
  maxTimes: number
  /** 各连板高度家数（动态键 limitUp2 / limitUp3 ...） */
  [key: string]: number | string
}

/** 多日统计响应 data */
export interface LimitMultiDaysData {
  /** 是否有数据 */
  hasData: boolean
  /** 截止交易日（YYYY-MM-DD） */
  endDate: string | null
  /** 回溯天数 */
  days: number
  /** 每日统计（按日期降序） */
  items: LimitMultiDaysItem[]
}

/** 列表视图响应 data */
export interface LimitListData {
  /** 是否有数据 */
  hasData: boolean
  /** 实际交易日（YYYY-MM-DD） */
  tradeDate: string | null
  /** 个股列表 */
  items: LimitStockItem[]
  /** 总数 */
  total: number
  /** 当前页码 */
  page: number
  /** 每页数量 */
  pageSize: number
}

/** 最新交易日响应 data */
export interface LimitLatestDateData {
  /** 是否有数据 */
  hasData: boolean
  /** 最新交易日（YYYY-MM-DD），无数据为 null */
  tradeDate: string | null
}
