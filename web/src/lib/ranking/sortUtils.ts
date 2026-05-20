// 排序工具函数
import type { RankingItem } from './types'

export function getTrendLabel(direction: number): string {
  switch (direction) {
    case 1:
      return '上升'
    case 0:
      return '横盘'
    case -1:
      return '下降'
    default:
      return '未知'
  }
}

export function getTrendColor(direction: number): string {
  switch (direction) {
    case 1:
      return 'text-rise'
    case 0:
      return 'text-muted-foreground'
    case -1:
      return 'text-fall'
    default:
      return 'text-faint'
  }
}

export function getTrendIcon(direction: number): string {
  switch (direction) {
    case 1:
      return '↑'
    case 0:
      return '→'
    case -1:
      return '↓'
    default:
      return '?'
  }
}

export function getStrengthColor(score: number): string {
  if (score >= 80) return 'text-rise'
  if (score >= 60) return 'text-amber-600'
  return 'text-fall'
}

export function getStrengthBgColor(score: number): string {
  if (score >= 80) return 'bg-rise/10'
  if (score >= 60) return 'bg-amber-100'
  return 'bg-fall/10'
}
