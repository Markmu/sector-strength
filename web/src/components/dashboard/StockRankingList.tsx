// 个股排名列表组件 - 使用虚拟滚动
import React, { useRef } from 'react'
import { FixedSizeList } from 'react-window'
import type { ListChildComponentProps } from 'react-window'
import { Card } from '@/components/ui/Card'
import { useStockRanking } from '@/hooks/useStockRanking'
import { LoadingState } from './LoadingState'
import { ErrorState } from './ErrorState'
import RankingItemComponent from './RankingItem'
import type { SortOrder } from '@/lib/ranking/types'

interface StockRankingListProps {
  topN?: number
  order?: SortOrder
  sortBy?: 'strength' | 'trend'
  sectorId?: string
  onSortChange?: (order: SortOrder) => void
}

const ITEM_HEIGHT = 72 // 每个列表项的高度

export const StockRankingList: React.FC<StockRankingListProps> = React.memo(({
  topN = 20,
  order = 'desc',
  sortBy = 'strength',
  sectorId,
  onSortChange,
}) => {
  const { stocks, total, isLoading, isError } = useStockRanking({
    topN,
    order,
    sortBy,
    sectorId,
  })

  const listRef = useRef<FixedSizeList>(null)

  // 虚拟滚动的行组件
  const Row = React.memo(({ index, style, data }: ListChildComponentProps) => {
    const stock = data[index]
    return (
      <div style={style}>
        <RankingItemComponent data={stock} type="stock" />
      </div>
    )
  })

  Row.displayName = 'Row'

  if (isLoading) {
    return (
      <Card className="p-6">
        <LoadingState message="加载个股排名..." />
      </Card>
    )
  }

  if (isError) {
    return (
      <Card className="p-6">
        <ErrorState message="加载个股排名失败" />
      </Card>
    )
  }

  return (
    <Card className="overflow-hidden flex flex-col h-full">
      <div className="p-4 border-b bg-gray-50 flex-shrink-0">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            个股强度排名 TOP {topN}
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
        <p className="text-xs text-gray-500 mt-1">共 {total} 只个股</p>
      </div>

      {stocks.length === 0 ? (
        <div className="p-8 text-center text-gray-500 flex-1 flex items-center justify-center">
          暂无数据
        </div>
      ) : (
        <div className="flex-1 overflow-auto" style={{ minHeight: 400 }}>
          <FixedSizeList
            ref={listRef}
            height={400}
            itemCount={stocks.length}
            itemSize={ITEM_HEIGHT}
            width="100%"
            itemData={stocks}
          >
            {Row}
          </FixedSizeList>
        </div>
      )}
    </Card>
  )
})

StockRankingList.displayName = 'StockRankingList'

export default StockRankingList
