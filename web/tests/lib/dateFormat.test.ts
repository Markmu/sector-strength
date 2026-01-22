/**
 * 日期格式化工具函数测试
 */

import { formatChineseDateTime, formatRelativeTime } from '@/lib/dateFormat'

describe('formatChineseDateTime', () => {
  it('应该格式化有效时间戳为 YYYY-MM-DD HH:mm 格式', () => {
    const timestamp = new Date('2026-01-22T15:30:00').getTime()
    expect(formatChineseDateTime(timestamp)).toBe('2026-01-22 15:30')
  })

  it('应该处理 ISO 8601 字符串', () => {
    const isoString = '2026-01-22T15:30:00'
    expect(formatChineseDateTime(isoString)).toBe('2026-01-22 15:30')
  })

  it('应该处理 null 值，返回"未知"', () => {
    expect(formatChineseDateTime(null)).toBe('未知')
  })

  it('应该处理 undefined 值，返回"未知"', () => {
    expect(formatChineseDateTime(undefined)).toBe('未知')
  })

  it('应该处理无效时间戳，返回"未知"', () => {
    expect(formatChineseDateTime(NaN)).toBe('未知')
  })

  it('应该正确处理月份和日期补零', () => {
    const timestamp = new Date('2026-01-02T03:05:00').getTime()
    expect(formatChineseDateTime(timestamp)).toBe('2026-01-02 03:05')
  })

  it('应该正确处理月份和日期不补零的情况', () => {
    const timestamp = new Date('2026-12-31T23:59:00').getTime()
    expect(formatChineseDateTime(timestamp)).toBe('2026-12-31 23:59')
  })

  it('应该处理无效的 Date 对象', () => {
    expect(formatChineseDateTime('invalid-date')).toBe('未知')
  })

  it('应该处理负数时间戳（1970年之前的日期）', () => {
    // 1969年12月31日 23:59:59
    const timestamp = -1000
    expect(formatChineseDateTime(timestamp)).toBe('1969-12-31 23:59')
  })
})

describe('formatRelativeTime', () => {
  it('应该返回"刚刚"对于小于1分钟的时间', () => {
    const now = Date.now()
    const timestamp = now - 30 * 1000 // 30秒前
    expect(formatRelativeTime(timestamp)).toBe('刚刚')
  })

  it('应该返回"X分钟前"对于小于1小时的时间', () => {
    const now = Date.now()
    const timestamp = now - 5 * 60 * 1000 // 5分钟前
    expect(formatRelativeTime(timestamp)).toBe('5分钟前')
  })

  it('应该返回"X小时前"对于小于1天的时间', () => {
    const now = Date.now()
    const timestamp = now - 3 * 60 * 60 * 1000 // 3小时前
    expect(formatRelativeTime(timestamp)).toBe('3小时前')
  })

  it('应该返回绝对时间对于大于1天的时间', () => {
    const timestamp = new Date('2026-01-22T15:30:00').getTime()
    const result = formatRelativeTime(timestamp)
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
  })

  it('应该处理 null 值，返回"未知"', () => {
    expect(formatRelativeTime(null)).toBe('未知')
  })

  it('应该处理 undefined 值，返回"未知"', () => {
    expect(formatRelativeTime(undefined)).toBe('未知')
  })
})
