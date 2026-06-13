/**
 * 股东分析面板页面路由（plan-04）
 *
 * 进入路径：/dashboard/shareholder-analysis（侧边栏"股东分析"导航项）
 * 布局参照 funds 页面：DashboardLayout 包裹业务内容，main 区域渲染主组件。
 */
'use client'

import { DashboardLayout } from '@/components/dashboard'
import ShareholderAnalysisPage from '@/components/shareholder-analysis/ShareholderAnalysisPage'

export default function ShareholderAnalysisRoute() {
  return (
    <DashboardLayout>
      <div className="px-4 py-6 md:px-6 md:py-8">
        <div className="max-w-7xl mx-auto">
          <ShareholderAnalysisPage />
        </div>
      </div>
    </DashboardLayout>
  )
}
