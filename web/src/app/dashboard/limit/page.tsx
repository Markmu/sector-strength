/**
 * 连板天梯页面路由
 *
 * 进入路径：/dashboard/limit（侧边栏"连板天梯"导航项）
 * 布局参照 etf-monitor/page.tsx。
 */
'use client'

import { DashboardLayout } from '@/components/dashboard'
import LimitLadderPage from '@/components/limit/LimitLadderPage'

export default function LimitRoute() {
  return (
    <DashboardLayout>
      <div className="px-4 py-6 md:px-6 md:py-8">
        <div className="max-w-7xl mx-auto">
          <LimitLadderPage />
        </div>
      </div>
    </DashboardLayout>
  )
}
