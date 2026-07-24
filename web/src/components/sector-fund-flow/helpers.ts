/**
 * 板块资金流展示辅助函数（plan-03）
 *
 * 金额单位：后端 inflow/outflow/netInflow 单位为元（akshare 原始），
 * 前端统一换算成"亿"展示（A 股资金流惯例），保留 2 位小数。
 * 百分比：后端 changePercent/leadingStockChange 为百分比数值（如 3.21 表示 3.21%）。
 */

/** 亿元换算阈值：|value| >= 1e8 显示"亿"，否则显示"万" */
const YI = 1e8
const WAN = 1e4

/**
 * 资金额格式化（元 → 亿/万）。
 * - |v| >= 1亿：显示"X.XX亿"
 * - |v| >= 1万：显示"X.XX万"
 * - 否则：显示原值（带千分位）
 * - null/undefined：返回 '—'
 */
export function formatAmount(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const abs = Math.abs(value)
  if (abs >= YI) {
    return `${(value / YI).toFixed(2)}亿`
  }
  if (abs >= WAN) {
    return `${(value / WAN).toFixed(2)}万`
  }
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

/** 净额带正负号格式化（亿/万），null → '—' */
export function formatSignedAmount(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const abs = Math.abs(value)
  const sign = value > 0 ? '+' : ''
  if (abs >= YI) {
    return `${sign}${(value / YI).toFixed(2)}亿`
  }
  if (abs >= WAN) {
    return `${sign}${(value / WAN).toFixed(2)}万`
  }
  return `${sign}${value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`
}

/**
 * 百分比格式化（后端数值即百分比，如 3.21 → "3.21%"）。
 * null/undefined → '—'。
 */
export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
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

/** 价格格式化（元），null → '—' */
export function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
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
