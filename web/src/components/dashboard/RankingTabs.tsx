// 移动端排名 Tab 切换组件
import React, { useState } from 'react'
import SectorRankingList from './SectorRankingList'
import StockRankingList from './StockRankingList'
import SortingControls from './SortingControls'
import type { SortBy, SortOrder } from '@/lib/ranking/types'

type TabType = 'sectors' | 'stocks'

export const RankingTabs: React.FC = React.memo(() => {
  const [activeTab, setActiveTab] = useState<TabType>('sectors')
  const [sortBy, setSortBy] = useState<SortBy>('strength')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  const handleSortByChange = (newSortBy: SortBy) => {
    setSortBy(newSortBy)
  }

  const handleSortOrderChange = (newSortOrder: SortOrder) => {
    setSortOrder(newSortOrder)
  }

  return (
    <div className="space-y-4">
      {/* Tab 切换 */}
      <div className="flex border-b border-[#e9ecef]">
        <button
          onClick={() => setActiveTab('sectors')}
          className={`flex-1 py-3 text-sm font-medium transition-colors ${
            activeTab === 'sectors'
              ? 'text-cyan-500 border-b-2 border-cyan-500'
              : 'text-[#6c757d] hover:text-[#1a1a2e]'
          }`}
        >
          板块排名
        </button>
        <button
          onClick={() => setActiveTab('stocks')}
          className={`flex-1 py-3 text-sm font-medium transition-colors ${
            activeTab === 'stocks'
              ? 'text-cyan-500 border-b-2 border-cyan-500'
              : 'text-[#6c757d] hover:text-[#1a1a2e]'
          }`}
        >
          个股排名
        </button>
      </div>

      {/* 排序控制 */}
      <div className="flex justify-center py-2">
        <SortingControls
          sortBy={sortBy}
          sortOrder={sortOrder}
          onSortByChange={handleSortByChange}
          onSortOrderChange={handleSortOrderChange}
        />
      </div>

      {/* 内容区域 */}
      <div className="min-h-[400px]">
        {activeTab === 'sectors' ? (
          <SectorRankingList
            topN={10}
            order={sortOrder}
            sortBy={sortBy}
            onSortChange={setSortOrder}
          />
        ) : (
          <StockRankingList
            topN={20}
            order={sortOrder}
            sortBy={sortBy}
            onSortChange={setSortOrder}
          />
        )}
      </div>
    </div>
  )
})

RankingTabs.displayName = 'RankingTabs'

export default RankingTabs
