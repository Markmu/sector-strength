'use client'

/**
 * 板块类型切换控件（券商荐股页排行榜筛选器）
 *
 * 切换排行榜的板块筛选维度（行业/概念/地域），对应后端 Sector.type 字段。
 * 默认选中 'industry'。范式照搬 fund-crowd-analysis/CrowdSectorTypeSelector。
 *
 * data-testid 约定（spec 选择器依赖）：
 * - 容器：broker-sector-type-selector
 * - 选项按钮：broker-sector-type-{value}（如 broker-sector-type-industry），含 aria-pressed
 */
import React from 'react'
import { cn } from '@/lib/utils'
import {
  SECTOR_TYPE_OPTIONS,
  type SectorType,
} from '@/types/sectorTypes'

export interface BrokerSectorTypeSelectorProps {
  value: SectorType
  onChange: (sectorType: SectorType) => void
  disabled?: boolean
}

export default function BrokerSectorTypeSelector({
  value,
  onChange,
  disabled,
}: BrokerSectorTypeSelectorProps) {
  return (
    <div
      className="inline-flex flex-wrap items-center gap-1 p-1 bg-muted/60 rounded-lg"
      data-testid="broker-sector-type-selector"
      role="group"
      aria-label="板块类型切换"
    >
      {SECTOR_TYPE_OPTIONS.map((opt) => {
        const isActive = value === opt.value
        return (
          <button
            key={opt.value}
            type="button"
            disabled={disabled}
            data-testid={`broker-sector-type-${opt.value}`}
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
