/**
 * ETF 监控展示辅助函数（plan-05）
 *
 * 仿 sector-fund-flow/helpers.ts（src/components/sector-fund-flow/helpers.ts）。
 *
 * 单位口径（与 etfMonitorTypes.ts / 架构 §7.2 一致）：
 * - share / totalShare / totalShareChange：亿份（ADR-7：存储万份 / 输出亿份 ÷10000）
 * - netInflow / totalNetInflow：亿元（share_change × 单位净值 估算）
 * - changePercent：百分比数值（如 0.85 表示 0.85%）
 * - unitNav：元（单位净值）
 *
 * 首版 change_percent 可能因数据源 fund_daily 不可用而为 null（plan-01 §6 风险），
 * formatPercent 对 null 容错（显示 "-"）。
 */

/**
 * 份额格式化（单位已是亿份，正值展示）。
 * - null/undefined：返回 '-'
 * - 否则：X.XX 亿份（带千分位整数部分）
 */
export function formatShare(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  return `${value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}亿份`
}

/**
 * 正数金额格式化（规模「亿元」等存量指标，不带正负号）。
 * - null/undefined：返回 '-'
 * - 否则：X.XX 亿元（带千分位整数部分）
 */
export function formatAmount(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  return `${value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}亿元`
}

/**
 * 带正负号格式化（净流入额「亿元」/ 份额变化「亿份」共用，均带正负色标）。
 * - null/undefined：返回 '-'
 * - isPositive=true 时强制加 '+' 号（用于明确正负语义的场景）
 *
 * 默认按 value 自身符号决定正负（value>0 自动补 '+'）。
 */
export function formatSignedAmount(
  value: number | null | undefined,
  unit: '亿元' | '亿份' = '亿元'
): string {
  if (value === null || value === undefined) return '-'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}${unit}`
}

/**
 * 百分比格式化（后端数值即百分比，如 0.85 → "0.85%"）。
 * null/undefined → '-'（首版 change_percent 可能 null，容错）。
 */
export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

/** 净值格式化（元），保留三位小数，null → '-' */
export function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  return value.toFixed(3)
}

/**
 * A 股惯例涨跌色 class：正值红、负值绿、零/空中性。
 * 对应 tailwind 色：rise（红）、fall（绿）。沿用项目"红涨绿跌"惯例。
 */
export function getAmountColorClass(value: number | null | undefined): string {
  if (value === null || value === undefined || value === 0) return 'text-foreground'
  return value > 0 ? 'text-rise' : 'text-fall'
}
