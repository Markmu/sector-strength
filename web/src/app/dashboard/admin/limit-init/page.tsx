'use client';

import { DashboardHeader } from '@/components/dashboard';
import AdminSidebar from '@/components/admin/AdminSidebar';
import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout';
import LimitSyncPanel from '@/components/admin/LimitSyncPanel';

/**
 * 涨停专题数据同步管理页面
 */
export default function LimitInitPage() {
  return (
    <AdminLayoutWithSidebar sidebar={<AdminSidebar />}>
      <DashboardHeader
        title="涨停专题同步"
        subtitle="涨跌停明细、连板天梯、涨停最强板块数据采集"
      />
      <LimitSyncPanel />
    </AdminLayoutWithSidebar>
  );
}
