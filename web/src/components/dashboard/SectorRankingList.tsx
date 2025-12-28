// 板块排名列表组件
import React from 'react'
import { Card } from '@/components/ui/Card'
import { useSectorRanking } from '@/hooks/useSectorRanking'
import { LoadingState } from './LoadingState'
import { ErrorState } from './ErrorState'
import RankingItemComponent from './RankingItem'
import type { SortOrder } from '@/lib/ranking/types'

interface SectorRankingListProps {
  topN?: number
  order?: SortOrder
  sortBy?: 'strength' | 'trend'
  sectorType?: 'industry' | 'concept'
  onSortChange?: (order: SortOrder) => void
}

export const SectorRankingList: React.FC<SectorRankingListProps> = React.memo(({
  topN = 10,
  order = 'desc',
  sortBy = 'strength',
  sectorType,
  onSortChange,
}) => {
  const { sectors, total, isLoading, isError } = useSectorRanking({
    topN,
    order,
    sortBy,
    sectorType,
  })

  if (isLoading) {
    return (
      <Card className="p-6">
        <LoadingState message="加载板块排名..." />
      </Card>
    )
  }

  if (isError) {
    return (
      <Card className="p-6">
        <ErrorState message="加载板块排名失败" />
      </Card>
    )
  }

  return (
    <Card className="overflow-hidden">
      <div className="p-4 border-b bg-gray-50">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            板块强度排名 TOP {topN}
          </h2>
          {onSortChange && (
            <button
              onClick={() => onSortChange(order === 'desc' ? 'asc' : 'desc')}
              className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1"
            >
              排序 {order === 'desc' ? '↓' : '↑'}
            </button>
          )}
        </div>
        <p className="text-xs text-gray-500 mt-1">共 {total} 个板块</p>
      </div>

      <div className="divide-y">
        {sectors.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            暂无数据
          </div>
        ) : (
          sectors.map((sector) => (
            <RankingItemComponent key={sector.id} data={sector} type="sector" />
          ))
        )}
      </div>
    </Card>
  )
})

SectorRankingList.displayName = 'SectorRankingList'

export default SectorRankingList
