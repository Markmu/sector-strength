/**
 * 板块资金流页面路由（13 期 plan-03）
 *
 * 进入路径：/dashboard/sector-fund-flow（侧边栏"板块资金流"导航项）
 * 布局参照 fund-crowd-analysis/page.tsx：DashboardLayout 包裹业务内容，main 区域渲染主组件。
 *
 * MEMORY 提醒（`admin 路由页 use client`）：新建 /dashboard 路由页 import
 * @/components/dashboard 必须加 'use client'，否则 build error 污染全局 E2E。
 */
'use client'

import { DashboardLayout } from '@/components/dashboard'
import SectorFundFlowPage from '@/components/sector-fund-flow/SectorFundFlowPage'

export default function SectorFundFlowRoute() {
  return (
    <DashboardLayout>
      <div className="px-4 py-6 md:px-6 md:py-8">
        <div className="max-w-7xl mx-auto">
          <SectorFundFlowPage />
        </div>
      </div>
    </DashboardLayout>
  )
}
