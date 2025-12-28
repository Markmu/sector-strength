// 格式化数字
export function formatNumber(
  value: number | string | undefined | null,
  options?: {
    decimals?: number
    thousandsSeparator?: boolean
    prefix?: string
    suffix?: string
  }
): string {
  if (value === undefined || value === null) return '-'

  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '-'

  const {
    decimals = 2,
    thousandsSeparator = true,
    prefix = '',
    suffix = ''
  } = options || {}

  let formatted = num.toFixed(decimals)

  if (thousandsSeparator) {
    formatted = formatted.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  }

  return `${prefix}${formatted}${suffix}`
}

// 格式化百分比
export function formatPercent(value: number | string | undefined | null, decimals = 2): string {
  const formatted = formatNumber(value, { decimals })
  return formatted === '-' ? '-' : `${formatted}%`
}

// 格式化货币
export function formatCurrency(
  value: number | string | undefined | null,
  currency = '¥',
  decimals = 2
): string {
  return formatNumber(value, { decimals, prefix: currency })
}

// 格式化日期
export function formatDate(
  date: string | Date,
  format: 'short' | 'long' | 'time' = 'short'
): string {
  const d = typeof date === 'string' ? new Date(date) : date

  if (isNaN(d.getTime())) return '-'

  switch (format) {
    case 'short':
      return d.toLocaleDateString('zh-CN')
    case 'long':
      return d.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    case 'time':
      return d.toLocaleString('zh-CN')
    default:
      return d.toLocaleDateString('zh-CN')
  }
}

// 计算相对时间
export function getRelativeTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diff = now.getTime() - d.getTime()

  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 30) return `${days}天前`

  return formatDate(d, 'short')
}

// 生成颜色
export function generateColor(value: number, min: number, max: number): string {
  const ratio = (value - min) / (max - min)
  const hue = ratio * 120 // 从红(0)到绿(120)
  return `hsl(${hue}, 70%, 50%)`
}

// 获取涨跌颜色
export function getPriceChangeColor(value: number): string {
  if (value > 0) return 'text-red-500' // 涨：红色
  if (value < 0) return 'text-green-500' // 跌：绿色
  return 'text-gray-500' // 平：灰色
}

// 防抖函数
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => func(...args), delay)
  }
}

// 节流函数
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let lastCall = 0
  return (...args: Parameters<T>) => {
    const now = new Date().getTime()
    if (now - lastCall < delay) return
    lastCall = now
    return func(...args)
  }
}

// 深拷贝
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') return obj
  if (obj instanceof Date) return new Date(obj.getTime()) as unknown as T
  if (obj instanceof Array) return obj.map(item => deepClone(item)) as unknown as T
  if (typeof obj === 'object') {
    const clonedObj = {} as { [key: string]: any }
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        clonedObj[key] = deepClone(obj[key])
      }
    }
    return clonedObj as T
  }
  return obj
}

// 数组分组
export function groupBy<T, K extends keyof T>(
  array: T[],
  key: K
): Record<string, T[]> {
  return array.reduce((groups, item) => {
    const groupKey = String(item[key])
    groups[groupKey] = groups[groupKey] || []
    groups[groupKey].push(item)
    return groups
  }, {} as Record<string, T[]>)
}

// 数组去重
export function uniqueBy<T, K extends keyof T>(array: T[], key: K): T[] {
  const seen = new Set()
  return array.filter(item => {
    const value = item[key]
    if (seen.has(value)) return false
    seen.add(value)
    return true
  })
}

// 本地存储
export const storage = {
  get: <T>(key: string, defaultValue?: T): T | null => {
    if (typeof window === 'undefined') return defaultValue || null
    try {
      const item = localStorage.getItem(key)
      return item ? JSON.parse(item) : defaultValue || null
    } catch {
      return defaultValue || null
    }
  },

  set: (key: string, value: any): void => {
    if (typeof window === 'undefined') return
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch (error) {
      console.error('Failed to save to localStorage:', error)
    }
  },

  remove: (key: string): void => {
    if (typeof window === 'undefined') return
    localStorage.removeItem(key)
  },

  clear: (): void => {
    if (typeof window === 'undefined') return
    localStorage.clear()
  }
}

// URL 参数处理
export function getQueryParam(name: string): string | null {
  if (typeof window === 'undefined') return null
  const urlParams = new URLSearchParams(window.location.search)
  return urlParams.get(name)
}

export function setQueryParam(name: string, value: string): void {
  if (typeof window === 'undefined') return
  const url = new URL(window.location.href)
  url.searchParams.set(name, value)
  window.history.replaceState({}, '', url.toString())
}

// 错误处理
export function handleError(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'string') return error
  return '发生了未知错误'
}