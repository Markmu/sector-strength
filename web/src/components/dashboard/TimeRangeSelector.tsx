'use client'

import { memo } from 'react'
import type { TimeRangeOption, TimeRangeConfig } from '@/types'

interface TimeRangeSelectorProps {
  value: TimeRangeOption
  onChange: (value: TimeRangeOption) => void
}

const TIME_RANGES: TimeRangeConfig[] = [
  { label: '1周', days: 7, value: '1w' },
  { label: '1月', days: 30, value: '1m' },
  { label: '2月', days: 60, value: '2m' },
  { label: '3月', days: 90, value: '3m' },
  { label: '6月', days: 180, value: '6m' },
  { label: '1年', days: 365, value: '1y' },
]

export const TimeRangeSelector = memo(function TimeRangeSelector({
  value,
  onChange,
}: TimeRangeSelectorProps) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-sm text-gray-600 mr-2">时间范围:</span>
      {TIME_RANGES.map((range) => (
        <button
          key={range.value}
          onClick={() => onChange(range.value)}
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
  )
})
