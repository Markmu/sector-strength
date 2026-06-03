'use client';

import { DashboardHeader } from '@/components/dashboard';
import AdminSidebar from '@/components/admin/AdminSidebar';
import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout';
import FundSyncPanel from '@/components/admin/FundSyncPanel';

/**
 * 基金数据同步管理页面
 */
export default function FundInitPage() {
  return (
    <AdminLayoutWithSidebar sidebar={<AdminSidebar />}>
      <DashboardHeader
        title="基金同步"
        subtitle="基金数据采集和手动同步管理"
      />
      <FundSyncPanel />
    </AdminLayoutWithSidebar>
  );
}
