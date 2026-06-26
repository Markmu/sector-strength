/**
 * 板块类型统一定义
 *
 * 集中管理所有板块类型的常量映射，作为前端唯一的类型真相源。
 * 与后端 server/src/services/data_acquisition/sector_types.py 保持一致。
 */

// 所有合法的板块类型 key
export const SECTOR_TYPES = [
  'industry',
  'concept',
  'region',
  'feature',
  'style',
  'theme',
] as const

export type SectorType = (typeof SECTOR_TYPES)[number]

// 内部 key → 简短中文标签
export const SECTOR_TYPE_LABELS: Record<SectorType, string> = {
  industry: '行业',
  concept: '概念',
  region: '地域',
  feature: '特色',
  style: '风格',
  theme: '主题',
}

// 内部 key → 完整中文显示标签
export const SECTOR_TYPE_DISPLAY: Record<SectorType, string> = {
  industry: '行业板块',
  concept: '概念板块',
  region: '地域板块',
  feature: '特色板块',
  style: '风格板块',
  theme: '主题板块',
}

// 类型选项数组（用于 UI 遍历渲染）
export const SECTOR_TYPE_OPTIONS: {
  value: SectorType
  label: string
  display: string
}[] = SECTOR_TYPES.map((t) => ({
  value: t,
  label: SECTOR_TYPE_LABELS[t],
  display: SECTOR_TYPE_DISPLAY[t],
}))

/**
 * 基金扎堆分析支持的板块维度子集（仅行业/概念/地域）。
 *
 * 扎堆页只展示行业、概念、地域三种板块维度，排除 theme/feature/style。
 * 排除 theme：Tushare 同花顺「主题」(TH) 分类仅有 10 个特殊旗舰主题指数
 * （同花顺金仓30/50/100/200 + 茅指数 + 宁组合），成分股去重仅 ~223 只，
 * 而扎堆股集合约 3100 只 → ~93% 股票无主题归属、归「未分类」，分布无分析价值。
 * 其余页面（sector-analysis/heatmap/rankings 等）仍使用全量 SECTOR_TYPES，不受影响。
 */
export const FUND_CROWD_SECTOR_TYPES = [
  'industry',
  'concept',
  'region',
] as const

export type FundCrowdSectorType = (typeof FUND_CROWD_SECTOR_TYPES)[number]

// 扎堆页板块选项（仅行业/概念/地域）
export const FUND_CROWD_SECTOR_OPTIONS: {
  value: FundCrowdSectorType
  label: string
  display: string
}[] = FUND_CROWD_SECTOR_TYPES.map((t) => ({
  value: t,
  label: SECTOR_TYPE_LABELS[t],
  display: SECTOR_TYPE_DISPLAY[t],
}))
