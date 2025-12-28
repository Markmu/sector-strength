// 排名区域容器组件
import React, { useState } from 'react'
import SectorRankingList from './SectorRankingList'
import StockRankingList from './StockRankingList'
import SortingControls from './SortingControls'
import type { SortBy, SortOrder } from '@/lib/ranking/types'

export const RankingSection: React.FC = React.memo(() => {
  const [sortBy, setSortBy] = useState<SortBy>('strength')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  const handleSortByChange = (newSortBy: SortBy) => {
    setSortBy(newSortBy)
  }

  const handleSortOrderChange = (newSortOrder: SortOrder) => {
    setSortOrder(newSortOrder)
  }

  return (
    <div className="space-y-6">
      {/* 排序控制 */}
      <div className="flex justify-center">
        <SortingControls
          sortBy={sortBy}
          sortOrder={sortOrder}
          onSortByChange={handleSortByChange}
          onSortOrderChange={handleSortOrderChange}
        />
      </div>

      {/* 排名列表 - 桌面端双列布局 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 板块排名列表 */}
        <SectorRankingList
          topN={10}
          order={sortOrder}
          sortBy={sortBy}
          onSortChange={setSortOrder}
        />

        {/* 个股排名列表 */}
        <StockRankingList
          topN={20}
          order={sortOrder}
          sortBy={sortBy}
          onSortChange={setSortOrder}
        />
      </div>
    </div>
  )
})

RankingSection.displayName = 'RankingSection'

export default RankingSection
