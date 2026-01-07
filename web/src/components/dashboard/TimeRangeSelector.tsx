'use client'

import { memo, useState, useCallback } from 'react'
import type { TimeRangeOption, TimeRangeConfig } from '@/types'

interface TimeRangeSelectorProps {
  value: TimeRangeOption
  customStartDate?: string | null
  customEndDate?: string | null
  onChange: (value: TimeRangeOption) => void
  onCustomDateChange?: (startDate: string, endDate: string) => void
}

const TIME_RANGES: TimeRangeConfig[] = [
  { label: '1周', days: 7, value: '1w' },
  { label: '1月', days: 30, value: '1m' },
  { label: '2月', days: 60, value: '2m' },
  { label: '3月', days: 90, value: '3m' },
  { label: '6月', days: 180, value: '6m' },
  { label: '1年', days: 365, value: '1y' },
  { label: '自定义', days: 0, value: 'custom' },
]

// 辅助函数
const getTodayDate = () => {
  return new Date().toISOString().split('T')[0]
}

const getDefaultStartDate = () => {
  const date = new Date()
  date.setDate(date.getDate() - 30)
  return date.toISOString().split('T')[0]
}

export const TimeRangeSelector = memo(function TimeRangeSelector({
  value,
  customStartDate,
  customEndDate,
  onChange,
  onCustomDateChange,
}: TimeRangeSelectorProps) {
  const [showCustomInputs, setShowCustomInputs] = useState(value === 'custom')
  const [isApplying, setIsApplying] = useState(false)
  const [dateError, setDateError] = useState<string | null>(null)

  // 临时状态，用于保存用户正在选择但尚未确认的日期
  const [tempStartDate, setTempStartDate] = useState<string>(customStartDate || getDefaultStartDate())
  const [tempEndDate, setTempEndDate] = useState<string>(customEndDate || getTodayDate())

  const handleRangeChange = (newValue: TimeRangeOption) => {
    onChange(newValue)
    if (newValue === 'custom') {
      setShowCustomInputs(true)
      setDateError(null)
    } else {
      setShowCustomInputs(false)
      setDateError(null)
    }
  }

  // 开始日期输入变化（仅更新临时状态）
  const handleStartDateInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setTempStartDate(e.target.value)
    setDateError(null)
  }, [])

  // 结束日期输入变化（仅更新临时状态）
  const handleEndDateInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setTempEndDate(e.target.value)
    setDateError(null)
  }, [])

  // 点击应用按钮时提交
  const handleApplyButtonClick = useCallback(() => {
    // 验证日期
    if (tempStartDate > tempEndDate) {
      setDateError('开始日期不能晚于结束日期')
      return
    }

    setDateError(null)
    setIsApplying(true)

    if (onCustomDateChange) {
      onCustomDateChange(tempStartDate, tempEndDate)
    }

    // 延迟重置加载状态，让用户看到反馈
    setTimeout(() => {
      setIsApplying(false)
    }, 500)
  }, [tempStartDate, tempEndDate, onCustomDateChange])

  // 计算两个日期之间的天数
  const calculateDays = useCallback((start: string, end: string) => {
    const startDate = new Date(start)
    const endDate = new Date(end)
    const diffTime = Math.abs(endDate.getTime() - startDate.getTime())
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1
  }, [])

  // 获取当前选择的天数显示
  const getDaysDisplay = () => {
    try {
      const days = calculateDays(tempStartDate, tempEndDate)
      return <span className="text-sm text-gray-500">（共 {days} 天）</span>
    } catch {
      return null
    }
  }

  const today = getTodayDate()

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm text-gray-600 mr-2">时间范围:</span>
        {TIME_RANGES.map((range) => (
          <button
            key={range.value}
            onClick={() => handleRangeChange(range.value)}
            className={`
              px-3 py-1 text-sm rounded border transition-colors
              ${
                value === range.value
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }
            `}
          >
            {range.label}
          </button>
        ))}
      </div>

      {/* 自定义日期范围输入 */}
      {showCustomInputs && value === 'custom' && (
        <div className="pl-20 mt-2 p-4 bg-blue-50 rounded-lg border border-blue-200 space-y-3">
          {/* 日期输入区域 */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <label htmlFor="start-date" className="text-sm font-medium text-gray-700 whitespace-nowrap">
                开始日期:
              </label>
              <input
                id="start-date"
                type="date"
                value={tempStartDate}
                onChange={handleStartDateInputChange}
                max={today}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div className="flex items-center gap-2">
              <label htmlFor="end-date" className="text-sm font-medium text-gray-700 whitespace-nowrap">
                结束日期:
              </label>
              <input
                id="end-date"
                type="date"
                value={tempEndDate}
                onChange={handleEndDateInputChange}
                max={today}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* 应用按钮 */}
            <button
              onClick={handleApplyButtonClick}
              disabled={isApplying}
              className={`
                px-4 py-1.5 text-sm font-medium rounded transition-colors
                ${
                  isApplying
                    ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
                    : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow'
                }
              `}
            >
              {isApplying ? '应用中...' : '应用'}
            </button>

            {/* 天数显示 */}
            {getDaysDisplay()}
          </div>

          {/* 提示信息 */}
          <div className="flex items-center gap-2 text-sm">
            {dateError && (
              <div className="flex items-center gap-2 text-red-600">
                <svg
                  className="h-4 w-4"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span>{dateError}</span>
              </div>
            )}

            {!isApplying && !dateError && (
              <div className="text-xs text-gray-500 flex items-center gap-1">
                <svg
                  className="h-3 w-3"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span>选择日期后点击"应用"按钮更新图表数据</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
})
