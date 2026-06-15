'use client';

import { DashboardHeader } from '@/components/dashboard';
import AdminSidebar from '@/components/admin/AdminSidebar';
import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout';
import ShareholderGroupEditor from '@/components/admin/ShareholderGroupEditor';

/**
 * 新增股东分组页面（plan-03 重构：弹窗 → 整页表单）
 *
 * 路由：/dashboard/admin/shareholder-groups/new
 * 静态段 new 优先于动态段 [id] 匹配，不会被吞。
 */
export default function NewShareholderGroupPage() {
  return (
    <AdminLayoutWithSidebar sidebar={<AdminSidebar />}>
      <DashboardHeader title="新增分组" subtitle="配置监控组名称与匹配关键词" />
      <ShareholderGroupEditor mode="create" />
    </AdminLayoutWithSidebar>
  );
}
