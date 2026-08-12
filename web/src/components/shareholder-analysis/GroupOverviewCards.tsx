'use client'

/**
 * 监控组概览卡片（plan-04）
 *
 * Props:
 * - groups: 监控组概览列表（API 已按 stockCount 降序）
 * - selectedGroupIds: 当前选中组 id 数组
 * - onGroupSelect: 选中组变化回调（多选 toggle）
 *
 * 每张卡片展示：组名、描述、持仓股票数、增持/减持/新进/退出数量
 * 卡片可点击切换选中态，选中时高亮（border-primary + bg-primary/5）
 * 使用 button + aria-pressed 暴露选中态（spec 退化用 aria-pressed/data-selected 断言）
 * data-testid="group-card-{groupId}" 供 spec 稳定定位
 *
 * 边界：空 groups → 展示"暂无监控组"提示
 */
import React from 'react'
import { InboxIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ShareholderGroupOverview } from '@/lib/api'

export interface GroupOverviewCardsProps {
  groups: ShareholderGroupOverview[]
  selectedGroupIds: number[]
  onGroupSelect: (groupIds: number[]) => void
  hasPrevPeriod: boolean
}

export default function GroupOverviewCards({
  groups,
  selectedGroupIds,
  onGroupSelect,
  hasPrevPeriod,
}: GroupOverviewCardsProps) {
  // 空状态：无监控组
  if (groups.length === 0) {
    return (
      <div className="bg-card rounded-xl border border-border shadow-sm p-12 text-center">
        <InboxIcon className="w-12 h-12 mx-auto mb-3 text-faint" />
        <p className="text-lg font-medium text-foreground mb-2">暂无监控组</p>
        <p className="text-sm text-muted-foreground">
          请管理员先在管理后台配置股东监控组并同步数据
        </p>
      </div>
    )
  }

  const handleToggle = (groupId: number) => {
    const next = selectedGroupIds.includes(groupId)
      ? selectedGroupIds.filter((id) => id !== groupId)
      : [...selectedGroupIds, groupId]
    onGroupSelect(next)
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
      {groups.map((group) => {
        const isSelected = selectedGroupIds.includes(group.groupId)
        return (
          <button
            key={group.groupId}
            type="button"
            data-testid={`group-card-${group.groupId}`}
            aria-pressed={isSelected}
            data-selected={isSelected ? 'true' : 'false'}
            onClick={() => handleToggle(group.groupId)}
            className={cn(
              'text-left p-4 rounded-xl border shadow-sm transition-all cursor-pointer',
              'hover:shadow-md hover:-translate-y-0.5',
              isSelected
                ? 'border-primary bg-primary/5 ring-2 ring-primary/30'
                : 'border-border bg-card'
            )}
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <span className="font-semibold text-foreground text-base">
                {group.groupName}
              </span>
              {isSelected && (
                <span className="inline-flex items-center px-1.5 py-0.5 text-xs bg-primary text-primary-foreground rounded">
                  已选
                </span>
              )}
            </div>
            {group.description && (
              <p className="text-xs text-muted-foreground mb-3 line-clamp-1">
                {group.description}
              </p>
            )}
            <div className="grid grid-cols-2 gap-y-1.5 gap-x-2 text-xs">
              <div className="text-muted-foreground">持仓股票</div>
              <div className="text-right font-semibold text-foreground">
                {group.stockCount}
              </div>
              {hasPrevPeriod ? (
                <>
                  <div className="text-rise">↑增持</div>
                  <div className="text-right text-rise font-medium">
                    {group.increaseCount}
                  </div>
                  <div className="text-rise">↓减持</div>
                  <div className="text-right text-rise font-medium">
                    {group.decreaseCount}
                  </div>
                  <div className="text-primary">★新进</div>
                  <div className="text-right text-primary font-medium">
                    {group.newCount}
                  </div>
                  <div className="text-muted-foreground">✕退出</div>
                  <div className="text-right text-muted-foreground font-medium">
                    {group.exitCount}
                  </div>
                </>
              ) : (
                <div className="col-span-2 text-xs text-muted-foreground italic mt-1">
                  上期数据不完整，变动趋势暂不可用
                </div>
              )}
            </div>
          </button>
        )
      })}
    </div>
  )
}
