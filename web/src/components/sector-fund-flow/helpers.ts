/**
 * 板块资金流展示辅助函数（plan-03）
 *
 * 金额单位：后端 inflow/outflow/netInflow 单位为「亿元」（akshare 同花顺即时资金流
 * 原始口径，DB 模型 Numeric(15,2) 即此量级），前端直接以亿元展示，保留 2 位小数。
 * 百分比：后端 changePercent/leadingStockChange 为百分比数值（如 3.21 表示 3.21%）。
 */

/**
 * 资金额格式化（单位已是亿元）。
 * - null/undefined：返回 '-'
 * - 否则：X.XX 亿（带千分位整数部分）
 */
export function formatAmount(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  return `${value.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}亿`
}

/** 净额带正负号格式化（单位已是亿元），null → '-' */
export function formatSignedAmount(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}亿`
}

/**
 * 百分比格式化（后端数值即百分比，如 3.21 → "3.21%"）。
 * null/undefined → '-'。
 */
export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

/**
 * A 股惯例涨跌色 class：正值红、负值绿、零/空中性。
 * 对应 tailwind 色：rise（红 hsl 8）、fall（绿 hsl 153）。
 */
export function getAmountColorClass(value: number | null | undefined): string {
  if (value === null || value === undefined || value === 0) return 'text-foreground'
  return value > 0 ? 'text-rise' : 'text-fall'
}

/** 价格格式化（元），null → '-' */
export function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  return value.toFixed(2)
}

/** 采样时间 → HH:mm（盘中交易时段横轴刻度），无效返回原值 */
export function formatSampleTime(sampleTime: string): string {
  // ISO 字符串或 "YYYY-MM-DDTHH:MM:SS"
  const dt = new Date(sampleTime)
  if (Number.isNaN(dt.getTime())) return sampleTime
  const hh = String(dt.getHours()).padStart(2, '0')
  const mm = String(dt.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}
