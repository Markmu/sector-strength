/**
 * 更新时间显示组件
 *
 * 显示数据最后更新时间，支持中文本地化格式
 */

'use client'

import { formatChineseDateTime } from '@/lib/dateFormat'

/**
 * UpdateTimeDisplay 组件属性
 */
export interface UpdateTimeDisplayProps {
  /** 最后获取时间戳（Unix 毫秒） */
  lastFetch: number | null | undefined
  /** 自定义类名 */
  className?: string
}

/**
 * 更新时间显示组件
 *
 * @description
 * - 显示时钟图标和格式化的更新时间
 * - 时间格式：YYYY-MM-DD HH:mm（中文本地化）
 * - 缺失时显示"未知"
 * - 使用 Tailwind CSS 样式
 *
 * @example
 * ```tsx
 * <UpdateTimeDisplay lastFetch={Date.now()} />
 * <UpdateTimeDisplay lastFetch={null} /> // 显示"未知"
 * ```
 */
export function UpdateTimeDisplay({ lastFetch, className }: UpdateTimeDisplayProps) {
  const updateText = formatChineseDateTime(lastFetch)

  return (
    <div className={`text-sm text-gray-500 flex items-center ${className || ''}`}>
      <svg
        className="w-4 h-4 mr-1.5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <span>数据更新时间：{updateText}</span>
    </div>
  )
}
