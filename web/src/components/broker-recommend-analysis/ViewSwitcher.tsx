'use client'

/**
 * 视图切换控件（09 期 plan-03，AC-04/14）
 *
 * 单选按钮组，默认选中 'stock'（股票维度）。
 * 切换时由父组件统一清空 search + 回第 1 页（AC-14）。
 *
 * data-testid：broker-view-stock / broker-view-broker + aria-pressed（spec 选择器依赖）
 */
import React from 'react'
import { cn } from '@/lib/utils'
import type { BrokerView } from '@/lib/api'

export interface ViewSwitcherProps {
  value: BrokerView
  onChange: (view: BrokerView) => void
  disabled?: boolean
}

const OPTIONS: Array<{ value: BrokerView; label: string }> = [
  { value: 'stock', label: '股票维度' },
  { value: 'broker', label: '券商维度' },
]

export default function ViewSwitcher({
  value,
  onChange,
  disabled,
}: ViewSwitcherProps) {
  return (
    <div
      className="inline-flex items-center gap-1 p-1 bg-muted/60 rounded-lg"
      role="group"
      aria-label="视图切换"
    >
      {OPTIONS.map((opt) => {
        const isActive = value === opt.value
        return (
          <button
            key={opt.value}
            type="button"
            disabled={disabled}
            data-testid={`broker-view-${opt.value}`}
            aria-pressed={isActive}
            onClick={() => onChange(opt.value)}
            className={cn(
              'px-3 py-1.5 text-sm rounded-md transition-colors',
              isActive
                ? 'bg-card text-foreground shadow-sm font-medium'
                : 'text-muted-foreground hover:text-foreground',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
