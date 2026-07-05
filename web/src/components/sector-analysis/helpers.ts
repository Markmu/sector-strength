/**
 * 板块成分股表格格式化辅助函数。
 *
 * 同时被 SectorStocksTable 与个股分析落地页（StockInfoCard）复用。
 */

/** 趋势方向数值含义：1=上升 / 0=横盘 / -1=下降（与后端 trend_direction 一致） */
export interface TrendDisplay {
  arrow: string
  /** A 股惯例：红涨绿跌。上升=红，下降=绿，横盘=灰 */
  colorClass: string
  label: string
}

/**
 * 趋势渲染：trend_direction 数值 → 箭头 + 颜色 + 文案。
 * A 股红涨绿跌：上升 ▲ 红，下降 ▼ 绿，横盘/缺失 ▬ 灰。
 */
export function getTrendDisplay(trendDirection: number | null): TrendDisplay {
  if (trendDirection === 1) {
    return { arrow: '▲', colorClass: 'text-red-600', label: '上升' }
  }
  if (trendDirection === -1) {
    return { arrow: '▼', colorClass: 'text-green-600', label: '下降' }
  }
  return { arrow: '▬', colorClass: 'text-muted-foreground', label: '横盘' }
}

/**
 * 市值量级简写：number → 中文量级字符串。
 * 万亿/亿/万 量级，保留两位小数。null 或非正值返回占位符。
 */
export function formatMarketCap(value: number | null): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—'
  }
  if (value <= 0) return '—'
  if (value >= 1e12) {
    return `${(value / 1e12).toFixed(2)}万亿`
  }
  if (value >= 1e8) {
    return `${(value / 1e8).toFixed(2)}亿`
  }
  if (value >= 1e4) {
    return `${(value / 1e4).toFixed(2)}万`
  }
  return value.toFixed(2)
}

/** 最新价两位小数。null 返回占位符。 */
export function formatPrice(value: number | null): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—'
  }
  return value.toFixed(2)
}

/** 强度分取整数。null 返回占位符。 */
export function formatScore(value: number | null): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—'
  }
  return Math.round(value).toString()
}
