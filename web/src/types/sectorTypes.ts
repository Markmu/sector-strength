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
