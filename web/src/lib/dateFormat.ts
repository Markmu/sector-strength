/**
 * 日期格式化工具函数
 *
 * 提供中文本地化的日期时间格式化功能
 */

/**
 * 格式化日期时间为中文本地化格式
 *
 * @param timestamp - Unix 时间戳（毫秒）或 ISO 8601 字符串
 * @returns 格式化的时间字符串 "YYYY-MM-DD HH:mm"，无效时返回"未知"
 *
 * @example
 * formatChineseDateTime(1705906200000) // "2026-01-22 15:30"
 * formatChineseDateTime('2026-01-22T15:30:00') // "2026-01-22 15:30"
 * formatChineseDateTime(null) // "未知"
 */
export function formatChineseDateTime(timestamp: number | string | null | undefined): string {
  if (timestamp === null || timestamp === undefined) {
    return '未知'
  }

  try {
    // 转换为 Date 对象
    const date = typeof timestamp === 'number'
      ? new Date(timestamp)
      : new Date(timestamp)

    // 验证日期有效性
    if (isNaN(date.getTime())) {
      return '未知'
    }

    // 格式化：YYYY-MM-DD HH:mm
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')

    return `${year}-${month}-${day} ${hours}:${minutes}`
  } catch (error) {
    console.error('日期格式化失败:', error)
    return '未知'
  }
}

/**
 * 格式化相对时间（可选，用于未来增强）
 *
 * @param timestamp - Unix 时间戳（毫秒）
 * @returns 相对时间描述，如"刚刚"、"5分钟前"，或绝对时间
 *
 * @example
 * formatRelativeTime(Date.now() - 30000) // "刚刚"
 * formatRelativeTime(Date.now() - 5 * 60 * 1000) // "5分钟前"
 * formatRelativeTime(Date.now() - 3 * 60 * 60 * 1000) // "3小时前"
 */
export function formatRelativeTime(timestamp: number | null | undefined): string {
  if (timestamp === null || timestamp === undefined) {
    return '未知'
  }

  const now = Date.now()
  const diff = now - timestamp

  // 小于 1 分钟
  if (diff < 60 * 1000) {
    return '刚刚'
  }

  // 小于 1 小时
  if (diff < 60 * 60 * 1000) {
    const minutes = Math.floor(diff / (60 * 1000))
    return `${minutes}分钟前`
  }

  // 小于 1 天
  if (diff < 24 * 60 * 60 * 1000) {
    const hours = Math.floor(diff / (60 * 60 * 1000))
    return `${hours}小时前`
  }

  // 大于 1 天，显示绝对时间
  return formatChineseDateTime(timestamp)
}
