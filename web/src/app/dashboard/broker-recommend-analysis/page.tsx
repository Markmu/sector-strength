/**
 * 券商每月荐股分析页面路由（09 期 plan-03）
 *
 * 进入路径：/dashboard/broker-recommend-analysis（侧边栏"券商每月荐股"导航项）
 * 布局参照 fund-crowd-analysis/page.tsx：DashboardLayout 包裹业务内容。
 *
 * MEMORY 提醒（`admin 路由页 use client`）：新建 /dashboard 路由页 import
 * @/components/dashboard 必须加 'use client'，否则 build error 污染全局 E2E。
 */
'use client'

import { DashboardLayout } from '@/components/dashboard'
import BrokerRecommendPage from '@/components/broker-recommend-analysis/BrokerRecommendPage'

export default function BrokerRecommendAnalysisRoute() {
  return (
    <DashboardLayout>
      <div className="px-4 py-6 md:px-6 md:py-8">
        <div className="max-w-7xl mx-auto">
          <BrokerRecommendPage />
        </div>
      </div>
    </DashboardLayout>
  )
}
