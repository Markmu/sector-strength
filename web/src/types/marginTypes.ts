/**
 * 全市场融资融券前端契约类型（第 17 期 plan-07）
 *
 * 对应后端 GET /api/v1/margin/trend（plan-06 §实现规格 / 架构 §7.2）。
 *
 * 响应外层统一 { success: boolean; data: {...} }，data 内字段经后端
 * _dict_to_camel 转 camelCase、Decimal → float、date → ISO 字符串。
 *
 * 存储单位口径与架构一致：元 / 股原始值，前端显示层 ÷1e8 转亿（亿元）。
 * rqmcl 为股口径，不入曲线图，仅保留数据契约（spec D2 / plan-07 交接上下文）。
 */

/** 全市场单日两融指标点（plan-06 §1）。缺失日六指标全 null（不补 0 / 前值，AC-5）。 */
export interface MarginPoint {
  /** 交易日（YYYY-MM-DD ISO 字符串） */
  tradeDate: string
  /** 融资余额（元原始值，显示层 ÷1e8 转亿元） */
  rzye: number | null
  /** 融券余额（元原始值，显示层 ÷1e8 转亿元） */
  rqye: number | null
  /** 融资买入额（元原始值，显示层 ÷1e8 转亿元） */
  rzmre: number | null
  /** 融资偿还额（元原始值，显示层 ÷1e8 转亿元） */
  rzche: number | null
  /** 融券卖出量（股；不入图，仅保留数据契约） */
  rqmcl: number | null
  /** 两融合计余额（元原始值，显示层 ÷1e8 转亿元；服务层 = rzye + rqye 重算口径） */
  rzrqye: number | null
}

/** 两融趋势范围（30/90/250，与后端 Query pattern 一致） */
export type MarginRange = 30 | 90 | 250

/** /trend 响应 data（plan-06 §1 MarginTrendData） */
export interface MarginTrendData {
  /** 最近成功结果日（自尾向头第一个有值点，不伪装今天）；全空为 null */
  latest: MarginPoint | null
  /** 趋势点序列（升序，缺失日为 null 非 0） */
  points: MarginPoint[]
  /** 当前请求范围 */
  range: MarginRange
  /** 任一点 rzye 为 null → true（缺口断线提示依据） */
  hasMissingDates: boolean
}

// ===================== 同步任务结果（第 17 期 plan-08）=====================
//
// 以下两类对应后端范围同步任务 result（plan-04 handler 约定）。
// 后端 handler 构造 result 时键全 camelCase，AsyncTask.to_dict() 原样透传，
// 不经 _dict_to_camel 二次转换 —— 前端直消费、无键转换层。

/** 单交易日同步结果（两融无四类计数，仅成败与原因）。 */
export interface MarginDateResult {
  /** 交易日（YYYY-MM-DD ISO 字符串） */
  tradeDate: string
  /** 当日处理状态：成功 / 失败 */
  status: 'success' | 'failed'
  /** 失败原因（仅 failed 有） */
  reason?: string
}

/** 范围同步任务聚合结果（plan-08 消费；result 键 camelCase 直消费）。 */
export interface MarginTaskResult {
  /** 成功交易日数 */
  successCount: number
  /** 跳过交易日数（非交易日守卫） */
  skippedCount: number
  /** 失败交易日数 */
  failedCount: number
  /** 逐日同步结果 */
  dateResults: MarginDateResult[]
  /** 未处理日期（取消/超时/重启恢复遗留） */
  unprocessedDates: string[]
}
