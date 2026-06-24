'use client'

/**
 * 口径切换控件（plan-02，AC-02）
 *
 * 单选按钮组（非下拉），贴合 PRD §3.1 线框图 [● 仅主动基金   ○ 全部基金]。
 * 默认选中 'active'（仅主动基金，剔除被动指数型/增强指数型）。
 *
 * data-testid 约定（spec 选择器依赖）：
 * - 容器：crowd-scope-selector
 * - 选项按钮：crowd-scope-active / crowd-scope-all（含 aria-pressed 反映选中态）
 */
import React from 'react'
import { cn } from '@/lib/utils'
import type { CrowdScope } from '@/lib/api'

export interface CrowdScopeSelectorProps {
  value: CrowdScope
  onChange: (scope: CrowdScope) => void
  disabled?: boolean
}

const OPTIONS: Array<{ value: CrowdScope; label: string; hint: string }> = [
  { value: 'active', label: '仅主动基金', hint: '剔除被动指数型/增强指数型' },
  { value: 'all', label: '全部基金', hint: '含场内 ETF 与被动指数' },
]

export default function CrowdScopeSelector({
  value,
  onChange,
  disabled,
}: CrowdScopeSelectorProps) {
  return (
    <div
      className="inline-flex items-center gap-1 p-1 bg-secondary/50 rounded-lg"
      data-testid="crowd-scope-selector"
      role="group"
      aria-label="基金口径切换"
    >
      {OPTIONS.map((opt) => {
        const isActive = value === opt.value
        return (
          <button
            key={opt.value}
            type="button"
            disabled={disabled}
            data-testid={`crowd-scope-${opt.value}`}
            aria-pressed={isActive}
            title={opt.hint}
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
