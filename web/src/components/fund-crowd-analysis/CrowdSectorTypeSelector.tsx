'use client'

/**
 * 板块类型切换控件
 *
 * 切换分布图 + 排行榜分类列的板块维度（行业/概念/地域），
 * 对应后端 Sector.type 字段。默认选中 'industry'。
 * 复用 CrowdScopeSelector 的 segmented control 范式 + web/src/types/sectorTypes 常量。
 *
 * 不含 theme/feature/style：扎堆页板块维度只保留行业/概念/地域（见 sectorTypes.ts 注释）。
 *
 * data-testid 约定（spec 选择器依赖）：
 * - 容器：crowd-sector-type-selector
 * - 选项按钮：crowd-sector-type-{value}（如 crowd-sector-type-industry），含 aria-pressed
 */
import React from 'react'
import { cn } from '@/lib/utils'
import {
  FUND_CROWD_SECTOR_OPTIONS,
  type FundCrowdSectorType,
} from '@/types/sectorTypes'

export interface CrowdSectorTypeSelectorProps {
  value: FundCrowdSectorType
  onChange: (sectorType: FundCrowdSectorType) => void
  disabled?: boolean
}

export default function CrowdSectorTypeSelector({
  value,
  onChange,
  disabled,
}: CrowdSectorTypeSelectorProps) {
  return (
    <div
      className="inline-flex flex-wrap items-center gap-1 p-1 bg-secondary/50 rounded-lg"
      data-testid="crowd-sector-type-selector"
      role="group"
      aria-label="板块类型切换"
    >
      {FUND_CROWD_SECTOR_OPTIONS.map((opt) => {
        const isActive = value === opt.value
        return (
          <button
            key={opt.value}
            type="button"
            disabled={disabled}
            data-testid={`crowd-sector-type-${opt.value}`}
            aria-pressed={isActive}
            title={opt.display}
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
