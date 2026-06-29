'use client'

/**
 * 月份选择器（09 期 plan-03，AC-05/10）
 *
 * 显示 YYYY-MM，options 来自 months（仅已同步月份，降序）。
 * 默认最新已同步月份（YYYYMM 值最大者，months 首项）。
 *
 * data-testid：broker-month-selector（spec 选择器依赖）
 */
import React from 'react'
import { cn } from '@/lib/utils'

export interface MonthSelectorProps {
  months: string[] // YYYY-MM-01 ISO 字符串，降序
  value: string | undefined
  onChange: (month: string) => void
  disabled?: boolean
}

/** YYYY-MM-01 → "YYYY-MM" 显示 */
function toDisplay(iso: string): string {
  if (!iso || iso.length < 7) return iso
  return iso.slice(0, 7) // "2026-06-01" → "2026-06"
}

export default function MonthSelector({
  months,
  value,
  onChange,
  disabled,
}: MonthSelectorProps) {
  return (
    <div
      className="inline-flex items-center gap-2"
      data-testid="broker-month-selector"
    >
      <span className="text-sm text-muted-foreground">月份</span>
      <select
        className={cn(
          'h-9 rounded-lg border border-border bg-card px-3 text-sm text-foreground',
          'focus:outline-none focus:ring-2 focus:ring-primary/40',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
        value={value ?? ''}
        disabled={disabled || months.length === 0}
        onChange={(e) => onChange(e.target.value)}
      >
        {months.map((m) => (
          <option key={m} value={m}>
            {toDisplay(m)}
          </option>
        ))}
      </select>
    </div>
  )
}
