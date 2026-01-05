'use client'

import { memo } from 'react'
import type { MAPeriod, MAConfig } from '@/types'

interface MAToggleControlsProps {
  visibleMAs: Record<MAPeriod, boolean>
  onToggle: (maPeriod: MAPeriod) => void
  disabledMAs?: Set<MAPeriod>
}

// 均线配置
const MA_CONFIGS: MAConfig[] = [
  { key: 'ma5', label: 'MA5', color: '#EF4444', lineType: 'solid', defaultVisible: true },
  { key: 'ma10', label: 'MA10', color: '#F59E0B', lineType: 'solid', defaultVisible: true },
  { key: 'ma20', label: 'MA20', color: '#FBBF24', lineType: 'solid', defaultVisible: true },
  { key: 'ma30', label: 'MA30', color: '#10B981', lineType: 'solid', defaultVisible: true },
  { key: 'ma60', label: 'MA60', color: '#3B82F6', lineType: 'solid', defaultVisible: true },
  { key: 'ma90', label: 'MA90', color: '#6366F1', lineType: 'solid', defaultVisible: false },
  { key: 'ma120', label: 'MA120', color: '#8B5CF6', lineType: 'solid', defaultVisible: false },
  { key: 'ma240', label: 'MA240', color: '#EC4899', lineType: 'solid', defaultVisible: false },
]

export const MAToggleControls = memo(function MAToggleControls({
  visibleMAs,
  onToggle,
  disabledMAs = new Set(),
}: MAToggleControlsProps) {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      <span className="text-sm text-gray-600">均线:</span>
      {MA_CONFIGS.map((config) => {
        const isVisible = visibleMAs[config.key]
        const isDisabled = disabledMAs.has(config.key)

        return (
          <label
            key={config.key}
            className={`
              flex items-center gap-1 px-2 py-1 text-sm rounded border cursor-pointer transition-colors
              ${
                isDisabled
                  ? 'opacity-40 cursor-not-allowed'
                  : 'hover:bg-gray-50'
              }
            `}
            style={{
              borderColor: config.color,
              backgroundColor: isVisible ? `${config.color}20` : 'transparent',
            }}
          >
            <input
              type="checkbox"
              checked={isVisible}
              disabled={isDisabled}
              onChange={() => !isDisabled && onToggle(config.key)}
              className="cursor-pointer"
            />
            <span
              className="font-medium"
              style={{ color: config.color }}
            >
              {config.label}
            </span>
          </label>
        )
      })}
    </div>
  )
})
