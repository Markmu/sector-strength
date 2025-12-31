// 排名列表项组件
import React from 'react'
import { useRouter } from 'next/navigation'
import { getTrendIcon, getTrendColor, getStrengthColor } from '@/lib/ranking/sortUtils'
import type { RankingItem } from '@/lib/ranking/types'

interface RankingItemProps {
  data: RankingItem
  type: 'sector' | 'stock'
}

export const RankingItemComponent: React.FC<RankingItemProps> = React.memo(({ data, type }) => {
  const router = useRouter()

  const handleClick = () => {
    if (type === 'sector') {
      router.push(`/sector/${data.id}`)
    } else {
      router.push(`/stock/${data.id}`)
    }
  }

  return (
    <div
      className="flex items-center justify-between p-3 border-b border-[#f1f3f5] hover:bg-[#f8f9fb] cursor-pointer transition-colors"
      onClick={handleClick}
    >
      <div className="flex items-center gap-3 flex-1">
        {/* 排名编号 */}
        <span className="text-sm font-semibold text-[#adb5bd] w-6 text-center">
          {data.rank}
        </span>

        {/* 名称和代码 */}
        <div className="flex flex-col">
          <span className="font-medium text-[#1a1a2e]">{data.name}</span>
          <span className="text-xs text-[#6c757d]">{data.code}</span>
        </div>
      </div>

      {/* 右侧信息 */}
      <div className="flex items-center gap-4">
        {/* 趋势方向 */}
        <span className={`text-lg font-semibold ${getTrendColor(data.trend_direction)}`}>
          {getTrendIcon(data.trend_direction)}
        </span>

        {/* 强度得分 */}
        <span className={`text-lg font-bold ${getStrengthColor(data.strength_score)}`}>
          {data.strength_score.toFixed(1)}
        </span>
      </div>
    </div>
  )
})

RankingItemComponent.displayName = 'RankingItemComponent'

export default RankingItemComponent
