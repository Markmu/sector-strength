/**
 * ETF 监控页面路由（14 期 plan-04 路由壳 / plan-05 业务接入）
 *
 * 进入路径：/dashboard/etf-monitor（侧边栏"ETF 监控"导航项）
 * 布局参照 sector-fund-flow/page.tsx：DashboardLayout 包裹业务内容，main 区域渲染主组件。
 *
 * plan-05：接入 EtfMonitorPage 业务组件（排行表/趋势图/明细等）。
 *
 * MEMORY 提醒（`admin 路由页 use client`）：新建 /dashboard 路由页 import
 * @/components/dashboard 必须加 'use client'，否则 build error 污染全局 E2E。
 */
'use client'

import { DashboardLayout } from '@/components/dashboard'
import EtfMonitorPage from '@/components/etf-monitor/EtfMonitorPage'

export default function EtfMonitorRoute() {
  return (
    <DashboardLayout>
      <div className="px-4 py-6 md:px-6 md:py-8">
        <div className="max-w-7xl mx-auto">
          <EtfMonitorPage />
        </div>
      </div>
    </DashboardLayout>
  )
}
