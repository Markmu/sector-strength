/**
 * 全市场量价指标前端契约类型（第 16 期 plan-07）
 *
 * 对应后端 GET /api/v1/market-metrics/trend（plan-06 §3 / 架构 §7.2 / §6.4.2）。
 *
 * 响应外层统一 { success: boolean; data: {...} }，data 内字段经后端
 * _dict_to_camel 转 camelCase、Decimal → float、date → ISO 字符串。
 *
 * 存储单位口径与架构一致：股 / 元原始值，前端显示层 ÷1e8 转亿（amountYuan/亿元、
 * volumeShares/亿股）；averagePrice 为元（卡片展示 2 位小数）。
 */

/** 全市场单日量价指标点（架构 §7.2）。缺失日五项指标全 null（不补 0 / 前值，AC-06）。 */
export interface MarketMetricPoint {
  /** 交易日（YYYY-MM-DD ISO 字符串） */
  tradeDate: string
  /** 成交量（股原始值，显示层 ÷1e8 转亿股） */
  volumeShares: number | null
  /** 成交额（元原始值，显示层 ÷1e8 转亿元） */
  amountYuan: number | null
  /** 全市场平均价（元，2 位小数） */
  averagePrice: number | null
  /** 当日正常交易股票数 */
  finalStockCount: number | null
  /** 当日停牌股票数 */
  suspendedStockCount: number | null
}

/** 量价趋势范围（30/90/250，与后端 Query pattern 一致） */
export type MarketMetricsRange = 30 | 90 | 250

/** /trend 响应 data（架构 §7.2 MarketMetricsTrendData） */
export interface MarketMetricsTrendData {
  /** 最近成功结果日（自尾向头第一个有值点，不伪装今天）；全空为 null */
  latest: MarketMetricPoint | null
  /** 趋势点序列（升序，缺失日为 null 非 0） */
  points: MarketMetricPoint[]
  /** 当前请求范围 */
  range: MarketMetricsRange
  /** 任一点 volumeShares 为 null → true（缺口断线提示依据） */
  hasMissingDates: boolean
}

/** 面板可选指标（AC-04 指标切换） */
export type MetricKey = 'amountYuan' | 'volumeShares' | 'averagePrice'

// ===================== 同步任务结果（第 16 期 plan-08）=====================
//
// 以下两类对应后端范围同步任务 result（plan-05 §2 step6 约定）。
// 后端 handler 构造 result 时键全 camelCase，AsyncTask.to_dict() 原样透传，
// 不经 _dict_to_camel 二次转换 —— 前端直消费、无键转换层。

/** 单交易日完整性校验结果（架构 §6.2.7-8 / §7.2）。 */
export interface MarketMetricsDateResult {
  /** 交易日（YYYY-MM-DD ISO 字符串） */
  tradeDate: string
  /** 当日处理状态：成功 / 失败（完整性校验未通过） */
  status: 'success' | 'failed'
  /** 应参与股票数（L/D/P/G 生命周期构造的参与集合大小） */
  expected: number
  /** 当日正常行情命中数（采集到的 daily 条数） */
  daily: number
  /** 全天停牌股票数（suspend_d 明确整日停牌） */
  suspended: number
  /** 最终参与计算股票数（daily，停牌补值不计入成交口径；失败日为 0） */
  final: number
  /** 失败原因（仅 failed 有；前端截断展示，AC-07） */
  reason?: string
}

/** 范围同步任务聚合结果（plan-05 §2 step6 / 架构 §7.2）。 */
export interface MarketMetricsTaskResult {
  /** 成功交易日数 */
  successCount: number
  /** 跳过交易日数（非交易日守卫，AC-09） */
  skippedCount: number
  /** 失败交易日数（完整性校验未通过，AC-07） */
  failedCount: number
  /** 逐日完整性结果（默认最近在前，前端可展开四类计数） */
  dateResults: MarketMetricsDateResult[]
  /** 未处理日期（取消/超时/重启恢复遗留，AC-07 恢复语义） */
  unprocessedDates: string[]
}
