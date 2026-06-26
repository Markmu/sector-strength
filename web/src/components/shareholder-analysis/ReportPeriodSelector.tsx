'use client'

/**
 * 报告期下拉选择器（plan-04）
 *
 * Props:
 * - periods: 可选报告期列表（YYYY-MM-DD 字符串）
 * - value: 当前选中报告期
 * - onChange: 切换回调
 *
 * 实现：基于 SimpleSelect，trigger 为 button，选项为 role=option（spec 选择器）
 */
import React from 'react'
import SimpleSelect from '@/components/ui/SimpleSelect'

export interface ReportPeriodSelectorProps {
  periods: string[]
  value: string | null
  onChange: (period: string) => void
}

export default function ReportPeriodSelector({
  periods,
  value,
  onChange,
}: ReportPeriodSelectorProps) {
  if (periods.length === 0) {
    return null
  }

  const options = periods.map((p) => ({ value: p, label: p }))

  return (
    <SimpleSelect
      value={value ?? ''}
      options={options}
      onChange={onChange}
      placeholder="选择报告期"
      testId="report-period-selector"
      ariaLabel="报告期选择"
      className="min-w-[160px]"
    />
  )
}
