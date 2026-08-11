/**
 * 关键指数监控展示辅助函数（第 15 期 plan-04）
 *
 * 仿 etf-monitor/helpers.ts（src/components/etf-monitor/helpers.ts）范式，
 * 沿用项目"红涨绿跌"惯例（text-rise 红 / text-fall 绿）。
 *
 * 单位口径（与 indexMonitorTypes.ts / plan-03 §3 一致）：
 * - amount：亿元（后端 plan-03 Task 2 已 ÷10000 转亿元输出，前端不再除）
 * - pctChg：百分比数值（如 0.85 表示 0.85%）
 * - peTtm / pb：倍数
 * - close：指数点位
 */

/**
 * A 股惯例涨跌色 class：正值红、负值绿、零/空中性。
 * 对应 tailwind 色：rise（红）、fall（绿）。沿用项目"红涨绿跌"惯例。
 */
export function getChangeColor(pctChg: number | null | undefined): string {
  if (pctChg === null || pctChg === undefined || pctChg === 0)
    return 'text-foreground'
  return pctChg > 0 ? 'text-rise' : 'text-fall'
}

/**
 * 成交额格式化（后端 amount 已是亿元，无需再 ÷10000）。
 * - null/undefined：返回 '—'
 * - 否则：X.XX 亿元
 */
export function formatAmount(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return '—'
  return `${amount.toLocaleString('zh-CN', { maximumFractionDigits: 2 })} 亿元`
}

/**
 * PE TTM 格式化（倍数，保留两位小数），无估值返回"暂无估值"。
 */
export function formatPe(peTtm: number | null | undefined): string {
  if (peTtm === null || peTtm === undefined) return '暂无估值'
  return peTtm.toFixed(2)
}

/**
 * 涨跌幅百分比格式化（后端数值即百分比，如 0.85 → "+0.85%"）。
 * 正值补 '+' 号，null → '—'。
 */
export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

/**
 * 收盘价格式化（指数点位，保留两位小数），null → '—'。
 */
export function formatClose(close: number | null | undefined): string {
  if (close === null || close === undefined) return '—'
  return close.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

/**
 * 权重百分比格式化（后端数值即百分比，如 5.23 → "5.23%"）。
 */
export function formatWeight(weight: number | null | undefined): string {
  if (weight === null || weight === undefined) return '—'
  return `${weight.toFixed(2)}%`
}
