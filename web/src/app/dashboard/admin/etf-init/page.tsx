'use client';

import { DashboardHeader } from '@/components/dashboard';
import AdminSidebar from '@/components/admin/AdminSidebar';
import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout';
import EtfSyncPanel from '@/components/admin/EtfSyncPanel';

/**
 * ETF 数据同步管理页面（第 14 期 plan-03 admin UI）
 */
export default function EtfInitPage() {
  return (
    <AdminLayoutWithSidebar sidebar={<AdminSidebar />}>
      <DashboardHeader
        title="ETF 数据同步"
        subtitle="ETF 份额/净值当日采集与历史数据回填"
      />
      <EtfSyncPanel />
    </AdminLayoutWithSidebar>
  );
}
