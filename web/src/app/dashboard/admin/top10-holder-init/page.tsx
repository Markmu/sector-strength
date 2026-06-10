'use client';

import { DashboardHeader } from '@/components/dashboard';
import AdminSidebar from '@/components/admin/AdminSidebar';
import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout';
import StockTop10SyncPanel from '@/components/admin/StockTop10SyncPanel';

/**
 * 股票十大流通股东同步管理页面
 */
export default function Top10HolderInitPage() {
  return (
    <AdminLayoutWithSidebar sidebar={<AdminSidebar />}>
      <DashboardHeader
        title="股票持仓同步"
        subtitle="十大流通股东数据采集和手动同步管理"
      />
      <StockTop10SyncPanel />
    </AdminLayoutWithSidebar>
  );
}
