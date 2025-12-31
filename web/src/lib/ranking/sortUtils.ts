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
      return 'text-green-600'
    case 0:
      return 'text-gray-500'
    case -1:
      return 'text-red-600'
    default:
      return 'text-gray-400'
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
  if (score >= 80) return 'text-green-600'
  if (score >= 60) return 'text-yellow-600'
  return 'text-red-600'
}

export function getStrengthBgColor(score: number): string {
  if (score >= 80) return 'bg-green-100'
  if (score >= 60) return 'bg-yellow-100'
  return 'bg-red-100'
}
