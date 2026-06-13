'use client';

import { DashboardHeader } from '@/components/dashboard';
import AdminSidebar from '@/components/admin/AdminSidebar';
import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout';
import ShareholderGroupPanel from '@/components/admin/ShareholderGroupPanel';

/**
 * 股东分组管理页面（plan-03）
 *
 * 管理员可在此新增 / 编辑 / 删除股东监控组及其匹配关键词规则。
 * 路由：/dashboard/admin/shareholder-groups
 */
export default function ShareholderGroupsPage() {
  return (
    <AdminLayoutWithSidebar sidebar={<AdminSidebar />}>
      <DashboardHeader
        title="股东分组管理"
        subtitle="监控组与匹配规则管理"
      />
      <ShareholderGroupPanel />
    </AdminLayoutWithSidebar>
  );
}
