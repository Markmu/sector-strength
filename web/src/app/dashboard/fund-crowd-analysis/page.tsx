/**
 * 基金扎堆分析页面路由（plan-02）
 *
 * 进入路径：/dashboard/fund-crowd-analysis（侧边栏"基金扎堆分析"导航项）
 * 布局参照 shareholder-analysis/page.tsx：DashboardLayout 包裹业务内容，main 区域渲染主组件。
 *
 * MEMORY 提醒（`admin 路由页 use client`）：新建 /dashboard 路由页 import @/components/dashboard
 * 必须加 'use client'，否则 build error 污染全局 E2E。
 */
'use client'

import { DashboardLayout } from '@/components/dashboard'
import FundCrowdAnalysisPage from '@/components/fund-crowd-analysis/FundCrowdAnalysisPage'

export default function FundCrowdAnalysisRoute() {
  return (
    <DashboardLayout>
      <div className="px-4 py-6 md:px-6 md:py-8">
        <div className="max-w-7xl mx-auto">
          <FundCrowdAnalysisPage />
        </div>
      </div>
    </DashboardLayout>
  )
}
