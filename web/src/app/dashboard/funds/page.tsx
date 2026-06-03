/**
 * 基金列表页
 *
 * 布局：顶部 FundSearchBar + 左侧 FundFilterPanel + 右侧 FundListTable + 分页
 * URL query 同步：?search=xxx&market=E,O&fundType=股票型&page=1&pageSize=20
 */
'use client'

import { Suspense } from 'react'
import FundListPageContent from './FundListPageContent'

export default function FundListPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
            <p className="text-muted-foreground">加载中...</p>
          </div>
        </div>
      }
    >
      <FundListPageContent />
    </Suspense>
  )
}
